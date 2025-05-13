import asyncio
import logging
import os
import socket
from typing import Any, Dict, Optional

import psutil
import yaml
from nacos import NacosClient

from app.config import app_settings

# from app.config import nacos_settings
# from app.core.logger import logger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NacosManager:
    def __init__(self):
        self._client = None
        self.server = os.getenv("NACOS_SERVER", "localhost:8848")
        self.namespace = os.getenv("NACOS_NAMESPACE", "dev")
        self.username = os.getenv("NACOS_USERNAME", "nacos")
        self.password = os.getenv("NACOS_PASSWORD", "nacos")
        self.data_id = os.getenv("NACOS_DATA_ID", "data.yaml")
        self.group = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")
        self.heartbeat_interval = os.getenv("NACOS_HEARBEAT_INTERVAL", 5)

        self.heartbeat_task: Optional[asyncio.Task] = None
        self._registered = False
        self._service_ip = self.get_local_ip()
        self._current_config = {}

    def _init_client(self):
        if self._client is None:
            self._client = NacosClient(
                server_addresses=self.server,
                namespace=self.namespace,
                username=self.username,
                password=self.password,
            )

    @property
    def current_config(self):
        return self._current_config

    @property
    def service_ip(self) -> str:
        return self._service_ip or self.get_local_ip()

    def get_client(self) -> NacosClient:
        return self._client

    def get_config(self) -> Dict[str, Any]:
        return self._current_config or self.load_initial_config()

    def load_initial_config(self) -> Dict[str, Any]:
        try:
            config_str = self._client.get_config(
                data_id=self.data_id, group=self.group
            )
            self._current_config = yaml.safe_load(config_str)
            logger.info(
                f"Successfully loaded config from Nacos: {self._current_config}")
            app_settings.merge_config(self._current_config)
            logger.info(f"App Config updated: {app_settings.foo.bar}")

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing failed: {str(e)}")
            self._current_config = {"error": "fallback_config"}

        except Exception as e:
            logger.error(f"Config loading failed: {str(e)}")
            self._current_config = {"error": "fallback_config"}

        return self._current_config

    @staticmethod
    def get_local_ip() -> str:
        try:
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith(
                        "127."
                    ):
                        return addr.address
            raise Exception(-403, "no valid non-loopback IPv4 interface found")
        except socket.gaierror as err:
            raise Exception(
                -403, f"failed to query local IP address, error: {str(err)}"
            )

    async def register(self):
        if self._registered:
            return

        self._init_client()

        self.load_initial_config()
        logger.info(f"Config loaded: {self._current_config}")

        logger.info(
            f"Registering at {self.service_ip}:{app_settings.app.port}"
        )
        try:
            self._client.add_naming_instance(
                service_name=app_settings.app.name,
                ip=self.service_ip,
                port=app_settings.app.port,
                cluster_name="DEFAULT",
                metadata={
                    "heartbeat_interval": str(self.heartbeat_interval),
                },
            )
            self._registered = True
            self.heartbeat_task = asyncio.create_task(self._send_heartbeat())

            logger.info(
                f"Service registered at {self.service_ip}:{app_settings.app.port}"
            )

            self._client.add_config_watcher(
                data_id=self.data_id,
                group=self.group,
                cb=self._on_nacos_config_changed,
            )

        except Exception as e:
            logger.error(f"Nacos registration failed: {str(e)}")
            raise RuntimeError("Nacos registration failed") from e

    async def deregister(self):
        if not self._registered:
            return

        self._init_client()
        try:
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    logger.debug("Heartbeat task cancelled")

            self._client.remove_naming_instance(
                service_name=app_settings.app.name,
                ip=self.service_ip,
                port=app_settings.app.port,
                cluster_name="DEFAULT",
            )

            self._registered = False
            logger.info("Service deregistered")
        except Exception as e:
            logger.error(f"Service deregistration failed: {str(e)}")
            raise RuntimeError("Nacos deregistration failed") from e

    def _on_nacos_config_changed(self, new_config):
        try:
            raw_content = new_config.get("raw_content")
            config_str = yaml.safe_load(raw_content)
            self._current_config = config_str
            app_settings.merge_config(config_str)
            logger.info(f"App Config updated: {app_settings.foo.bar}")
        except Exception as e:
            logger.error(f"Config update failed: {str(e)}")

    async def _send_heartbeat(self):
        while self._registered:
            try:
                if self._registered and self._client:
                    self._client.send_heartbeat(
                        service_name=app_settings.app.name,
                        ip=self.service_ip,
                        port=app_settings.app.port,
                        group_name=self.group,
                    )
                    logger.debug("Heatbeat sent")
            except asyncio.CancelledError:
                logger.info("Heartbeat task exiting...")
                break
            except Exception as e:
                logger.error(f"Heartbeat failed: {str(e)}")

            await asyncio.sleep(self.heartbeat_interval)


nacos_manager = NacosManager()
