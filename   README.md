# FlowPilot

FlowPilot is a workflow orchestration platform for reliable bulk CSV processing.

It uses:

- React frontend
- FastAPI backend
- PostgreSQL for persistent state
- RabbitMQ/AMQP for background job delivery
- Worker process for asynchronous task execution

## Current Status


## Project Structure

```text
flowpilot/
  client/
  server/
```

## Backend

```bash
cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
run worker:
python -m app.workers.test_worker
python -m app.workers.outbox_publisher

running scripts:
source venv/bin/activate && uvicorn app.main:app --reload
venv/bin/python -m app.workers.job_worker
venv/bin/python -m app.workers.outbox_publisher
'''


```

### Backend architecture

The backend is implemented in `server/app` as an async FastAPI service with a transactional database, an outbox event pattern, and separate worker processes for reliable job execution.

```text
Frontend -> FastAPI API -> PostgreSQL
                |
                v
             Outbox DB
                |
                v
            Outbox Publisher
                |
                v
             RabbitMQ Exchange
                |
      +---------+---------+
      |         |         |
      v         v         v
   Job Queue  Retry Q2s  DLQ
      |         |
      v         |
  Job Worker    |
      |         |
      v         +-> retry back to main exchange
  Task Executor
```

1. FastAPI application
   - Entry point: `server/app/main.py`
   - Includes routers for `health`, `jobs`, `files`, `workflows`, and AMQP test endpoints.
   - Uses CORS middleware for local frontend origins and a shared API prefix at `/api/v1`.
   - Serves OpenAPI docs at `/docs` for easy development and testing.

2. Configuration
   - `server/app/core/config.py` loads environment settings from `.env` using Pydantic Settings.
   - Config includes database connection, RabbitMQ URL, AMQP exchange/queue names, retry routing keys, DLQ names, and API prefix.
   - `get_settings()` is cached to avoid repeated reloading.

3. Async database layer
   - `server/app/db/database.py` creates an async SQLAlchemy engine and session maker with `expire_on_commit=False`.
   - `server/app/models/job.py` defines the `jobs` table with JSONB payload fields, state tracking, retries, timestamps, and error details.
   - `server/app/models/outbox_event.py` defines the `outbox_events` table with event status, retry count, next attempt timing, and failure metadata.
   - The design uses PostgreSQL JSONB for flexible payload/result storage without rigid schema changes.
   - `get_db_session()` yields an async session for API request handlers and worker code.

4. Job lifecycle and atomic claim
   - A new job is created with `PENDING` status and an outbox event for guaranteed delivery.
   - `server/app/services/job_service.py` flushes the job first to get the ID, then writes the outbox event in the same transaction.
   - Once the outbox event is published, the job transitions to `QUEUED` and becomes eligible for worker processing.
   - `claim_job_for_processing()` atomically updates `PENDING` or `QUEUED` jobs to `RUNNING`, preventing duplicate execution across workers.
   - Status lifecycle: `PENDING` -> `QUEUED` -> `RUNNING` -> `SUCCESS` / `FAILED` / `CANCELLED`.
   - `retry_failed_job()` and `mark_job_retrying()` support retrying failures while preserving retry count and error context.

5. Outbox pattern
   - The outbox pattern separates concerns between database state and message broker delivery.
   - `create_job()` writes both job data and an outbox event in one transactional unit so the broker message is never lost if the database commit succeeds.
   - `outbox_events` store event payload, current publish state, retry metadata, and deadlines for delayed retries.
   - `server/app/workers/outbox_publisher.py` actively claims pending events and serializes the publish operation to RabbitMQ.
   - Event claim updates avoid multiple workers publishing the same event, and `mark_outbox_event_publishing()` records that a worker has taken ownership.
   - If publishing fails, the event is marked `FAILED`, `attempt_count` increments, and `next_attempt_at` is scheduled using exponential backoff via `calculate_outbox_retry_delay_seconds()`.
   - `reset_failed_outbox_events_to_pending()` and `reset_stuck_publishing_outbox_events_to_pending()` ensure eventual recovery from transient broker outages or stuck publishers.
   - This design delivers at-least-once semantics for messages while keeping the database authoritative.

6. AMQP topology and retry delivery
   - `server/app/amqp/topology.py` builds the RabbitMQ infrastructure at startup: a durable direct exchange, a main job queue, retry queues with TTL, and a dead-letter queue.
   - The main job queue is bound to `job.created` messages, while retry queues are bound to separate retry routing keys.
   - Each retry queue uses `x-message-ttl` and `x-dead-letter-exchange` so expired messages return to the main exchange after a delay.
   - The current topology provides fixed retry delays of 2s, 4s, and 8s without adding a dedicated scheduler service.
   - `server/app/amqp/job_publisher.py` sends persistent JSON messages and chooses the correct retry route based on `retry_count`.
   - Dead-letter delivery is handled by `publish_job_dead_letter()`, allowing failed jobs to be inspected or processed separately later.
   - Using durable queues, persistent messages, and DLX-based retry improves robustness during broker restarts and partial failures.

7. Job worker and execution
   - `server/app/workers/job_worker.py` consumers a job message and looks up `job_id` from the payload.
   - It claims a job for processing with `claim_job_for_processing()`, ensuring only one worker can set the job to `RUNNING`.
   - The worker updates workflow step state to `RUNNING` before executing the task.
   - `execute_task()` supports `echo`, `csv_profile`, `csv_clean_basic`, and `fail` task types, with CSV tasks accessing the database for file metadata or processing logic.
   - On successful execution, the worker marks the job as `SUCCESS`, stores the result, updates workflow state, and triggers the next workflow step if needed.
   - On transient failure, `mark_job_retrying()` increments retry count and publishes a retry message through the retry exchange.
   - If a job exhausts retries, the worker marks it `FAILED` and publishes to the dead-letter queue.
   - This isolates long-running or failing work from the API layer and preserves clear failure semantics.

8. Workflow orchestration
   - Workflow APIs in `server/app/api/routes/workflows.py` expose endpoints to create workflows, start CSV cleaning workflows, list workflows, and retrieve workflow results.
   - `server/app/services/workflow_service.py` persists workflows and workflow steps, linking each job to workflow state.
   - `start_csv_cleaning_workflow()` creates a workflow, starts the first `csv_profile` job, and records the first step as `QUEUED`.
   - When a job succeeds, `create_next_step_after_success()` may add a follow-up `csv_clean_basic` job, enabling chained workflow transitions.
   - The workflow model supports multi-step pipelines while keeping individual job retry and failure handling separate.

9. Validation and file handling
   - `server/app/services/job_validation_service.py` validates task payloads for CSV jobs, including `file_id` and boolean clean options.
   - `server/app/api/routes/files.py` provides file upload, metadata listing, CSV preview, and download endpoints.
   - File uploads are stored on disk and referenced in the database, so tasks can safely access file paths and metadata.

10. Design decisions
   - Async FastAPI, SQLAlchemy, and aio-pika provide end-to-end async I/O for API, DB, and broker operations.
   - Separate API and worker processes ensure HTTP requests remain fast while background processing is handled independently.
   - The outbox pattern enforces durability and consistency between the database and RabbitMQ.
   - RabbitMQ retry queues and dead-letter routing avoid custom retry scheduling and make failure paths explicit.
   - JSONB payload storage provides flexible task and result data modeling with minimal schema churn.
   - Using durable queues, persistent messages, and DB-backed outbox state improves resilience against partial outages.
   - Health and doc endpoints support observability, developer debugging, and quick validation of the running service.

```
db queries:
select * from jobs WHERE status='PENDING';

Backend runs at:

```text
http://127.0.0.1:8000
```

Health endpoint:

```text
http://127.0.0.1:8000/api/v1/health
```

Swagger docs:

```text
http://127.0.0.1:8000/docs
```

## Frontend

```bash
cd client
npm install
npm run dev
```

Frontend usually runs at:

```text
http://localhost:5173
```