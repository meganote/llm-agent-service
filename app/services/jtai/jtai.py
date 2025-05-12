import json
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Literal, Optional
from uuid import uuid4

from openai import APIConnectionError, APIError, OpenAI, RateLimitError
from typing_extensions import NotRequired, Required, TypedDict, TypeGuard

from app.core.logger import logger

from .chat_context import ChatContent, ChatMessage, ChatRole
from .models import ChatModels
from .types import DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN, NotGivenOr


@dataclass
class _ModelOptions:
    model: str | ChatModels
    user: NotGivenOr[str]
    temperature: NotGivenOr[float]
    parallel_tool_calls: NotGivenOr[bool]
    metadata: NotGivenOr[dict[str, str]]


class JTAI:
    def __init__(self,
                 *,
                 api_key: NotGivenOr[str] = NOT_GIVEN,
                 base_url: NotGivenOr[str] = NOT_GIVEN,
                 model: str | ChatModels = "jiutian-lan-comv3",
                 user: NotGivenOr[str] = NOT_GIVEN,
                 temperature: NotGivenOr[float] = NOT_GIVEN,
                 parallel_tool_calls: NotGivenOr[bool] = NOT_GIVEN,
                 metadata: NotGivenOr[dict[str, str]] = NOT_GIVEN,
                 ) -> None:

        self._opts = _ModelOptions(
            model=model,
            user=user,
            temperature=temperature,
            parallel_tool_calls=parallel_tool_calls,
            metadata=metadata,
        )

        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def create_converstaion() -> str:
        return str(uuid4()).replace("-", "")

    def chat(self,
             *,
             messages: List[ChatMessage],
             model: Optional[str] = None,
             stream: bool = False,
             temperature: Optional[float] = 0.7,
             max_tokens: Optional[int] = 1024,
             top_p: Optional[float] = None,
             stop: Optional[List[str]] = None,
             tools: Optional[List[str]] = None,
             tool_choice: Optional[List[str]] = "auto",
             response_format: Optional[List[str]] = None,
             ) -> Generator[ChatMessage, None, None] | str:

        extra_body = {
            "recordId": "123",
            "sourceType": "playground",
            "auditSwitch": False,
        }

        model = model if model is not None else self._opts.model

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                # response_format={ "type": "json_object" },
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                extra_body=extra_body,
                user="user",
                stream=stream,
                tools=tools,
                tool_choice=tool_choice,
            )

            return response
            # if stream:
            #     role: Any = None
            #     for chunk in response:
            #         LOGGER.debug(f"--- {chunk}")
            #         if not chunk.choices:
            #             continue
            #         delta = chunk.choices[0].delta
            #         if delta is None:
            #             continue

            #         role = delta.role if delta.role is not None else role
            #         content = delta.content if delta.content is not None else ""
            #         if content is None:
            #             continue

            #         yield format_chat_message(role, content)
            # else:
            #     print(f"--- {response}")
            #     message = response.choices[0].message
            #     if message is None:
            #         raise Exception("Empty response")
            #     response: ChatMessage = format_chat_message(
            #         role=(message.role if message.role is not None else "assistant"),
            #         message=(
            #             message.content if message.content is not None else ""),
            #     )

            #     if message.tool_calls is not None and len(message.tool_calls) > 0:
            #         response["role"] = "function"
            #         response["content"] = json.dumps(
            #             [
            #                 {
            #                     "id": t.id,
            #                     "name": t.function.name,
            #                     "arguments": json.loads(t.function.arguments),
            #                 }
            #                 for t in message.tool_calls
            #             ],
            #         )
            #     yield response

        except APIConnectionError as e:
            print("APIConnectionError: ", e)
            return None

        except RateLimitError as e:
            print("RateLimitError: ", e)
            return None

        except APIError as e:
            print("APIError: ", e)
            return None


def format_chat_message_content(
    content_type: Literal["text", "image_url"],
    content_value: str,
) -> ChatContent:
    if content_type == "image_url":
        return {
            "type": content_type,
            content_type: {
                "url": content_value,
            },
        }
    else:
        return {
            "type": content_type,
            content_type: content_value,
        }


def format_chat_message(
    role: ChatRole,
    message: str,
    image_urls: Optional[List[str]] = None,
    name: Optional[str] = None,
) -> ChatMessage:
    if not image_urls:
        msg: ChatMessage = {
            "role": role,
            "content": message,
        }
    else:
        msg: ChatMessage = {
            "role": role,
            "content": [
                format_chat_message_content("text", message),
            ]
            + [format_chat_message_content("image_url", image)
               for image in image_urls],
        }
    if name is not None:
        msg["name"] = name
    return msg
