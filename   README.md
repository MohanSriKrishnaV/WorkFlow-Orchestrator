# FlowPilot

FlowPilot is a workflow orchestration platform for reliable bulk CSV processing.

It uses:

- React frontend
- FastAPI backend
- PostgreSQL for persistent state
- RabbitMQ/AMQP for background job delivery
- Worker process for asynchronous task execution

## Current Status

Phase 0: Initial backend setup.

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
```

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