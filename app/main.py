#! /usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import os
from contextlib import asynccontextmanager

import shortuuid
import uvicorn
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import nacos_settings
from app.core import probes
from app.routers import agent
from app.services.nacos import nacos_manager

nacos: bool = os.getenv("NACOS", "true").lower() == "true"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if nacos:
            await nacos_manager.register()
            app.state.nacos_manager = nacos_manager
            yield
            await nacos_manager.deregister()
        else:
            app.state.nacos_manager = None
            yield
    except Exception as e:
        logger.critical(f"Startup failed: {str(e)}")
        raise
    finally:
        if nacos_manager:
            await nacos_manager.deregister()


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
app.add_middleware(CorrelationIdMiddleware, generator=lambda: shortuuid.uuid())


@app.get("/nacos/status")
async def nacos_status():
    if hasattr(app.state, "nacos_manager"):
        manager = app.state.nacos_manager
        data = {
            "registerd": manager._registered,
            "config": manager.current_config,
            "ip": manager.service_ip,
            "port": nacos_settings.service_port,
        }
        return JSONResponse(content=data, status_code=200)
    else:
        data = {
            "registerd": "unkown",
            "config": "unkown",
            "ip": "unkown",
            "port": nacos_settings.service_port,
        }

        return JSONResponse(content=data, status_code=500)


app.include_router(probes.router)
app.include_router(agent.router)

if __name__ == "__main__":
    # log_config = uvicorn.config.LOGGING_CONFIG
    # log_config["formatters"]["access"][
    #     "fmt"
    # ] = "%(asctime)s - %(levelname)s - %(message)s"
    # log_config["formatters"]["default"][
    #     "fmt"
    # ] = "%(asctime)s - %(levelname)s - %(message)s"
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=nacos_manager.service_port,
        log_level="debug",
    )
