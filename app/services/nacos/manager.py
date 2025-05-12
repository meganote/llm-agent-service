import asyncio
import logging
import socket
from typing import Any, Dict, Optional

import psutil
import yaml
from nacos import NacosClient

from app.config import nacos_settings
from app.core.logger import logger

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)


class NacosManager:
    def __init__(self):
        self._client = NacosClient(
            server_addresses=nacos_settings.server,
            namespace=nacos_settings.namespace,
            username=nacos_settings.username,
            password=nacos_settings.password,
        )
        self.heartbeat_task: Optional[asyncio.Task] = None
        self._registered = False
        self._current_config = {}

    @property
    def current_config(self):
        return self._current_config

    @property
    def service_ip(self) -> str:
        return nacos_settings.service_ip or self.get_local_ip()

    def get_client(self) -> NacosClient:
        return self._client

    def get_config(self) -> Dict[str, Any]:
        return self._current_config or self.load_initial_config()

    def load_initial_config(self) -> Dict[str, Any]:
        try:
            config_str = self._client.get_config(
                data_id=nacos_settings.data_id, group=nacos_settings.group
            )
            self._current_config = yaml.safe_load(config_str)
            logger.info(
                f"Successfully loaded config from Nacos: {self._current_config}")

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

        self.load_initial_config()
        logger.info(f"Config loaded: {self._current_config}")

        try:
            self._client.add_naming_instance(
                service_name=nacos_settings.service_name,
                ip=self.service_ip,
                port=nacos_settings.service_port,
                cluster_name="DEFAULT",
                metadata={
                    "heartbeat_interval": str(nacos_settings.heartbeat_interval),
                },
            )
            self._registered = True
            self.heartbeat_task = asyncio.create_task(self._send_heartbeat())

            logger.info(
                f"Service registered at {self.service_ip}:{nacos_settings.service_port}"
            )

            self._client.add_config_watcher(
                data_id=nacos_settings.data_id,
                group=nacos_settings.group,
                cb=self._handel_config_update,
            )

        except Exception as e:
            logger.error(f"Nacos registration failed: {str(e)}")
            raise RuntimeError("Nacos registration failed") from e

    async def deregister(self):
        if not self._registered:
            return

        try:
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    logger.debug("Heartbeat task cancelled")

            self._client.remove_naming_instance(
                service_name=nacos_settings.service_name,
                ip=self.service_ip,
                port=nacos_settings.service_port,
                cluster_name="DEFAULT",
            )

            self._registered = False
            logger.info("Service deregistered")
        except Exception as e:
            logger.error(f"Service deregistration failed: {str(e)}")
            raise RuntimeError("Nacos deregistration failed") from e

    def _handel_config_update(self, new_config):
        try:
            raw_content = new_config.get("raw_content")
            config_str = yaml.safe_load(raw_content)
            self._current_config = config_str
            logger.info(f"Config updated: {self._current_config}")
        except Exception as e:
            logger.error(f"Config update failed: {str(e)}")

    async def _send_heartbeat(self):
        while self._registered:
            try:
                if self._registered and self._client:
                    self._client.send_heartbeat(
                        service_name=nacos_settings.service_name,
                        ip=self.service_ip,
                        port=nacos_settings.service_port,
                        group_name=nacos_settings.group,
                    )
                    logger.debug("Heatbeat sent")
            except asyncio.CancelledError:
                logger.info("Heartbeat task exiting...")
                break
            except Exception as e:
                logger.error(f"Heartbeat failed: {str(e)}")

            await asyncio.sleep(nacos_settings.heartbeat_interval)


nacos_manager = NacosManager()
