AMQP fits in the **middle between your FastAPI orchestration engine and your worker processes**.

In simple terms:

> FastAPI decides **what job should run next**.  
> RabbitMQ/AMQP delivers that job to an available worker.  
> Worker executes the job and updates PostgreSQL.

So AMQP is your **reliable communication layer** between the orchestrator and the workers.

---

# Where AMQP sits in the architecture

```text
React Dashboard
      |
      v
FastAPI API + Workflow Engine
      |
      | 1. Save workflow/job state
      v
PostgreSQL
      |
      | 2. Publish job message
      v
RabbitMQ / AMQP
      |
      | 3. Deliver job to worker
      v
Worker Process
      |
      | 4. Execute task
      v
PostgreSQL
      |
      | 5. Engine queues next step
      v
RabbitMQ / AMQP
```

---

# In your CSV import workflow

Your workflow is:

```text
validate_file
   ↓
parse_csv
   ↓
validate_records
   ↓
store_customers
   ↓
generate_report
   ↓
send_notification
```

Each step becomes an AMQP message.

Example:

```text
Step: parse_csv
Message sent to RabbitMQ
Worker consumes it
Worker parses CSV
Worker updates DB
Workflow engine queues next step
```

---

# Full example flow

## 1. User uploads CSV from React

```text
React
  ↓
POST /csv-imports
  ↓
FastAPI
```

FastAPI stores:

```text
uploaded_files table
workflow_runs table
workflow_steps table
```

Then it finds the first step:

```text
validate_file
```

And publishes a message to RabbitMQ.

---

## 2. FastAPI publishes AMQP message

RabbitMQ message:

```json
{
  "job_id": "job_101",
  "workflow_run_id": "run_55",
  "step_key": "validate_file",
  "task_type": "validate_file",
  "payload": {
    "file_id": "file_22"
  }
}
```

Published to:

```text
Exchange: flowpilot.exchange
Routing key: job.execute.validate_file
Queue: validate_file.queue
```

---

## 3. Worker consumes message

```text
RabbitMQ
  ↓
Worker
```

Worker receives:

```text
Run validate_file task for file_22
```

Worker does:

```text
Check file exists
Check extension is .csv
Check required columns
Check size limit
```

Then updates DB:

```text
workflow_steps.validate_file = SUCCESS
job.status = SUCCESS
```

---

## 4. Workflow engine queues next step

After `validate_file` succeeds, the engine checks:

```text
Which steps depend on validate_file?
```

It finds:

```text
parse_csv
```

Then it publishes another AMQP message:

```json
{
  "job_id": "job_102",
  "workflow_run_id": "run_55",
  "step_key": "parse_csv",
  "task_type": "parse_csv",
  "payload": {
    "file_id": "file_22"
  }
}
```

Worker consumes and runs `parse_csv`.

This continues until:

```text
send_notification
```

is complete.

---

# Why use AMQP here?

Without AMQP, FastAPI would process everything directly:

```text
Upload CSV
  ↓
FastAPI validates
  ↓
FastAPI parses
  ↓
FastAPI stores
  ↓
FastAPI reports
```

That is bad because:

- API request may timeout
- user must wait
- server gets blocked
- failures are harder to retry
- scaling is difficult
- no proper queueing
- no worker separation

With AMQP:

```text
FastAPI accepts request quickly
RabbitMQ stores jobs
Workers process in background
User tracks status from dashboard
```

---

# AMQP responsibilities in your project

AMQP handles:

## 1. Job delivery

When a workflow step is ready, publish it as a message.

```text
workflow engine → RabbitMQ → worker
```

---

## 2. Worker distribution

If you run 3 workers:

```text
Worker A
Worker B
Worker C
```

RabbitMQ distributes jobs among them.

```text
Queue has 100 jobs
RabbitMQ sends jobs to available workers
```

This lets you scale horizontally.

---

## 3. Acknowledgement

Worker must confirm:

```text
I processed this message successfully
```

This is called:

```text
ACK
```

If worker crashes before ACK, RabbitMQ can redeliver the message.

---

## 4. Failure handling

If worker fails a task:

```text
NACK
```

Then you decide:

```text
Retry later
or
Dead-letter
```

---

## 5. Retry with delay

Failed job can go to a retry queue:

```text
Main Queue
   ↓ failure
Retry Queue, wait 30 seconds
   ↓
Main Queue again
```

This is AMQP + RabbitMQ dead-letter/TTL behavior.

---

## 6. Dead-letter queue

If job fails too many times:

```text
Dead Letter Queue
```

Example:

```text
parse_csv failed 3 times
Move to dead-letter queue
Show it in dashboard
```

---

# Your AMQP design

Start simple.

## Version 1: one queue

```text
Exchange: flowpilot.exchange
Queue: flowpilot.jobs.queue
Routing key: job.execute
```

All steps go to the same queue.

```text
validate_file
parse_csv
validate_records
store_customers
generate_report
send_notification
```

All are consumed by one type of worker.

This is easiest.

---

## Version 2: task-specific routing keys

Later:

```text
Routing key: job.execute.validate_file
Routing key: job.execute.parse_csv
Routing key: job.execute.store_customers
Routing key: job.execute.notification
```

Queues:

```text
file.queue
csv.queue
database.queue
notification.queue
```

This lets you specialize workers.

Example:

```text
CSV Worker consumes csv.queue
Notification Worker consumes notification.queue
Database Worker consumes database.queue
```

This is more advanced and impressive.

---

# Recommended AMQP setup for your project

Use this design:

```text
Exchange: flowpilot.jobs.exchange
Type: direct

Main queue:
flowpilot.jobs.queue

Retry queues:
flowpilot.retry.5s.queue
flowpilot.retry.30s.queue
flowpilot.retry.60s.queue

Dead-letter queue:
flowpilot.dead.queue
```

## Routing keys

```text
job.execute
job.retry.5s
job.retry.30s
job.retry.60s
job.dead
```

---

# Message lifecycle

```text
1. FastAPI creates job in DB
2. FastAPI publishes message to RabbitMQ
3. Worker receives message
4. Worker marks job RUNNING
5. Worker executes task
6. If success:
      Mark job SUCCESS
      ACK message
      Queue next workflow step
7. If failure and retry_count < max_retries:
      Mark job RETRYING
      Publish to retry queue
      ACK original message
8. If failure and retry_count >= max_retries:
      Mark job DEAD_LETTER
      Publish to dead queue
      ACK original message
```

Important:

> Do not blindly `NACK requeue=true` forever. That can create infinite retry loops.

---

# Example AMQP message

```json
{
  "message_id": "msg_abc_123",
  "job_id": "job_101",
  "workflow_run_id": "run_55",
  "step_key": "parse_csv",
  "task_type": "parse_csv",
  "payload": {
    "file_id": "file_22"
  },
  "attempt": 1,
  "max_retries": 3,
  "idempotency_key": "run_55_parse_csv"
}
```

---

# PostgreSQL vs AMQP responsibility

This distinction is important.

| Responsibility | PostgreSQL | RabbitMQ/AMQP |
|---|---|---|
| Store workflow definitions | Yes | No |
| Store workflow status | Yes | No |
| Store job status | Yes | No |
| Store execution logs | Yes | No |
| Deliver jobs to workers | No | Yes |
| Retry routing | Partial | Yes |
| Dead-letter queue | Partial | Yes |
| Worker load distribution | No | Yes |
| Long-term audit history | Yes | No |

Remember:

> PostgreSQL is the source of truth.  
> RabbitMQ is the delivery system.

If RabbitMQ message is lost or duplicated, PostgreSQL helps recover state.

---

# In interview, explain like this

Say:

> “AMQP fits between the orchestration engine and workers. The API creates workflow runs and persists state in PostgreSQL. Whenever a step becomes executable, the engine publishes a job message to RabbitMQ. Workers consume messages, execute the step, update the database, and then the engine schedules the next dependent steps. RabbitMQ gives us asynchronous delivery, acknowledgements, retry queues, dead-letter queues, and horizontal worker scaling.”

That is a strong answer.

---

# Final simple mental model

Think of it like this:

```text
FastAPI = manager
PostgreSQL = memory/source of truth
RabbitMQ/AMQP = task dispatch system
Worker = employee doing the work
React = control room/dashboard
```

For your CSV import:

```text
Manager says: parse this CSV
Task dispatch system sends it to worker
Worker parses it
Memory is updated
Manager sends next task
Dashboard shows progress
```

That is where AMQP fits.