Start with **AMQP job runner first**, then evolve it into a workflow orchestrator. Since your main goals are **React + FastAPI + AMQP + free-tier deployment**, build it in small phases where every phase gives you a working demo.

Your final project should become:

> **FlowPilot — Free-tier friendly distributed workflow and job orchestration platform using React, FastAPI, RabbitMQ/AMQP, and PostgreSQL.**

Use **CloudAMQP for RabbitMQ**, **Supabase PostgreSQL**, **Vercel/Netlify for React**, and a free web host such as Render for the FastAPI API. Supabase’s free plan includes a limited Postgres database, CloudAMQP has a free/development RabbitMQ plan, Vercel has a Hobby plan for personal projects, and Render currently supports free web services/datastores with usage limits — but verify limits before final deployment because free-tier policies change. ([supabase.com](https://supabase.com/pricing?from=yinji.org&utm_source=openai))

---

# Final Architecture You Are Building Toward

```text
React Dashboard
      |
      v
FastAPI Backend
      |
      |---- PostgreSQL / Supabase
      |
      |---- RabbitMQ / CloudAMQP
                    |
                    v
              Worker Process
                    |
                    v
              Task Execution
```

For local development:

```text
React local
FastAPI local
Worker local
Supabase PostgreSQL
CloudAMQP RabbitMQ
```

For free-tier hosted demo:

```text
React hosted
FastAPI hosted
Supabase hosted
CloudAMQP hosted
Worker local OR demo worker endpoint
```

---

# Phase 0 — Project Setup

## Goal

Create the basic project structure and connect FastAPI + React.

## Backend structure

```text
flowpilot/
  backend/
    app/
      main.py
      config.py
      database.py
      models/
      schemas/
      routers/
      services/
      amqp/
      workers/
    requirements.txt
    .env.example

  frontend/
    src/
      pages/
      components/
      api/
      hooks/
    package.json

  README.md
```

## Backend packages

Use:

```text
fastapi
uvicorn
sqlalchemy
alembic
psycopg2-binary or asyncpg
pydantic
pydantic-settings
aio-pika
python-dotenv
```

## Frontend packages

Use:

```text
react
vite
axios
react-router-dom
@tanstack/react-query
tailwindcss
```

## Deliverables

By the end of this phase:

```text
GET /health
```

returns:

```json
{
  "status": "ok"
}
```

React shows:

```text
FlowPilot Dashboard
API Status: Online
```

## Do not add yet

Do not add:

```text
Docker
JWT
Workflow engine
Retries
Dashboard complexity
```

---

# Phase 1 — AMQP Hello World

## Goal

Learn AMQP properly before building workflow logic.

You need this flow:

```text
FastAPI endpoint
      |
      v
RabbitMQ exchange
      |
      v
Queue
      |
      v
Worker consumes message
```

## AMQP objects

Create:

```text
Exchange: flowpilot.exchange
Queue: flowpilot.jobs.queue
Routing key: job.created
```

## Backend endpoint

```text
POST /amqp/test
```

Request:

```json
{
  "message": "hello from api"
}
```

API publishes this to RabbitMQ.

## Worker

Create:

```text
backend/app/workers/test_worker.py
```

It should consume the message and print:

```text
Received message: hello from api
```

## AMQP concepts you learn

Focus on:

```text
connection
channel
exchange
queue
routing key
publish
consume
ack
```

## Acceptance criteria

This phase is complete when:

```text
1. You call POST /amqp/test
2. Message appears in RabbitMQ
3. Worker receives it
4. Worker acknowledges it
```

## Resume value

Not huge yet, but this gives you the AMQP foundation.

---

# Phase 2 — Persistent Job Queue

## Goal

Now every message should represent a real job stored in PostgreSQL.

Flow:

```text
POST /jobs
      |
      v
Create job in DB: PENDING
      |
      v
Publish message to RabbitMQ
      |
      v
Update job: QUEUED
      |
      v
Worker consumes
      |
      v
Update job: RUNNING
      |
      v
Update job: SUCCESS / FAILED
```

## Database table: `jobs`

```text
id
task_type
payload
status
retry_count
max_retries
error_message
created_at
updated_at
started_at
completed_at
```

## Job statuses

```text
PENDING
QUEUED
RUNNING
SUCCESS
FAILED
RETRYING
DEAD_LETTER
```

## API endpoints

```text
POST /jobs
GET /jobs
GET /jobs/{job_id}
```

## Example request

```json
{
  "task_type": "echo",
  "payload": {
    "text": "Hello FlowPilot"
  },
  "max_retries": 3
}
```

## Example response

```json
{
  "id": "job_123",
  "status": "QUEUED"
}
```

## Worker task types

Start with only 3 task types:

```text
echo
wait
random_fail
```

### `echo`

Just logs the payload.

### `wait`

Waits for given seconds.

```json
{
  "task_type": "wait",
  "payload": {
    "seconds": 5
  }
}
```

### `random_fail`

Fails randomly.

```json
{
  "task_type": "random_fail",
  "payload": {
    "failure_rate": 0.5
  }
}
```

## React page

Create:

```text
/jobs
```

Show:

```text
Job ID
Task Type
Status
Retry Count
Created At
Completed At
Error Message
```

Use polling every 5 seconds.

## Acceptance criteria

This phase is complete when:

```text
1. User creates job from API
2. Job is saved in DB
3. Message goes to RabbitMQ
4. Worker consumes message
5. DB status changes to SUCCESS or FAILED
6. React dashboard shows job status
```

---

# Phase 3 — Manual Retry

## Goal

Before automatic retries, implement manual retry.

Flow:

```text
FAILED job
   |
   v
POST /jobs/{id}/retry
   |
   v
Publish again to RabbitMQ
   |
   v
Worker retries job
```

## Endpoint

```text
POST /jobs/{job_id}/retry
```

## Rules

Only retry if status is:

```text
FAILED
DEAD_LETTER
```

Do not retry if status is:

```text
QUEUED
RUNNING
SUCCESS
```

## DB changes

Add:

```text
last_retried_at
```

## React update

On failed jobs, show button:

```text
Retry Job
```

## Acceptance criteria

This phase is complete when:

```text
1. random_fail job fails
2. User clicks Retry
3. Job is republished
4. Status changes from FAILED to QUEUED to RUNNING to SUCCESS/FAILED
```

## Interview value

You can explain:

> “Failed jobs are persisted. Retry does not create a new job blindly; it republishes the same job with updated retry metadata.”

---

# Phase 4 — AMQP Retry with Delay

## Goal

Now implement real AMQP retry using RabbitMQ queues.

You want:

```text
Main Queue
   |
   | failure
   v
Retry Queue with TTL
   |
   | after delay
   v
Main Queue again
```

## AMQP objects

Use:

```text
flowpilot.exchange
flowpilot.retry.exchange
flowpilot.dead.exchange
```

Queues:

```text
flowpilot.jobs.queue
flowpilot.retry.5s.queue
flowpilot.retry.30s.queue
flowpilot.dead.queue
```

Routing keys:

```text
job.execute
job.retry.5s
job.retry.30s
job.dead
```

## Retry strategy

Use:

```text
Retry 1: 5 seconds
Retry 2: 30 seconds
Retry 3: 60 seconds
After that: DEAD_LETTER
```

## Important AMQP learning

Learn and implement:

```text
basic_ack
basic_nack
dead-letter exchange
message TTL
routing keys
poison message handling
```

## DB updates

When job fails but can retry:

```text
status = RETRYING
retry_count = retry_count + 1
next_retry_at = now + delay
```

When retries exhausted:

```text
status = DEAD_LETTER
```

## React update

Add page:

```text
/dead-letter
```

Show:

```text
Job ID
Task Type
Retry Count
Final Error
Failed At
Retry Button
```

## Acceptance criteria

This phase is complete when:

```text
1. random_fail job fails
2. It goes to retry queue
3. After delay, it comes back to main queue
4. Retry count increases
5. After max retries, job goes to dead-letter queue
```

This is one of the **most important phases** for your resume.

---

# Phase 5 — Job Logs and Execution Timeline

## Goal

Add observability.

Every job should have logs.

## New table: `job_events`

```text
id
job_id
event_type
message
metadata_json
created_at
```

## Event types

```text
JOB_CREATED
JOB_QUEUED
JOB_STARTED
JOB_SUCCESS
JOB_FAILED
JOB_RETRY_SCHEDULED
JOB_DEAD_LETTERED
JOB_MANUAL_RETRY
```

## API endpoints

```text
GET /jobs/{job_id}/events
```

## React update

Job details page should show:

```text
Timeline

10:00:01 JOB_CREATED
10:00:02 JOB_QUEUED
10:00:05 JOB_STARTED
10:00:07 JOB_FAILED
10:00:07 JOB_RETRY_SCHEDULED
10:00:12 JOB_STARTED
10:00:13 JOB_SUCCESS
```

## Acceptance criteria

This phase is complete when every job has a visible timeline.

## Resume value

This lets you say:

> “Implemented persistent execution logs and timeline tracking for asynchronous jobs.”

---

# Phase 6 — Workflow Definitions

## Goal

Move from individual jobs to workflows.

A workflow is a set of steps.

Example:

```json
{
  "name": "CSV Processing Workflow",
  "description": "Validates, parses, stores, and reports CSV data",
  "steps": [
    {
      "key": "validate_csv",
      "task_type": "validate_csv",
      "depends_on": []
    },
    {
      "key": "parse_csv",
      "task_type": "parse_csv",
      "depends_on": ["validate_csv"]
    },
    {
      "key": "store_records",
      "task_type": "store_records",
      "depends_on": ["parse_csv"]
    },
    {
      "key": "send_notification",
      "task_type": "send_notification",
      "depends_on": ["store_records"]
    }
  ]
}
```

## New table: `workflows`

```text
id
name
description
definition_json
is_active
created_at
updated_at
```

## API endpoints

```text
POST /workflows
GET /workflows
GET /workflows/{workflow_id}
PUT /workflows/{workflow_id}
DELETE /workflows/{workflow_id}
```

## Validation rules

Before saving workflow:

```text
1. Every step must have unique key
2. depends_on must reference existing steps
3. No circular dependency
4. task_type must be supported
```

## React update

Add pages:

```text
/workflows
/workflows/new
/workflows/:id
```

For now, use a JSON editor textarea.

Do not build drag-and-drop UI.

## Acceptance criteria

This phase is complete when:

```text
1. User can create workflow JSON
2. Backend validates it
3. Workflow is stored in DB
4. React shows workflow details
```

---

# Phase 7 — Sequential Workflow Execution

## Goal

Run a workflow step by step.

Flow:

```text
Start workflow run
      |
      v
validate_csv
      |
      v
parse_csv
      |
      v
store_records
      |
      v
send_notification
```

## New table: `workflow_runs`

```text
id
workflow_id
status
input_payload
created_at
started_at
completed_at
```

## New table: `workflow_steps`

```text
id
workflow_run_id
step_key
task_type
status
depends_on
payload
job_id
retry_count
error_message
started_at
completed_at
```

## Workflow run statuses

```text
PENDING
RUNNING
SUCCESS
FAILED
CANCELLED
```

## Step statuses

```text
PENDING
QUEUED
RUNNING
SUCCESS
FAILED
SKIPPED
```

## API endpoints

```text
POST /workflows/{workflow_id}/runs
GET /workflow-runs
GET /workflow-runs/{run_id}
GET /workflow-runs/{run_id}/steps
```

## Engine logic

When workflow starts:

```text
1. Create workflow_run
2. Create workflow_steps
3. Find steps with no dependencies
4. Queue first step
```

When a step succeeds:

```text
1. Mark step SUCCESS
2. Find next dependent steps
3. If dependencies are complete, queue next step
4. If no steps left, mark workflow SUCCESS
```

When a step fails permanently:

```text
1. Mark step FAILED
2. Mark workflow FAILED
3. Do not run dependent steps
```

## Acceptance criteria

This phase is complete when:

```text
1. User starts a workflow
2. First step is queued
3. Worker processes it
4. Next step starts automatically
5. Workflow eventually becomes SUCCESS or FAILED
```

---

# Phase 8 — Real CSV Processing Demo

## Goal

Make the project understandable to recruiters.

Build one real workflow:

```text
Upload CSV
   |
   v
Validate CSV
   |
   v
Parse CSV
   |
   v
Store Records
   |
   v
Generate Report
   |
   v
Notify User
```

## New table: `uploaded_files`

```text
id
file_name
file_path
size_bytes
uploaded_at
```

## New table: `csv_records`

```text
id
workflow_run_id
row_number
data_json
is_valid
error_message
created_at
```

## New table: `reports`

```text
id
workflow_run_id
total_rows
valid_rows
invalid_rows
report_json
created_at
```

## Task types

Implement:

```text
validate_csv
parse_csv
store_records
generate_report
send_notification
```

## Free-tier constraint

Keep file size small:

```text
Max CSV size: 1 MB initially
Max rows: 1,000 initially
```

## React update

Add:

```text
/csv-upload
```

User uploads CSV and starts workflow.

## Acceptance criteria

This phase is complete when:

```text
1. User uploads CSV
2. Workflow starts
3. Steps run in background
4. Dashboard shows progress
5. Final report is generated
```

This becomes your main demo.

---

# Phase 9 — Parallel DAG Execution

## Goal

Support workflows where independent steps run in parallel.

Example:

```text
validate_csv
    |
    |----------------|
    v                v
store_records   generate_report
    |                |
    |----------------|
            |
            v
     send_notification
```

## Workflow JSON

```json
{
  "name": "Parallel CSV Workflow",
  "steps": [
    {
      "key": "validate_csv",
      "task_type": "validate_csv",
      "depends_on": []
    },
    {
      "key": "store_records",
      "task_type": "store_records",
      "depends_on": ["validate_csv"]
    },
    {
      "key": "generate_report",
      "task_type": "generate_report",
      "depends_on": ["validate_csv"]
    },
    {
      "key": "send_notification",
      "task_type": "send_notification",
      "depends_on": ["store_records", "generate_report"]
    }
  ]
}
```

## Engine logic

After each step succeeds:

```text
Find all PENDING steps
For each step:
  Check if all dependencies are SUCCESS
  If yes, queue it
```

## Acceptance criteria

This phase is complete when multiple independent steps can run at the same time.

## Resume value

Now you can say:

> “Implemented DAG-based workflow execution with dependency resolution and parallel step scheduling.”

---

# Phase 10 — Idempotency and Duplicate Protection

## Goal

Handle duplicate RabbitMQ message delivery safely.

RabbitMQ can redeliver messages, so your worker should not process completed jobs again.

## Add field to `jobs`

```text
idempotency_key
```

Example:

```text
workflow_run_123_step_validate_csv
```

## Rules

Before worker executes a job:

```text
1. Fetch job by ID
2. If job status is SUCCESS, ack and skip
3. If job status is RUNNING and recently started, ack or reject based on strategy
4. If job status is QUEUED/RETRYING, process
```

## DB constraint

Add unique constraint:

```text
UNIQUE(idempotency_key)
```

## Acceptance criteria

This phase is complete when publishing the same job message twice does not execute the task twice.

## Interview explanation

Say:

> “The system is designed for at-least-once delivery. Since RabbitMQ can redeliver messages, every job has an idempotency key and workers check persisted state before executing.”

This is a very strong backend interview point.

---

# Phase 11 — Authentication

## Goal

Add basic user accounts.

Do this after orchestration works.

## Tables

```text
users
```

Fields:

```text
id
name
email
password_hash
role
created_at
```

## Roles

Keep simple:

```text
USER
ADMIN
```

## API endpoints

```text
POST /auth/register
POST /auth/login
GET /auth/me
```

## Protected resources

Each user should own:

```text
workflows
workflow_runs
uploaded_files
```

## React pages

```text
/login
/register
/profile
```

## Acceptance criteria

This phase is complete when:

```text
1. User can register
2. User can login
3. JWT is stored in frontend
4. User sees only their workflows and jobs
```

Do not build complex RBAC now.

---

# Phase 12 — Scheduling

## Goal

Allow workflows to run automatically later.

Start simple with interval scheduling.

## New table: `schedules`

```text
id
workflow_id
enabled
schedule_type
interval_seconds
next_run_at
last_run_at
created_at
updated_at
```

## Scheduler process

Create:

```text
backend/app/scheduler.py
```

Logic:

```text
Every 60 seconds:
  Find schedules where next_run_at <= now
  Start workflow run
  Update next_run_at
```

## API endpoints

```text
POST /workflows/{workflow_id}/schedules
GET /schedules
PATCH /schedules/{schedule_id}/enable
PATCH /schedules/{schedule_id}/disable
```

## Free-tier constraint

Do not schedule too frequently.

Minimum interval:

```text
5 minutes or 15 minutes
```

## Acceptance criteria

This phase is complete when a workflow can run automatically on interval.

---

# Phase 13 — Hosted Free-Tier Demo Mode

## Goal

Make sure recruiters can use the project even if your worker is not always running.

This is important because free hosting for always-on background workers can be unreliable.

## Add demo worker endpoints

```text
POST /demo/process-next-job
POST /demo/process-pending-jobs?limit=5
```

These endpoints should:

```text
1. Pull a message from RabbitMQ
2. Process it
3. Update DB
4. Return result
```

## React button

Add:

```text
Process Next Job
Process Pending Jobs
```

## README explanation

Write clearly:

```text
Production Mode:
- Dedicated worker consumes RabbitMQ messages continuously.

Free-Tier Demo Mode:
- Since many free platforms do not provide reliable always-on workers,
  the hosted demo includes manual worker endpoints to process queued jobs.
```

## Acceptance criteria

This phase is complete when:

```text
1. App is deployed
2. User can create job/workflow
3. User can click Process Pending Jobs
4. Status updates in dashboard
```

This makes your project practical for free-tier deployment.

---

# Phase 14 — Deployment

## Suggested deployment

| Component | Free-tier option |
|---|---|
| React | Vercel or Netlify |
| FastAPI | Render free web service |
| PostgreSQL | Supabase |
| RabbitMQ | CloudAMQP |
| Worker | Local first, optional hosted later |
| CI/CD | GitHub Actions |

Render’s free services can spin down or have usage limits, so design the demo so it can recover after sleep. ([render.com](https://render.com/docs/free?utm_source=openai))

## Deployment order

Deploy in this order:

```text
1. Supabase PostgreSQL
2. CloudAMQP RabbitMQ
3. FastAPI backend
4. React frontend
5. Optional worker
```

## Environment variables

```text
DATABASE_URL=
RABBITMQ_URL=
JWT_SECRET=
FRONTEND_URL=
ENVIRONMENT=
```

## Acceptance criteria

This phase is complete when:

```text
1. Frontend is publicly accessible
2. Backend health endpoint works
3. Backend connects to DB
4. Backend connects to RabbitMQ
5. User can run demo workflow
```

---

# Phase 15 — Dockerization

You said dockerize later — correct.

Do Docker only after your local app works.

## Docker services

```text
api
worker
scheduler
frontend
postgres
rabbitmq
```

## Files

```text
backend/Dockerfile
frontend/Dockerfile
docker-compose.yml
```

## Why Docker later?

Because first you should understand:

```text
FastAPI
RabbitMQ
AMQP
Worker process
PostgreSQL
Workflow execution
```

Docker should make the project reproducible, not hide the fundamentals.

## Acceptance criteria

This phase is complete when:

```bash
docker compose up
```

starts:

```text
React
FastAPI
PostgreSQL
RabbitMQ
Worker
Scheduler
```

---

# Phase 16 — Polish for Resume

## README sections

Your README should include:

```text
1. Project overview
2. Why this project exists
3. Architecture diagram
4. Tech stack
5. AMQP design
6. Database schema
7. Workflow lifecycle
8. Retry and dead-letter design
9. Idempotency strategy
10. Free-tier deployment strategy
11. Screenshots
12. API documentation
13. Local setup
14. Docker setup
15. Future improvements
```

## Add architecture diagram

Example:

```text
React Dashboard
      |
      v
FastAPI API
      |
      |------ PostgreSQL
      |
      |------ RabbitMQ Exchange
                    |
                    v
              Job Queue
                    |
                    v
              Worker Pool
                    |
                    v
              Job Events + Status
```

## Add screenshots

Include:

```text
Jobs dashboard
Workflow list
Workflow run details
Execution timeline
Dead-letter queue
CSV report
```

## Final resume bullet

Use:

> Built **FlowPilot**, a distributed workflow orchestration platform using React, FastAPI, RabbitMQ/AMQP, and PostgreSQL, supporting asynchronous job execution, DAG-based workflows, retries with delayed queues, dead-letter handling, persistent execution logs, idempotency, JWT authentication, and free-tier cloud deployment.

---

# Recommended Timeline

## Week 1 — AMQP + Jobs

```text
Phase 0
Phase 1
Phase 2
```

Deliverable:

```text
API creates job, RabbitMQ queues it, worker processes it, DB updates status.
```

---

## Week 2 — Retry System

```text
Phase 3
Phase 4
Phase 5
```

Deliverable:

```text
Retries, delayed retry queues, dead-letter queue, job timeline.
```

---

## Week 3 — Workflow Engine

```text
Phase 6
Phase 7
```

Deliverable:

```text
Sequential workflow execution.
```

---

## Week 4 — CSV Demo + DAG

```text
Phase 8
Phase 9
```

Deliverable:

```text
Real CSV processing workflow with parallel DAG support.
```

---

## Week 5 — Production Concepts

```text
Phase 10
Phase 11
Phase 12
```

Deliverable:

```text
Idempotency, auth, user-owned workflows, scheduling.
```

---

## Week 6 — Deployment + Polish

```text
Phase 13
Phase 14
Phase 15
Phase 16
```

Deliverable:

```text
Hosted demo, Docker setup, README, screenshots, resume-ready project.
```

---

# Start Here: Your First 3 Tasks

Do these first, nothing else:

## Task 1

Create FastAPI backend:

```text
GET /health
```

## Task 2

Connect to CloudAMQP and publish message:

```text
POST /amqp/test
```

## Task 3

Create worker:

```text
python -m app.workers.test_worker
```

Worker should consume and acknowledge the message.

Once this works, your AMQP foundation is ready.

Do **not** start with React UI, Docker, auth, or workflow DAG. Start with the queue.