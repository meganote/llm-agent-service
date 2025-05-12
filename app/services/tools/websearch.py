import json
import os
from typing import Dict, List, Optional, Union

import httpx
from httpx_sse import SSEError, connect_sse
from pydantic import BaseModel, Field, ValidationError

# from app.config import VMP_SEARCH_URL
from app.core.logger import logger
from app.services.jtai import Function, FunctionParameter, FunctionResponse

VMP_SEARCH_URL = os.getenv(
    "VMP_SEARCH_URL", "http://172.31.192.111:30443/largemodel/search/dataLake/api/v2/kb/search/stream")


def websearch_callback(args: Dict) -> str:
    logger.info(f"websearch_callback args: {args}")
    keyword = args["keyword"]

    headers = {}

    body = {
        "query_sentence": keyword,
        "query_type_code": "1-2",
        "user_id": "user",
        "summarize": True
    }

    timeout = httpx.Timeout(
        connect=3.0,
        read=60.0,
        write=3.0,
        pool=3.0,
    )

    results = []

    try:
        with httpx.Client(timeout=timeout) as client:
            with connect_sse(client, method="POST", url=VMP_SEARCH_URL, headers=headers, json=body) as event_source:
                event_source.response.raise_for_status()

                for event in event_source.iter_sse():
                    try:
                        if event.event == "delta":
                            data = event.json()
                            search_response = FunctionResponse.model_validate(
                                data)
                            if search_response.status == "finish":
                                response = search_response.response
                                if response.type == "browser_result" and response.status == "finish":
                                    results = [
                                        item.text for item in response.result if item.text is not None]

                            # print(data)
                    except json.JSONDecodeError:
                        print("Not JSON:")
                        continue
                    except ValidationError as e:
                        print(e.errors())
                        continue

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP 错误: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"请求失败: {e}")
    except httpx.ConnectTimeout as e:
        logger.error(
            f"连接超时：{e.request.url} 无法在 {e.request.timeout.connect} 秒内建立连接")
    except httpx.ReadTimeout as e:
        logger.error(
            f"读取超时：{e.request.url} 在 {e.request.timeout.read} 秒内未收到数据")
    except SSEError as e:
        logger.error(f"返回格式错误：{e.request.url} 返回的不是SSE")

    return '\n\n'.join(results)


websearch_params = {
    "keyword": FunctionParameter(
        type="string",
        description="查询关键字",
        required=True
    )
}

websearch_func = Function(
    name="web_search",
    description="联网查询",
    parameters=websearch_params,
    callback=websearch_callback
)
