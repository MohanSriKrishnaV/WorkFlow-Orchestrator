from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FlowPilot"
    app_env: str = "development"
    app_debug: bool = True

    api_prefix: str = "/api/v1"


    rabbitmq_url: str = ""
    amqp_exchange: str = "flowpilot.exchange"
    amqp_queue: str = "flowpilot.test.queue"
    amqp_routing_key: str = "test.message"

    amqp_jobs_exchange: str = "flowpilot.jobs.exchange"
    amqp_jobs_queue: str = "flowpilot.jobs.queue"
    amqp_job_created_routing_key: str = "job.created"

    amqp_jobs_retry_exchange: str = "flowpilot.jobs.retry.exchange"

    amqp_jobs_retry_2s_queue: str = "flowpilot.jobs.retry.2s.queue"
    amqp_jobs_retry_4s_queue: str = "flowpilot.jobs.retry.4s.queue"
    amqp_jobs_retry_8s_queue: str = "flowpilot.jobs.retry.8s.queue"

    amqp_jobs_retry_2s_routing_key: str = "jobs.retry.2s"
    amqp_jobs_retry_4s_routing_key: str = "jobs.retry.4s"
    amqp_jobs_retry_8s_routing_key: str = "jobs.retry.8s"

    amqp_jobs_dlq_exchange: str = "flowpilot.jobs.dlq.exchange"
    amqp_jobs_dlq_queue: str = "flowpilot.jobs.dlq.queue"
    amqp_jobs_dlq_routing_key: str = "jobs.dlq"

    database_url: str = ""


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()