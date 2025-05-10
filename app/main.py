#! /usr/bin/python3
# -*- coding: utf-8 -*-
import asyncio
from contextlib import asynccontextmanager
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.services.nacos import NacosManager
from app.config import nacos_settings
from app.core import probes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = NacosManager()

    try:
        await manager.register()
        app.state.nacos_manager = manager
        yield
        await manager.deregister()
    except Exception as e:
        logger.critical(f"Startup failed: {str(e)}")
        raise
    finally:
        await manager.deregister()

deploy_env = os.getenv("DEPLOY_ENV", "dev")
if deploy_env != "dev":
    app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)
else:
    app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/nacos/status")
async def nacos_status():
    manager = app.state.nacos_manager
    return {
        "registerd": manager.registered,
        "config": manager.current_config,
        "ip": manager.service_ip,
        "port": nacos_settings.service_port
    }

app.include_router(probes.router)

if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"][
        "fmt"
    ] = "%(asctime)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"][
        "fmt"
    ] = "%(asctime)s - %(levelname)s - %(message)s"
    uvicorn.run(app, host="0.0.0.0", port=nacos_settings.service_port)
