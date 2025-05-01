import openai
import traceback
import json
from threading import Event
from provider import ProviderMetaclass  # 假设这个模块存在

import config

API_KEY = config.get_config("grok.api_key", "", caster=lambda x: x.strip(),
                            comment = "用于Grok的API_KEY")
HTTP_PROXY = config.get_config("grok.http_proxy", "", caster=lambda x: x.strip(),
                               comment = "用于Grok的Http代理(可选)")
MODEL = config.get_config("grok.model", "grok-3-mini-beta", caster=lambda x: x.strip(),
                          comment = "Grok模型")
REASONING_EFFORT = config.get_config("grok.reasoning_effort", "low", caster=lambda x: x.strip(),
                                     comment = "可用值: low/high")

config.update_config()

write_fake_data = False

class Provider(metaclass=ProviderMetaclass):
    name = "grok"
    # mode = "function_calling"
    mode = "section_calling"
    
    def __init__(self):
        client = openai.DefaultHttpxClient(proxy=HTTP_PROXY) \
            if HTTP_PROXY else None
        self.client = openai.Client(
            base_url="https://api.x.ai/v1",
            api_key=API_KEY,
            http_client=client,
        )

        if API_KEY == "":
            raise Exception("\n你需要为Grok设置API_KEY\n使用 -c 选项打开配置文件\n")

    def execute(self, options, on_thinking, on_outputing):
        if write_fake_data:
            f = open("fakedata.txt", "w")
        try:
            # 使用自定义会话发送请求
            response = self.client.chat.completions.create(
                model=MODEL,
                reasoning_effort=REASONING_EFFORT,
                messages=options["messages"],
                stream=True,
            )
            
            for chunk in response:
                choice = chunk.choices[0]
                if hasattr(choice.delta, "reasoning_content"):
                    if write_fake_data:
                        f.write("T:" + json.dumps(choice.delta.reasoning_content) + "\n")
                    on_thinking(choice.delta.reasoning_content)
                elif hasattr(choice.delta, "content"):
                    if write_fake_data:
                        f.write("C:" + json.dumps(choice.delta.content) + "\n")
                    if choice.delta.content is not None:
                        on_outputing(choice.delta.content)
                elif choice.finish_reason is not None:
                    if write_fake_data:
                        f.write("F:" + json.dumps(choice.finish_reason) + "\n")
                        f.close()
                    return {"finishReason": choice.finish_reason}
                else:
                    on_thinking("\nUnhandled chunk: " + str(chunk))
            
            # f.close()
            return {"finishReason": "stop"}
            
        except InterruptedError:
            return {"finishReason": "interrupted"}
        except Exception:
            e = traceback.format_exc()
            return {"finishReason": f"Error: {str(e)}"}
        finally:
            self._current_session = None

    def interrupt(self):
        pass
