import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NacosSettings(BaseSettings):
    server: str = Field(default="localhost:8848", env="NACOS_SERVER")
    namespace: Optional[str] = Field(default=None, env="NACOS_NAMESPACE")
    username: Optional[str] = Field(default=None, env="NACOS_USERNAME")
    password: Optional[str] = Field(default=None, env="NACOS_PASSWORD")
    data_id: str = Field(default="fastapi-service", env="NACOS_DATA_ID")
    group: str = Field(default="DEFAULT_GROUP", env="NACOS_GROUP")
    service_name: str = os.getenv("SERVICE_NAME", "true")
    service_port: int = os.getenv("SERVICE_PORT", "true")
    service_ip: str = Field(default="127.0.0.1", env="NACOS_SERVICE_IP")
    heartbeat_interval: int = Field(default=5, env="NACOS_HEARBEAT_INTERVAL")

    model_config = SettingsConfigDict(env_prefix="NACOS_")


nacos_settings = NacosSettings()
print("[DEBUG] Loaded config:", nacos_settings.model_dump())
