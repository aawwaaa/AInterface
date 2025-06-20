import openai
import traceback
import json
from threading import Event
from provider import ProviderMetaclass

import config

API_KEY = config.get_config("provider.openai.api_key", "", caster=lambda x: x.strip(),
                            comment = "用于OpenAI的API_KEY")
HTTP_PROXY = config.get_config("provider.openai.http_proxy", "", caster=lambda x: x.strip(),
                               comment = "用于OpenAI的Http代理(可选)")
MODEL = config.get_config("provider.openai.model", "gpt-4", caster=lambda x: x.strip(),
                          comment = "OpenAI模型，如 gpt-4, gpt-3.5-turbo, gpt-4-turbo 等")
BASE_URL = config.get_config("provider.openai.base_url", "https://api.openai.com/v1", caster=lambda x: x.strip(),
                             comment = "OpenAI API基础URL，可用于OpenAI兼容的端点")
TOOLS_MODE = config.get_config("provider.openai.tools_mode", "function_calling", caster=lambda x: x.strip(),
                               comment = "可用值: function_calling/section_calling")
TEMPERATURE = config.get_config("provider.openai.temperature", 0.7, caster=float,
                                comment = "生成温度，控制响应的随机性 (0.0-2.0)")
MAX_TOKENS = config.get_config("provider.openai.max_tokens", 4096, caster=int,
                               comment = "最大生成令牌数")

config.update_config()

class OpenaiToolCall:
    def __init__(self, id, name, args):
        self.id = id
        self.function = OpenaiToolCall.OpenaiToolCallFunction(name, args)
    class OpenaiToolCallFunction:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

class Provider(metaclass=ProviderMetaclass):
    name = "openai"
    mode = TOOLS_MODE
    
    def __init__(self):
        client = openai.DefaultHttpxClient(proxy=HTTP_PROXY) \
            if HTTP_PROXY else None
        self.client = openai.Client(
            base_url=BASE_URL,
            api_key=API_KEY,
            http_client=client,
        )

        if API_KEY == "":
            raise Exception("\n你需要为OpenAI设置API_KEY\n使用 -c 选项打开配置文件\n")

        self.tools = []
        self.tool_call_handler = lambda call: None

    def apply_tools(self, tools, tool_call_handler):
        self.tools = tools
        self.tool_call_handler = tool_call_handler

    def execute(self, options, on_thinking, on_outputing):
        try:
            # 准备请求参数
            request_params = {
                "model": MODEL,
                "messages": options["messages"],
                "stream": True,
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
            }
            
            # 如果有工具，添加工具参数
            if self.tools:
                request_params["tools"] = self.tools
                request_params["function_call"] = "auto"

                tool_call_id = ""
                tool_call_name = ""
                tool_call_args = ""

                def run_tool():
                    nonlocal tool_call_id, tool_call_name, tool_call_args
                    self.tool_call_handler(OpenaiToolCall(tool_call_id, tool_call_name, tool_call_args))
                    tool_call_id = ""
                    tool_call_name = ""
                    tool_call_args = ""
                    on_outputing("\n")
            
            # 使用OpenAI客户端发送请求
            response = self.client.chat.completions.create(**request_params)
            
            for chunk in response:
                choice = chunk.choices[0]
                
                # 处理工具调用
                if choice.delta.tool_calls:
                    for call in choice.delta.tool_calls:
                        if call.id is not None:
                            if tool_call_id != "":
                                run_tool()
                            tool_call_id = call.id
                            on_outputing("Tool call: " + call.id + " -> ")
                        if call.function.name is not None:
                            tool_call_name = call.function.name
                            on_outputing(call.function.name + "\n")
                        if call.function.arguments is not None:
                            tool_call_args += call.function.arguments
                            on_outputing(call.function.arguments)
                
                # 处理常规内容
                if hasattr(choice.delta, "content") and choice.delta.content is not None:
                    on_outputing(choice.delta.content)
                
                # 处理完成原因
                elif choice.finish_reason is not None:
                    if tool_call_id != "":
                        run_tool()
                    if choice.finish_reason == "tool_calls":
                        return {"finish_reason": "stop"}
                    return {"finish_reason": choice.finish_reason}
            
            return {"finish_reason": "stop"}
            
        except InterruptedError:
            return {"finish_reason": "interrupted"}
        except Exception as e:
            error_msg = traceback.format_exc()
            return {"finish_reason": f"Error: {error_msg}"}

    def interrupt(self):
        # OpenAI client handles interruption automatically when the iterator is broken
        pass 
