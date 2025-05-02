from sys import argv

if len(argv) > 1 and argv[1] == "__connect__":
    import subprocess_client
    subprocess_client.run()
    exit(0)

import curses
import pyfiglet
import time
import re
import argparse
import math
import threading
import queue

import tool.base
import tool.fsop
import tool.subprocess
from provider import ProviderMetaclass
import util.interact as interact
from util.session import Session
from util.tools import Tools, TOOL_CALLING_PROMPT
import util.section as section
import config

session = Session()
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

tools.import_tools(tool.base.tools)
tools.import_tools(tool.fsop.tools)
tools.import_tools(tool.subprocess.tools)

args = {}

SYSTEM_PROMPT = """You are an AI assistant.
NO ROLEPLAY and META ANALYSIS. Follow ANY structured output instruction.
MUST output the hint to next turn which can boost the thinking in every output.
The message presented to the user MUST be outputed by section `output`. \
"""

PREDICT_PROMPT = f"""
If the output is without more steps, ppend some predicts about the statement of the user \
according to the context by section `predict` with subsection `.{{index}}` \
WITH ONLY direct command.
For example:
```
{section.unparse('predict', '', {
    '1': 'Find the meeting material created in last week',
    '2': 'Write index.{html,css,js} with some basic template',
    '3': 'Make a new project in current directory powered by nodejs'
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
        os._exit(0)

    global provider
    provider_name = config.provider
    import provider.fakedata
    import provider.grok
    import provider.unlimitedai
    provider = ProviderMetaclass.providers[provider_name]()

    msg = SYSTEM_PROMPT + PREDICT_PROMPT
    # msg += section.SECTION_PROMPT
    if provider.mode == "section_calling":
        msg += TOOL_CALLING_PROMPT + tools.generate_prompt()
    session.add_message("system", msg)
    # if provider.mode == "section_calling":
    #     tools.add_example_tool()
    #     tools.add_example(messages)
    if provider.mode == "function_calling":
        provider.apply_tools(tools.to_openai_tools(), handle_tool_call)

    if args.exported_file:
        with open(args.exported_file, "r") as f:
            session.load_session(f.readlines())
            session.add_message("system", "This session is loaded from a file, ALL the processes ARE LOST!")
            global message_length_sum
            message_length_sum = sum([len(message["content"]) for message in session.get_messages()])
            interact.set_length_bar_value(message_length_sum)
    interact.set_save_session_implement(save_session_implement)

    tool.subprocess.start_websocket()

def main(stdscr):
    global message_length_sum
    interact.init_stdscr(stdscr)
    if args.exported_file:
        for obj in session.get_objects():
            if obj['type'] == 'message':
                global session_message_id, tool_call_index
                session_message_id = obj['id']
                tool_call_index = 0
                if obj["role"] == "assistant":
                    section_reader.reset()
                    handle_output(obj["content"], dump_all=True, handle_tools=False)
                    if 'metadata.tool_call_ids' in obj:
                        show_tool_calls(obj['metadata.tool_call_ids'].split('\n'))
                elif obj["role"] == "user":
                    interact.output_input(obj["content"])
        interact.output_output(f"已从文件 {args.exported_file} 载入会话\n")
    else:
        interact.output_output(pyfiglet.figlet_format("AInterface"))
        interact.output_output("使用`!`输入系统指令,使用`!!`继续输出\n")
    while True:
        command = interact.get_user_input(embed=False, label="<= " + tool.fsop.get_cwd_str())
        message_length_sum += len(command)
        if command[0:1] == "!":
            if command[1:2] != "!":
                session.add_message("system", command[1:])
                continue
            session.add_message("system", "Continue your output...")
            request_loop()
            continue
        session.add_message("user", command)
        request_loop()

def save_session_implement():
    filename = "session-" + time.strftime("%Y%m%d%H%M%S") + ".session.txt"
    with open(filename, "w") as f:
        for line in session.save_session():
            f.write(line)
    return filename

message = ""
has_output = False
tool_results = ""
tool_calls = []
tool_call_ids = []
tool_result_objects = []
tool_call_index = 0
message_length_sum = 0
session_message_id = ""
def handle_tool_call(call):
    global tool_calls
    tool_calls += [call]
def handle_tool_call_post(call):
    name, args, result_obj, id, content = tools.handle_openai_tool_calling(call)
    tool_call_ids.append(id)
    tool_result_objects.append({
        'type': 'message',
        'role': 'tool',
        'content': content,
        'tool_call_id': id
    })
    for key in args:
        args[key] = str(args[key])
    tool_result_objects.append({
        'id': id,
        'type': 'tool_call',
        'function_name': name,
        **args
    })
    tool_result_objects.append({
        'id': id,
        'type': 'tool_result',
        **result_obj
    })
def show_tool_calls(ids):
    for id in ids:
        if len(id) == 0:
            continue
        call = session.get_tool_call(id)
        if call is None:
            interact.tool_using("未知", {
                'notice': '无法从会话中恢复此次工具调用信息',
                'id': id
            })
            continue
        name = call.pop('function_name')
        interact.tool_using(name, call)
        result = session.get_tool_result(id)
        if result is None:
            interact.tool_using_result({
                'notice': '无法从会话中恢复此次工具调用结果',
                'id': id
            })
            continue
        if 'error' in result:
            interact.tool_using_error(result['error'])
        else:
            interact.tool_using_result(result)
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
    global tool_call_index
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
                session.add_tool_result_binded(str(tool_call_index), result)
            else:
                interact.tool_using(delta.data, delta.subsections)
                result = session.get_tool_result_binded(session_message_id,
                                str(tool_call_index))
                if result is None:
                    interact.tool_using_result({
                        "notice": '无法从会话中恢复此次工具调用结果',
                        'id': session_message_id + '|' + str(tool_call_index),
                    })
                elif 'error' in result:
                    interact.tool_using_error(result['error'])
                else:
                    interact.tool_using_result(result)
            tool_call_index += 1
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

message_queue = queue.Queue()
def execute_thread():
    finish = provider.execute({
        "messages": session.get_messages()
    },
        lambda x: message_queue.put(("thinking", x)),
        lambda x: message_queue.put(("output", x)))
    return finish
def wait_for_execute_done(thread):
    while thread.is_alive():
        if interact.is_required_interrupt():
            interact.remove_required_interrupt()
            provider.interrupt()
            thread.terminate()
            return {'finish_reason': 'interrupted'}
        try:
            data = message_queue.get(timeout=0.1)
            if data[0] == "thinking":
                interact.output_thinking(data[1])
            elif data[0] == "output":
                handle_output(data[1])
        except queue.Empty:
            interact.idle_getch()
            continue
    thread.join()
    while True:
        try:
            data = message_queue.get(timeout=0.1)
            if data[0] == "thinking":
                interact.output_thinking(data[1])
            elif data[0] == "output":
                handle_output(data[1])
        except queue.Empty:
            break
    return thread.result
class ReturnThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = None

    def run(self):
        if self._target is not None:
            self.result = self._target(*self._args, **self._kwargs)
def request_loop():
    global message, has_output, response, message_length_sum, tool_results
    global message_chars, tool_call_index
    tool_results += tool.subprocess.pull_stdout()
    if tool_results:
        message_length_sum += len(tool_results)
        session.add_message("system", tool_results)
    tool_results = ""
    interact.set_length_bar_value(message_length_sum)
    while True:
        section_reader.reset()
        tool_result_objects.clear()
        tool_call_ids.clear()
        tool_calls.clear()
        message = ""
        has_output = False
        tool_call_index = 0
        executing_thread = ReturnThread(target=execute_thread, daemon=True)
        executing_thread.start()
        finish = wait_for_execute_done(executing_thread)
        handle_output('', dump_all=True)
        if provider.mode == "function_calling":
            for call in tool_calls:
                handle_tool_call_post(call)
            session.add_message("assistant", message, {
                'metadata.tool_call_ids': '\n'.join(tool_call_ids)
            })
            for obj in tool_result_objects:
                session.add_object(obj)
        else:
            session.add_message("assistant", message)
        if finish["finish_reason"] != "stop":
            interact.output_error("\nTerminated: " + finish["finish_reason"])
            break
        tool_results += tool.subprocess.pull_stdout()
        if not tool_results and len(tool_result_objects) == 0:
            break
        if tool_results:
            message_length_sum += len(tool_results)
            session.add_message("system", tool_results)
            tool_results = ""


if __name__ == "__main__":
    init()
    try:
        curses.wrapper(main)
    except EOFError:
        pass
    except KeyboardInterrupt:
        pass
    try:
        curses.endwin()
    except curses.Error:
        pass
