import asyncio
import json
import logging
import socket
from typing import Any, Dict

import nacos
import psutil

from app.config import nacos_settings

logger = logging.getLogger(__name__)


class NacosManager:
    def __init__(self):
        self._client = nacos.NacosClient(
            server_addresses=nacos_settings.nacos_server,
            namespace=nacos_settings.namespace,
            username=nacos_settings.username,
            password=nacos_settings.password
        )

    def get_client(self) -> nacos.NacosClient:
        return self._client

    def get_config(self) -> Dict[str, Any]:
        return self._current_config or self.load_initial_config()

    def load_initial_config(self) -> Dict[str, Any]:
        try:
            config_str = self._client.get_config(
                data_id=nacos_settings.data_id,
                group=nacos_settings.group
            )
            self._current_config = json.loads(config_str)
            logger.info("Successfully loaded config from Nacos")

        except Exception as e:
            logger.error(f"Config loading failed: {str(e)}")
            self._current_config = {"error": "fallback_config"}

        return self._current_config

    @staticmethod
    def get_local_ip():
        try:
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        return addr.address
            raise Exception(-403, "no valid non-loopback IPv4 interface found")
        except socket.gaierror as err:
            raise Exception(-403,
                            f"failed to query local IP address, error: {str(err)}")

    def register_service(self):
        try:
            self._client.add_naming_instance(
                service_name=nacos_settings.service_name,
                ip=nacos_settings.service_ip or self.get_local_ip(),
                port=nacos_settings.service_port,
                cluster_name="DEFAULT"
            )
            logger.info("Service registered successfully")
        except Exception as e:
            logger.error(f"Service registration failed: {str(e)}")

    def deregister_service(self):
        try:
            self._client.remove_naming_instance(
                service_name=nacos_settings.service_name,
                ip=nacos_settings.service_ip or self.get_local_ip(),
                port=nacos_settings.service_port,
                cluster_name="DEFAULT"
            )
            logger.info("Service deregistered successfully")
        except Exception as e:
            logger.error(f"Service deregistration failed: {str(e)}")

    def watch_config(self, callback):
        self._client.add_config_watcher(
            data_id=nacos_settings.data_id,
            group=nacos_settings.group,
            callback=callback
        )

    async def start_heartbeat(self):
        loop = asyncio.get_event_loop()
        while True:
            await asyncio.sleep(5)
            try:
                await loop.run_in_executor(
                    None,
                    self._client.send_heartbeat,
                    nacos_settings.service_name,
                    nacos_settings.service_ip,
                    nacos_settings.service_port,
                    None,
                    nacos_settings.group
                )
                logger.debug("Heartbeat sent successfully")
            except Exception as e:
                logger.error(f"Heartbeat failed: {str(e)}")


manager = NacosManager()
