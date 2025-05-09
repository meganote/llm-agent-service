#! /usr/bin/python3
# -*- coding: utf-8 -*-
import asyncio
from contextlib import asynccontextmanager
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.nacos import NacosManager


@asynccontextmanager
aysnc def lifespan(app: FastAPI):
    manager = NacosManager()
    await manager.register()
    yield
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


@app.get("/nacos/config")
async def show_config():
    return config_manager.get_config()


@app.get("/")  # 根路由
def root():
    return {"code": 200}


if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"][
        "fmt"
    ] = "%(asctime)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"][
        "fmt"
    ] = "%(asctime)s - %(levelname)s - %(message)s"
    uvicorn.run(app, host="0.0.0.0", port=5000)
