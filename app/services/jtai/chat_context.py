import time
from typing import Annotated, Dict, List, Literal, Union

from pydantic import BaseModel, Field

from .types import NOT_GIVEN, NotGivenOr, get_uuid, is_given

ChatRole = Literal["system", "user", "assistant", "function"]
ChatContent = Dict[Literal["type", "text", "image_url"],
                   str | Dict[Literal["url"], str]]


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: get_uuid("item_"))
    type: Literal["message"] = "message"
    role: ChatRole
    content: list[ChatContent]
    created: float = Field(default_factory=time.time)


class FunctionCall(BaseModel):
    id: str = Field(default_factory=lambda: get_uuid("item_"))
    type: Literal["function_call"] = "function_call"
    call_id: str
    arguments: str
    name: str


class FunctionCallOutput(BaseModel):
    id: str = Field(default_factory=lambda: get_uuid("item_"))
    name: str = Field(default="")
    type: Literal["function_call_output"] = Field(
        default="function_call_output")
    call_id: str
    output: str
    is_error: bool


ChatItem = Annotated[
    Union[ChatMessage, FunctionCall, FunctionCallOutput], Field(
        discriminator="type")
]


class ChatContext:
    def __init__(self,
                 items: NotGivenOr[list[ChatItem]] = NOT_GIVEN):
        self._items = list[ChatItem] = items if is_given(items) else []

    @classmethod
    def empty(cls):
        return cls([])

    @property
    def items(self) -> list[ChatItem]:
        return self._items

    def add_messages(
            self,
            *,
            role: ChatRole,
            content: str,
            id: NotGivenOr[str] = NOT_GIVEN,
            created: NotGivenOr[float] = NOT_GIVEN,
    ) -> ChatMessage:
        kwargs = {}
        if is_given(id):
            kwargs["id"] = id
        if is_given(created):
            kwargs["created"] = created

        if isinstance(content, str):
            message = ChatMessage(role=role, content=[content], **kwargs)
        else:
            message = ChatMessage(role=role, content=content, **kwargs)

        self._items.append(message)
        return message

    def truncate(
            self,
            *,

            max_items: int
    ):
        """Truncate to last N items in chat context.
        """
        instructions = next(
            (item for item in self._items if item.type ==
             "message" and item.role == "system"),
            None,
        )

        new_items = self._items[-max_items]
        # remove tool_calls
        while new_items and new_items[0].type in [
            "function_call",
            "function_call_output",
        ]:
            new_items.pop(0)

        if instructions:
            new_items.insert(0, instructions)

        self._items[:] = new_items
        return self
