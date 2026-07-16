cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# uvicorn app.main:app --reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
run worker:
python -m app.workers.test_worker
python -m app.workers.outbox_publisher

running scripts:
source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
venv/bin/python -m app.workers.job_worker
venv/bin/python -m app.workers.outbox_publisher


scripts:
venv/bin/python  


 $ python scripts/random_workflow_trigger.py \
  --api-base http://127.0.0.1:8000/api/v1 \
  --min 5 --max 10 --file-id-min 19 --file-id-max 23
docker compose up -d

promethues:
http_requests_total
http_request_duration_seconds_count
http_server_requests_total
process_cpu_seconds_total
