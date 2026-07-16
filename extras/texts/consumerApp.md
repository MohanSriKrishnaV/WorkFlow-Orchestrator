Start with **one consumer/worker app** that can handle all workflow step types. Later, split into multiple specialized worker apps only if you want to show advanced scaling.

For your project, the best path is:

> **Version 1: single worker app, multiple task handlers inside it.**  
> **Version 2: multiple queues/workers by task category.**

---

# Recommended for you

Use one worker process like this:

```text
FastAPI API
   |
   v
RabbitMQ
   |
   v
Single Worker App
   |
   |-- validate_file handler
   |-- parse_csv handler
   |-- validate_records handler
   |-- store_customers handler
   |-- generate_report handler
   |-- send_notification handler
```

This is enough for the first complete version.

---

# Why start with a single consumer app?

Because your first goal is to understand:

- AMQP publishing
- consuming
- acknowledgement
- retry
- dead-letter queues
- workflow state updates
- step dependency logic

If you split into multiple apps too early, you will add unnecessary complexity.

You will have to manage:

- multiple queues
- multiple routing keys
- multiple worker deployments
- task-to-queue mapping
- different scaling rules
- more logs
- more configuration

That is useful later, not now.

---

# Version 1 architecture

Use one exchange and one queue.

```text
Exchange: flowpilot.jobs.exchange
Queue: flowpilot.jobs.queue
Routing key: job.execute
```

All workflow steps go to same queue:

```text
validate_file
parse_csv
validate_records
store_customers
generate_report
send_notification
```

Worker consumes from:

```text
flowpilot.jobs.queue
```

Message contains:

```json
{
  "job_id": "job_101",
  "workflow_run_id": "run_55",
  "step_key": "parse_csv",
  "task_type": "parse_csv",
  "payload": {
    "file_id": "file_22"
  }
}
```

Worker reads:

```text
task_type = parse_csv
```

Then calls the correct handler.

---

# Worker code structure

Use something like this:

```text
backend/app/workers/
  worker.py
  task_registry.py
  handlers/
    validate_file.py
    parse_csv.py
    validate_records.py
    store_customers.py
    generate_report.py
    send_notification.py
```

Your registry maps task type to function:

```python
TASK_REGISTRY = {
    "validate_file": validate_file_handler,
    "parse_csv": parse_csv_handler,
    "validate_records": validate_records_handler,
    "store_customers": store_customers_handler,
    "generate_report": generate_report_handler,
    "send_notification": send_notification_handler,
}
```

Worker flow:

```python
task_type = message["task_type"]
handler = TASK_REGISTRY[task_type]
result = handler(message["payload"])
```

This is clean and extensible.

---

# Version 1 message flow

```text
User uploads CSV
   |
   v
FastAPI creates workflow run
   |
   v
FastAPI queues validate_file message
   |
   v
Single worker consumes validate_file
   |
   v
Worker updates DB: validate_file SUCCESS
   |
   v
Workflow engine queues parse_csv
   |
   v
Same worker consumes parse_csv
   |
   v
Worker updates DB: parse_csv SUCCESS
   |
   v
Workflow continues
```

Same worker app handles every step.

---

# Can you still run multiple workers?

Yes.

Even with one worker app, you can run multiple instances.

```text
RabbitMQ Queue
     |
     |---- Worker instance 1
     |---- Worker instance 2
     |---- Worker instance 3
```

All run the same code.

RabbitMQ distributes messages among them.

This gives horizontal scaling without separate apps.

So you can say:

> “The worker service is stateless and horizontally scalable. Multiple instances of the same worker can consume from the same queue.”

That is a strong interview point.

---

# But what about specialized workers?

That is Version 2.

Later, you can split workers by task type/category.

Example:

```text
RabbitMQ Exchange
   |
   |-- file.queue          → File Worker
   |-- csv.queue           → CSV Worker
   |-- database.queue      → DB Worker
   |-- notification.queue  → Notification Worker
```

Routing keys:

```text
job.file.validate
job.csv.parse
job.csv.validate_records
job.db.store_customers
job.report.generate
job.notification.send
```

Architecture:

```text
FastAPI
  |
  v
RabbitMQ exchange
  |
  |-- file.queue
  |      v
  |   File Worker
  |
  |-- csv.queue
  |      v
  |   CSV Worker
  |
  |-- db.queue
  |      v
  |   DB Worker
  |
  |-- notification.queue
         v
      Notification Worker
```

This is useful when:

- CSV parsing is CPU-heavy
- notification jobs are slow/network-heavy
- DB writes need limited concurrency
- some tasks need different libraries
- some workers need different scaling

---

# When should you split workers?

Split only after your single-worker version works.

Use this rule:

| Situation | Use |
|---|---|
| Learning AMQP basics | Single worker |
| MVP/resume project V1 | Single worker |
| Need simple deployment | Single worker |
| Need to show horizontal scaling | Multiple instances of same worker |
| Need different scaling per task type | Specialized workers |
| Need different runtime/libraries | Specialized workers |
| Need advanced AMQP routing | Multiple queues/workers |

---

# For free-tier deployment

Single worker is much better.

Because free-tier hosting is limited.

If you create 4 worker apps:

```text
file-worker
csv-worker
db-worker
notification-worker
```

You now need to host 4 background services.

That is not free-tier friendly.

Instead, use:

```text
one worker app
one queue
many handlers
```

For local demo, run:

```bash
python -m app.workers.worker
```

If you want to simulate scaling locally:

```bash
python -m app.workers.worker --name worker-1
python -m app.workers.worker --name worker-2
python -m app.workers.worker --name worker-3
```

Same code, multiple instances.

---

# Recommended implementation path

## Phase A — Single worker, single queue

```text
flowpilot.jobs.queue
```

All tasks go here.

This is your first version.

---

## Phase B — Single worker app, multiple instances

Run multiple copies locally.

```text
worker-1
worker-2
worker-3
```

This teaches you load distribution.

---

## Phase C — Multiple routing keys, still one worker

Use routing keys but bind them to same queue.

Example:

```text
job.execute.validate_file
job.execute.parse_csv
job.execute.store_customers
```

All route to:

```text
flowpilot.jobs.queue
```

This lets you learn routing keys without separate workers.

---

## Phase D — Multiple queues and specialized workers

Only after MVP.

```text
flowpilot.csv.queue
flowpilot.notification.queue
flowpilot.db.queue
```

This becomes an advanced feature.

---

# Best design for your resume

Mention both:

> “Implemented a generic worker service using task registry pattern. The system supports running multiple worker instances against the same AMQP queue for horizontal scaling, and the AMQP routing design can be extended to specialized queues for task-specific workers.”

That sounds mature without overbuilding.

---

# Final recommendation

For now:

## Use one consumer app.

One worker app:

```text
worker.py
```

One queue:

```text
flowpilot.jobs.queue
```

Multiple handlers inside:

```text
validate_file
parse_csv
validate_records
store_customers
generate_report
send_notification
```

Later, after everything works, add optional advanced mode:

```text
specialized queues + specialized workers
```

But do **not** start there.