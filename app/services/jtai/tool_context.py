import json
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError

from app.core.logger import logger


class FunctionParameter:
    def __init__(
        self,
        type: str = "string",
        description: str = "",
        enum: Optional[List[str]] = None,
        required: bool = True
    ):
        self.type = type
        self.description = description
        self.enum = enum
        self.required = required


class Function:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, FunctionParameter],
        callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        async_callback: Optional[Callable[[Dict[str, Any]], Any]] = None
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.callback = callback

    def to_openai_tool(self) -> Dict:
        properties = {}
        required = []
        for param_name, param in self.parameters.items():
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param_name] = prop
            if param.required:
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def _validate_args(self, args: Dict[str, Any]) -> Optional[str]:
        for param in self.parameters.required:
            if param not in args:
                return f"Error: Missing required parameter '{param}'"
        for param, prop in self.parameters.properties.items():
            if "enum" in prop and args.get(param) not in prop["enum"]:
                return f"Error: Invalid value for '{param}'"
        return None

    def execute(self, arguments: str) -> str:
        try:
            args = json.loads(arguments)
            logger.info(f"- Function - {self.name} args: {args}")
            # if error := self._validate_args(args):
            #     return error
            if self.callback is None:
                return "Error: No synchronous callback defined"

            # for param_name, param in self.parameters.items():
            #     if param.required and param_name not in args:
            #         return f"Error: Missing required parameter '{param_name}'"
            #     if param.enum and args.get(param_name) not in param.enum:
            #         return f"Error: Invalid value for '{param_name}'"

            result = self.callback(args)
            return str(result)
        except json.JSONDecodeError as e:
            logger.error(e)
            return f"Error: Invalid JSON arguments. {str(e)}"
        except Exception as e:
            logger.error(e)
            return f"Error: {str(e)}"

    async def async_execute(self, arguments: str) -> str:
        try:
            args = json.loads(arguments)
            if error := self._validate_args(args):
                return error
            if self.async_callback is None:
                return "Error: No asynchronous callback defined"

            result = await self.async_callback(args)
            return str(result)
        except json.JSONDecodeError:
            return "Error: Invalid JSON arguments"
        except Exception as e:
            return f"Error: {str(e)}"


class FunctionManager:
    def __init__(self):
        self.functions: Dict[str, Function] = {}

    def register(self, func: Function) -> None:
        if func.name in self.functions:
            raise ValueError(f"Function {func.name} already exists")
        self.functions[func.name] = func

    def get_tools(self) -> List[Dict]:
        return [func.to_openai_tool() for func in self.functions.values()]

    def execute_tool_call(self, tool_call: Dict) -> str:
        func_name = tool_call["function"]["name"]
        if func_name not in self.functions:
            return f"Error: Function {func_name} not found"
        return self.functions[func_name].execute(tool_call["function"]["arguments"])


class AsyncFunctionManager:
    def __init__(self):
        self.functions: Dict[str, Function] = {}

    def register(self, func: Function) -> None:
        if func.name in self.functions:
            raise ValueError(f"Tool {func.name} already exists")
        self.functions[func.name] = func

    async def execute_async_tool_call(self, tool_call: Dict) -> str:
        func_name = tool_call["function"]["name"]
        if func_name not in self.tools:
            return f"Error: Function {func_name} not found"
        function = self.functions[func_name]
        return await function.async_execute(tool_call["function"]["arguments"])


class FunctionResult(BaseModel):
    text: Optional[str] = None
    id: Optional[int] = None
    file_type: Optional[str] = None
    file_info: Optional[Dict[str, str]] = None


class FunctionParts(BaseModel):
    type: str = Field(..., enum=["text", "code", "code_result", "browser",
                      "browser_result", "image", "tool", "tool_result", "video", "memory", "thinking"])
    title: Optional[str] = None
    text: Union[str, Dict, None] = None
    status: str = Field(None, enum=["init", "finish", "error", "terminate"])
    result: Optional[List[FunctionResult]] = None


class FunctionResponse(BaseModel):
    response: FunctionParts = Field(alias="response")
    role: str = Field(alias="role")
    status: str = Field(alias="status")
    finished: str = Field(None, enum=["Stop", "Length", "Error"])
    usage: Optional[Dict[str, int]] = Field(None, alias="Usage")
