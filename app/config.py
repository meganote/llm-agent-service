from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NacosSettings(BaseSettings):
    server: str = Field(default="127.0.0.1:8848", env="NACOS_SERVER")
    namespace: str = Field(default="", env="NAMESPACE")
    username: str = Field(default="", env="NACOS_USERNAME")
    password: str = Field(default="", env="NACOS_PASSWORD")
    data_id: str = Field(default="fastapi-service", env="DATA_ID")
    group: str = Field(default="DEFAULT_GROUP", env="GROUP")
    service_name: str = Field(default="fastapi-service", env="SERVICE_NAME")
    service_port: int = Field(default=8000, env="SERVICE_PORT")
    service_ip: str = Field(default="127.0.0.1", env="SERVICE_IP")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


nacos_ettings = NacosSettings()
