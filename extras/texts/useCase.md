Our **working use case** should be:

# **CSV/Data Import Workflow Orchestrator**

In simple words:

> A user uploads a CSV file, and your platform orchestrates multiple background jobs to validate, parse, store, report, and notify — with retries, failure handling, logs, and workflow tracking.

This is the best use case because it is **easy to understand**, **free-tier friendly**, and still demonstrates **serious backend engineering**.

---

## The real-world problem

Many companies have internal tools where users upload bulk data:

- customer records
- employee data
- product catalog
- invoices
- transaction records
- leads
- inventory data
- bank statements
- insurance claims

Processing these files synchronously is bad because:

- files may be large
- validation can take time
- some rows may fail
- the request may timeout
- users need progress tracking
- failures should be retried
- reports should be generated
- notifications should be sent

So instead of doing everything in one API call, your platform breaks the process into workflow steps.

---

# Main Demo Use Case

## **Bulk Customer Import Workflow**

Example:

A business admin uploads a CSV file containing customer data.

CSV:

```csv
name,email,phone,city
Rahul,rahul@test.com,9876543210,Hyderabad
Priya,invalid-email,9123456789,Bangalore
Amit,amit@test.com,,Chennai
```

Your orchestrator runs this workflow:

```text
Upload CSV
   ↓
Validate File
   ↓
Parse Rows
   ↓
Validate Records
   ↓
Store Valid Records
   ↓
Generate Import Report
   ↓
Send Notification
```

---

## What each step does

### 1. Upload CSV

User uploads file from React dashboard.

Backend stores file metadata.

Status:

```text
UPLOADED
```

---

### 2. Validate File

Checks:

```text
Is file CSV?
Is file size allowed?
Are required columns present?
Is file empty?
```

Example required columns:

```text
name
email
phone
city
```

If invalid:

```text
Workflow FAILED
```

If valid:

```text
Move to parse step
```

---

### 3. Parse Rows

Reads CSV rows and converts them to JSON.

Example:

```json
[
  {
    "name": "Rahul",
    "email": "rahul@test.com",
    "phone": "9876543210",
    "city": "Hyderabad"
  },
  {
    "name": "Priya",
    "email": "invalid-email",
    "phone": "9123456789",
    "city": "Bangalore"
  }
]
```

---

### 4. Validate Records

Checks each row:

```text
name is required
email must be valid
phone must be valid
city is required
```

Invalid rows are not stored.

They are added to report.

Example:

```json
{
  "row_number": 2,
  "error": "Invalid email format"
}
```

---

### 5. Store Valid Records

Stores valid rows in database.

Example table:

```text
customers
```

Only valid records are inserted.

---

### 6. Generate Import Report

Creates summary:

```json
{
  "total_rows": 1000,
  "valid_rows": 920,
  "invalid_rows": 80,
  "status": "PARTIAL_SUCCESS"
}
```

Also stores row-level errors.

---

### 7. Send Notification

For free-tier demo, you do not need real email initially.

Just create notification record:

```text
CSV import completed: 920 valid, 80 invalid
```

Later you can add real email/webhook.

---

# Why this use case is perfect

Because it naturally needs orchestration.

A simple CRUD app cannot show this much.

This use case gives you:

| Concept | How it appears |
|---|---|
| Async processing | CSV processing happens in workers |
| AMQP | Jobs are published to RabbitMQ |
| Retries | Failed steps retry automatically |
| Dead-letter queue | Permanently failed jobs go to DLQ |
| Workflow state | Each workflow run has status |
| Step dependencies | Parse runs after validate, store runs after parse |
| Observability | Timeline logs for each step |
| Idempotency | Same step should not insert duplicate customers |
| React dashboard | User tracks import progress |
| Free-tier friendly | Small CSV files, DB, RabbitMQ all manageable |

---

# Your product story

You are not just building “a workflow engine.”

You are building:

> **A bulk data import platform powered by a reusable workflow orchestration engine.**

This sounds much more practical.

---

## Project positioning

Use this name/description:

# **FlowPilot**

> FlowPilot is a workflow orchestration platform for reliable bulk data processing. It allows users to upload CSV files and executes multi-step workflows asynchronously using RabbitMQ workers, with retries, dead-letter handling, execution logs, and real-time status tracking.

---

# Main workflow for Version 1

Use this exact workflow:

```text
Customer CSV Import Workflow
```

Steps:

```text
validate_file
parse_csv
validate_records
store_customers
generate_report
send_notification
```

Workflow JSON:

```json
{
  "name": "Customer CSV Import",
  "description": "Validates and imports customer records from CSV",
  "steps": [
    {
      "key": "validate_file",
      "task_type": "validate_file",
      "depends_on": []
    },
    {
      "key": "parse_csv",
      "task_type": "parse_csv",
      "depends_on": ["validate_file"]
    },
    {
      "key": "validate_records",
      "task_type": "validate_records",
      "depends_on": ["parse_csv"]
    },
    {
      "key": "store_customers",
      "task_type": "store_customers",
      "depends_on": ["validate_records"]
    },
    {
      "key": "generate_report",
      "task_type": "generate_report",
      "depends_on": ["store_customers"]
    },
    {
      "key": "send_notification",
      "task_type": "send_notification",
      "depends_on": ["generate_report"]
    }
  ]
}
```

---

# What the user sees in React

## Page 1: Upload CSV

```text
Upload Customer CSV
[Choose File]
[Start Import]
```

---

## Page 2: Workflow Runs

```text
Run ID      Workflow              Status       Started At
101         Customer CSV Import   RUNNING      10:20 AM
100         Customer CSV Import   SUCCESS      09:45 AM
99          Customer CSV Import   FAILED       09:10 AM
```

---

## Page 3: Run Details

```text
Customer CSV Import - Run #101

validate_file        SUCCESS
parse_csv            SUCCESS
validate_records     RUNNING
store_customers      PENDING
generate_report      PENDING
send_notification    PENDING
```

---

## Page 4: Report

```text
Import Report

Total rows: 1000
Valid rows: 920
Invalid rows: 80

Invalid Rows:
Row 12 - Invalid email
Row 25 - Missing phone
Row 49 - Name required
```

---

## Page 5: Dead Letter Jobs

```text
Job ID       Step              Error                   Retry Count
501          parse_csv         File read failed         3
502          send_notification Webhook timeout          3

[Retry]
```

---

# Where AMQP fits

Every workflow step becomes a message.

Example message:

```json
{
  "job_id": "job_501",
  "workflow_run_id": "run_101",
  "step_key": "parse_csv",
  "task_type": "parse_csv",
  "payload": {
    "file_id": "file_22"
  },
  "retry_count": 0
}
```

RabbitMQ handles delivery:

```text
FastAPI
  ↓ publish message
RabbitMQ exchange
  ↓ route message
Queue
  ↓ consume
Worker
  ↓ update DB
Workflow engine
  ↓ queue next step
```

---

# Later you can add more workflow use cases

Once the engine works for CSV import, you can add more workflows without changing the engine.

## Use case 2: Invoice Processing

```text
Upload Invoice
   ↓
Validate Invoice
   ↓
Extract Fields
   ↓
Store Invoice
   ↓
Notify Finance Team
```

## Use case 3: E-commerce Order Processing

```text
Create Order
   ↓
Validate Payment
   ↓
Reserve Inventory
   ↓
Generate Invoice
   ↓
Send Confirmation
```

## Use case 4: Report Generation

```text
Select Date Range
   ↓
Fetch Data
   ↓
Aggregate Metrics
   ↓
Generate PDF/CSV
   ↓
Send Email
```

But do **not** start with all of these.

Start with **Customer CSV Import**.

---

# Final answer

Your working use case is:

> **Bulk Customer CSV Import and Processing**

Your platform will let users upload a customer CSV file and then orchestrate background steps to validate the file, parse rows, validate records, store valid customers, generate an import report, and notify the user.

This gives you a clear product, not just a technical toy.

The orchestrator is the engine.  
The CSV import platform is the use case.