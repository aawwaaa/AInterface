from sys import argv

if len(argv) > 1 and argv[1] == "__connect__":
    __import__("subprocess_client")
    exit(0)

import curses
import pyfiglet
import time
import re
import argparse
import math

import tool.base
import tool.fsop
import tool.subprocess
from provider import ProviderMetaclass
import util.interact as interact
from util.messages import Messages
from util.tools import Tools, TOOL_CALLING_PROMPT
import util.section as section
import config

messages = Messages()
tools = Tools()
section_reader = section.SectionReader({
    'tool': 'whole',
    'end_tool': 'block',
    'thought': 'through',
    'predict': 'whole',
    'predict_end': 'block',
    'output': 'through'
})
provider = None

tools.add_example_tool()

tools.import_tools("base", tool.base.tools)
tools.import_tools("fsop", tool.fsop.tools)
tools.import_tools("subprocess", tool.subprocess.tools)

args = {}

SYSTEM_PROMPT = """You are an AI assistant.
NO ROLEPLAY and META ANALYSIS. Follow ANY structured output instruction.
MUST output the important thought in every output by section `thought`, \
including: your plan, analysis and important things.
The message presented to the user MUST be outputed by section `output` \
and in Simpified Chinese.
Append some predicts about the statement of the user.
"""

PREDICT_PROMPT = f"""
according to the context by section `predict` with subsection `.{{index}}` \
WITH ONLY direct command.
For example:
```
{section.unparse('predict', '', {
    '1': '查找上周的会议资料',
    '2': '生成index.{html,css,js}并写入基础内容',
    '3': '创建新的nodejs项目'
})}
```
"""

def init():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", action="store_true", help="通过编辑器打开配置文件")
    parser.add_argument("exported_file", action="store", nargs="?", help="打开导出的记录")
    args = parser.parse_args()

    if args.config:
        config.edit_config()
        exit(0)

    global provider
    provider_name = config.provider
    import provider.fakedata
    import provider.grok
    import provider.unlimitedai
    provider = ProviderMetaclass.providers[provider_name]()

    msg = SYSTEM_PROMPT + PREDICT_PROMPT
    msg += section.SECTION_PROMPT
    if provider.mode == "section_calling":
        msg += TOOL_CALLING_PROMPT + tools.generate_prompt()
    messages.add_message("system", msg)
    tools.add_example(messages)

    if args.exported_file:
        with open(args.exported_file, "r") as f:
            messages.load_session(f.readlines())
            messages.add_message("system", f"This session is loaded from a file, ALL the processes ARE LOST!")
            global message_length_sum
            message_length_sum = sum([len(message["content"]) for message in messages.get_messages()])
            interact.set_length_bar_value(message_length_sum)
    interact.set_save_session_implement(save_session_implement)

def main(stdscr):
    global message_length_sum
    interact.init_stdscr(stdscr)
    if args.exported_file:
        index = 0
        for message in messages.get_messages():
            if message["role"] == "assistant":
                section_reader.reset()
                handle_output(message["content"], dump_all=True, handle_tools=False)
            elif message["role"] == "user":
                interact.output_input(message["content"])
            index += 1
        interact.output_output(f"已从文件 {args.exported_file} 载入会话\n")
    else:
        interact.output_output(pyfiglet.figlet_format("AInterface"))
        interact.output_output("使用`!`输入系统指令,使用`!!`继续输出\n")
    while True:
        command = interact.get_user_input(embed=False, label="<= " + tool.fsop.get_cwd_str())
        message_length_sum += len(command)
        if command[0:1] == "!":
            if command[1:2] != "!":
                messages.add_message("system", command[1:])
                continue
            messages.add_message("system", "Continue your output...")
            request_loop()
            continue
        messages.add_message("user", command)
        request_loop()

def save_session_implement():
    filename = "session-" + time.strftime("%Y%m%d%H%M%S") + ".session.txt"
    with open(filename, "w") as f:
        f.write(messages.save_session())
    return filename

message = ""
has_output = False
tool_results = ""
message_length_sum = 0
tool_result_index = 0
def interrupt_wrapper(func):
    def __wrapper(*args, **kwargs):
        if interact.is_required_interrupt():
            interact.remove_required_interrupt()
            provider.interrupt()
        return func(*args, **kwargs)
    return __wrapper
@interrupt_wrapper
def handle_output(chars, dump_all = False, handle_tools=True):
    global message, message_length_sum
    message += chars
    message_length_sum += len(chars)
    interact.set_length_bar_value(message_length_sum)
    write_output(section_reader.add(chars), handle_tools)
    if dump_all:
        write_output(section_reader.dump(), handle_tools)
def write_output(sections, handle_tools):
    global message, has_output, tool_results, message_length_sum
    for delta in sections:
        if delta.section == "predict":
            if not isinstance(delta, section.StructureDelta):
                message = interact.handle_predict(delta, message)
            continue
        if delta.section == "tool":
            if isinstance(delta, section.StructureDelta):
                continue
            if handle_tools and provider.mode == "section_calling":
                result, result_str = tools.handle_tool(delta)
                tool_results += result_str
                messages.add_tool_result(result)
            else:
                global tool_result_index
                interact.tool_using(delta.data, delta.subsections)
                result = messages.get_tool_result(tool_result_index)
                if result is None:
                    interact.tool_using_result({
                        "notice": '无法从历史记录获取此次工具调用的结果'
                    })
                elif 'error' in result:
                    interact.tool_using_error(result['error'])
                else:
                    interact.tool_using_result(result)
                tool_result_index += 1
            continue
        if isinstance(delta, section.StructureDelta):
            interact.output_normal(delta.data)
            continue
        if delta.section == "output":
            if not has_output:
                has_output = True
                interact.output_normal("\n")
            interact.output_output(delta.data)
        else:
            interact.output_normal(delta.data)
    
def request_loop():
    global message, has_output, response, message_length_sum, tool_results
    global message_chars
    tool_results += tool.subprocess.pull_stdout()
    if tool_results:
        message_length_sum += len(tool_results)
        messages.add_message("system", tool_results)
    tool_results = ""
    interact.set_length_bar_value(message_length_sum)
    while True:
        section_reader.reset()
        message = ""
        has_output = False
        finish = provider.execute({
            "messages": messages.get_messages()
        }, interrupt_wrapper(interact.output_thinking), handle_output)
        handle_output('', dump_all=True)
        messages.add_message("assistant", message)
        if finish["finishReason"] != "stop":
            interact.output_error("\nTerminated: " + finish["finishReason"])
            break
        tool_results += tool.subprocess.pull_stdout()
        if not tool_results:
            break
        message_length_sum += len(tool_results)
        messages.add_message("system", tool_results)
        tool_results = ""


if __name__ == "__main__":
    init()
    try:
        curses.wrapper(main)
    except EOFError:
        pass
    except KeyboardInterrupt:
        pass
