from typing import Dict

from fastapi import APIRouter

from app.core.logger import logger
from app.services.jtai import JTAI, FunctionManager
from app.services.tools import websearch_func

router = APIRouter(
    prefix="/agent",
    tags=["Agents"],
)

bot = JTAI(api_key="no_api_key",
           base_url="http://172.31.192.111:30518/scheduler/v3/")


@router.post("/websearch")
async def web_search(query: str):
    manager = FunctionManager()
    manager.register(websearch_func)

    messages = [
        {
            "role": "user",
            "content": query
        }
    ]

    tool_call_tracker: Dict[str, dict] = {}  # {tool_call_id: {name, args}}

    rounds = 0

    while True:
        rounds += 1
        if rounds > 5:
            logger.error("Max rounds exceed")
            break

        response = bot.chat(messages=messages, tools=manager.get_tools())
        logger.info(
            f"--- ROUND: {rounds} --- messages: {messages}, response: {response}")

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            for tool_call in tool_calls:
                result = manager.execute_tool_call(tool_call.model_dump())
                logger.info(f"Function Result: {result}")

                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tool_call.id,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                        "type": "function"
                    }]
                })

                messages.append({
                    "role": "tool",
                    "content": str(result),
                    "tool_call_id": tool_call.id
                })
        else:
            return response.choices[0].message.content
