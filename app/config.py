import os
from typing import Any, Dict, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# class NacosSettings(BaseSettings):
#     server: str = Field(default="localhost:8848", env="NACOS_SERVER")
#     namespace: Optional[str] = Field(default=None, env="NACOS_NAMESPACE")
#     username: Optional[str] = Field(default=None, env="NACOS_USERNAME")
#     password: Optional[str] = Field(default=None, env="NACOS_PASSWORD")
#     data_id: str = Field(default="llm-agent-service.yaml", env="NACOS_DATA_ID")
#     group: str = Field(default="DEFAULT_GROUP", env="NACOS_GROUP")
#     service_name: str = os.getenv("SERVICE_NAME", "true")
#     service_port: int = os.getenv("SERVICE_PORT", "true")
#     service_ip: str = Field(default="127.0.0.1", env="NACOS_SERVICE_IP")
#     heartbeat_interval: int = Field(default=5, env="NACOS_HEARBEAT_INTERVAL")

#     model_config = SettingsConfigDict(env_prefix="NACOS_")


class AppSettings():
    def __init__(self,
                 data: Dict[str, Any] = None,
                 local_config_path: str = "data/config.yaml"
                 ):
        self._config: Dict[str, Any] = {}
        self._local_config_path = local_config_path
        self._init_config(data)

    def _init_config(self, data: Optional[Dict[str, Any]] = None) -> None:
        if data is None:
            self._config = self._load_local_config()
        else:
            self._config = data.copy()

        self._wrap_config()

    def _wrap_config(self) -> None:
        for key, value in self._config.items():
            if isinstance(value, dict):
                self._config[key] = AppSettings(data=value)
            elif isinstance(value, list):
                self._config[key] = [AppSettings(data=item) if isinstance(
                    item, dict) else item for item in value]

    def _load_local_config(self) -> Dict[str, Any]:
        try:
            with open(self._local_config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
        except yaml.YAMLError:
            return {}

    def merge_config(self, override: Dict[str, Any]) -> None:
        self._config = self._deep_merge(self._config, override)
        self._wrap_config()

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        merged = base.copy()
        for key, val in override.items():
            if isinstance(val, dict):
                existing = merged.get(key)
                if isinstance(existing, AppSettings):
                    merged[key] = existing._deep_merge(existing._config, val)
                else:
                    merged[key] = self._deep_merge(existing or {}, val)
            else:
                merged[key] = val
        return merged

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config

        for k in keys:
            value = value.get(k, {}) if isinstance(value, dict) else default
            if value is default:
                break
        return value if value is not None else default

    def __setitem__(self, key: str, value: Any) -> None:
        self._config[key] = value
        self._wrap_config()

    def __getattr__(self, name: str) -> Any:
        value = self.get(name)
        if value is None:
            raise AttributeError(f"config {name} not exsist")
        return value

    def __getitem__(self, key: str) -> Any:
        return self.get(key)


app_settings = AppSettings()
