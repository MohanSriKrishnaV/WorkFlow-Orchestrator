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

    amqp_jobs_queue: str = "flowpilot.jobs.queue"
    amqp_job_created_routing_key: str = "job.created"

    database_url: str = ""


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()