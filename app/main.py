#! /usr/bin/python3
# -*- coding: utf-8 -*-
from contextlib import asynccontextmanager
import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fastapi.middleware.cors import CORSMiddleware

from app.services.nacos import NacosManager
from app.config import nacos_settings
from app.core import probes, logger
from asgi_correlation_id import CorrelationIdMiddleware
import shortuuid

nacos: bool = os.getenv("NACOS", "true").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = None

    try:
        if nacos:
            manager = NacosManager()

            await manager.register()
            app.state.nacos_manager = manager
            yield
            await manager.deregister()
        else:
            app.state.nacos_manager = None
            yield
    except Exception as e:
        logger.critical(f"Startup failed: {str(e)}")
        raise
    finally:
        if manager:
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
app.add_middleware(CorrelationIdMiddleware, generator=lambda: shortuuid.uuid())


@app.get("/nacos/status")
async def nacos_status():
    if hasattr(app.state, "nacos_manager"):
        manager = app.state.nacos_manager
        data = {
            "registerd": manager.registered,
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
        port=nacos_settings.service_port,
        # log_config=None,
        # log_level=None,
    )
