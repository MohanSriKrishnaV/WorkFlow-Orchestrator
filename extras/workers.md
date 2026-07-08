No — a **worker is usually not another FastAPI app**.

A worker is a **separate Python process/script** that runs in the background, listens to RabbitMQ, consumes messages, executes tasks, and updates the database.

Think of it like this:

```text
FastAPI app = handles HTTP requests from React/users
Worker app = handles background jobs from RabbitMQ
```

They can be in the **same codebase**, but they run as **different processes**.

---

# Simple mental model

```text
React UI
   |
   | HTTP request
   v
FastAPI API Server
   |
   | publish job message
   v
RabbitMQ Queue
   |
   | consume message
   v
Worker Process
   |
   | update status/result
   v
PostgreSQL
```

---

# FastAPI vs Worker

| Part | FastAPI App | Worker |
|---|---|---|
| Runs HTTP server? | Yes | Usually no |
| Handles React requests? | Yes | No |
| Listens to RabbitMQ? | Publishes mostly | Consumes mostly |
| Executes long jobs? | No | Yes |
| Example command | `uvicorn app.main:app --reload` | `python -m app.workers.worker` |
| Role | API/control layer | Background execution layer |

---

# Example in your project

## FastAPI receives CSV upload

User clicks:

```text
Upload CSV
```

React calls:

```http
POST /csv-imports
```

FastAPI does:

```text
1. Save file metadata
2. Create workflow run
3. Create first job: validate_file
4. Publish message to RabbitMQ
5. Return immediately
```

FastAPI response:

```json
{
  "workflow_run_id": "run_123",
  "status": "QUEUED"
}
```

FastAPI does **not** process the whole CSV.

---

## Worker receives job from RabbitMQ

Worker is already running in terminal:

```bash
python -m app.workers.worker
```

It waits for messages:

```text
Waiting for jobs...
```

RabbitMQ sends it:

```json
{
  "job_id": "job_101",
  "workflow_run_id": "run_123",
  "step_key": "validate_file",
  "task_type": "validate_file",
  "payload": {
    "file_id": "file_22"
  }
}
```

Worker executes:

```text
validate_file handler
```

Then updates PostgreSQL:

```text
job_101 = SUCCESS
validate_file step = SUCCESS
```

Then it triggers the next step:

```text
parse_csv
```

---

# Is the worker a separate project?

Not necessarily.

Best structure for you:

```text
backend/
  app/
    main.py                  # FastAPI entry point
    database.py
    models/
    routers/
    services/
    amqp/
      publisher.py
      connection.py
    workers/
      worker.py              # Worker entry point
      task_registry.py
      handlers/
        validate_file.py
        parse_csv.py
        validate_records.py
        store_customers.py
        generate_report.py
        send_notification.py
```

Same backend codebase.

Two ways to run it:

## Run API

```bash
uvicorn app.main:app --reload
```

## Run worker

```bash
python -m app.workers.worker
```

Same repo, same database models, same config, different process.

---

# What does a worker look like?

Very simplified example:

```python name=worker.py
import asyncio
import json
import aio_pika

from app.workers.task_registry import TASK_REGISTRY
from app.services.jobs import mark_job_running, mark_job_success, mark_job_failed

async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)

        job_id = body["job_id"]
        task_type = body["task_type"]
        payload = body["payload"]

        await mark_job_running(job_id)

        try:
            handler = TASK_REGISTRY[task_type]
            result = await handler(payload)

            await mark_job_success(job_id, result)

        except Exception as e:
            await mark_job_failed(job_id, str(e))
            raise

async def main():
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
    channel = await connection.channel()

    queue = await channel.declare_queue("flowpilot.jobs.queue", durable=True)

    await queue.consume(handle_message)

    print("Worker started. Waiting for jobs...")
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
```

This is not a FastAPI app. It has no routes. It just waits for queue messages.

---

# Can a worker be a FastAPI app?

Technically yes, but usually you should not do that for your main worker.

You could create a FastAPI endpoint like:

```http
POST /demo/process-next-job
```

for free-tier demo mode.

But your real worker should be a background process.

---

# Why not process inside FastAPI itself?

Bad version:

```text
React uploads CSV
FastAPI parses entire CSV
FastAPI validates rows
FastAPI inserts records
FastAPI generates report
FastAPI sends notification
Response returns after long time
```

Problems:

```text
Request timeout
API becomes slow
Hard to retry
Hard to scale
Bad user experience
```

Good version:

```text
React uploads CSV
FastAPI queues workflow
Response returns immediately
Worker processes in background
React polls status
```

---

# Running locally

During development, you will open multiple terminals.

## Terminal 1 — FastAPI

```bash
cd backend
uvicorn app.main:app --reload
```

## Terminal 2 — Worker

```bash
cd backend
python -m app.workers.worker
```

## Terminal 3 — React

```bash
cd frontend
npm run dev
```

## RabbitMQ

Initially CloudAMQP, so no local RabbitMQ needed.

Later with Docker:

```bash
docker compose up rabbitmq postgres
```

---

# Can you run multiple workers?

Yes.

Open more terminals:

```bash
python -m app.workers.worker --name worker-1
python -m app.workers.worker --name worker-2
python -m app.workers.worker --name worker-3
```

All consume from the same queue:

```text
flowpilot.jobs.queue
```

RabbitMQ distributes jobs among them.

This is horizontal scaling.

---

# Final answer

A **worker is not another FastAPI app**.

It is a **background Python process** that:

```text
1. Connects to RabbitMQ
2. Waits for job messages
3. Executes task handlers
4. Updates PostgreSQL
5. Triggers next workflow step
6. Acknowledges or retries the message
```

For your project:

```text
FastAPI = API server
Worker = background job consumer
RabbitMQ = bridge between them
PostgreSQL = source of truth
React = dashboard
```

Same codebase, different process.