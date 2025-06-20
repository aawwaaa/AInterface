from sys import argv

if len(argv) > 1 and argv[1] == "__connect__":
    import subprocess_client
    subprocess_client.run()
    exit(0)

import curses
import pyfiglet
import time
import argparse
import sys
import threading
import queue
import os.path as path

import tool.base
import tool.fsop
import tool.subprocess
import tool.memory
import tool.edit
from provider import ProviderMetaclass
import util.interact as interact
from util.session import Session
from util.tools import Tools
import util.section as section
import util.prompt as prompt
import config

session = Session()
tools = Tools()
section_reader = section.SectionReader({
    'tool': 'whole',
    'tool:end': 'block',
    'thought': 'through',
    'predict': 'whole',
    'predict:end': 'block',
    'output': 'through'
})
provider = None

tools.import_tools(tool.base.tools)
tools.import_tools(tool.fsop.tools)
tools.import_tools(tool.subprocess.tools)
if tool.memory.ENABLE_MEMORY:
    tools.import_tools(tool.memory.tools)
tools.import_tools(tool.edit.tools)

prompt.set_main_path(path.dirname(__file__))

SYSTEM_PROMPT = prompt.import_prompt("system")
SECTION_PROMPT = prompt.import_prompt("section")
TOOL_PROMPT = prompt.import_prompt("tool")
if tool.memory.ENABLE_MEMORY:
    MEMORY_PROMPT = prompt.import_prompt("memory")

args = {}

def init():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", action="store_true", help="通过编辑器打开配置文件")
    parser.add_argument("exported_file", action="store", nargs="?", help="打开导出的记录")
    args = parser.parse_args()

    if args.config:
        config.edit_config()
        sys.exit(0)

    global provider
    provider_name = config.provider
    import provider.fakedata
    import provider.grok
    import provider.unlimitedai
    import provider.openai_provider
    provider = ProviderMetaclass.providers[provider_name]()

    SYSTEM_PROMPT.apply("provider", provider.name)

    msg = SYSTEM_PROMPT.get()
    msg += SECTION_PROMPT.get()
    if provider.mode == "section_calling":
        TOOL_PROMPT.apply("available_tools", tools.generate_prompt())
        msg += TOOL_PROMPT.get()
    if tool.memory.ENABLE_MEMORY:
        msg += MEMORY_PROMPT.get()
    session.add_message("system", msg)
    # if provider.mode == "section_calling":
    #     tools.add_example_tool()
    #     tools.add_example(messages)
    if provider.mode == "function_calling":
        provider.apply_tools(tools.to_openai_tools(), handle_tool_call)

    if args.exported_file:
        with open(args.exported_file, "r") as f:
            session.load_session(f.readlines())
            session.add_message("system", "This session is loaded from a file, ALL the processes AND fds ARE LOST!")
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
            write_system()
            request_loop()
            continue
        session.add_message("user", command)
        write_system(input_data = True)
        request_loop()

def save_session_implement():
    filename = "session-" + time.strftime("%Y%m%d%H%M%S") + ".session.txt"
    with open(filename, "w") as f:
        for line in session.save_session():
            f.write(line)
    return filename

def write_system(input_data=False):
    global tool_results, message_length_sum
    msg = ""
    if tool_results:
        message_length_sum += len(tool_results)
        msg += tool_results
        tool_results = ""
    stdout = tool.subprocess.pull_stdout()
    if stdout:
        message_length_sum += len(stdout)
        msg += stdout
    if input_data:
        msg += tool.fsop.input_data()
        msg += tool.subprocess.input_data()
    if msg == "":
        return
    session.add_message("system", msg)

message = ""
has_output = False
tool_results = ""
tool_next_turn = False
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
    global tool_next_turn
    next_turn, name, args, result_obj, id, content = tools.handle_openai_tool_calling(call)
    tool_next_turn = tool_next_turn or next_turn
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
    global tool_call_index, tool_next_turn
    for delta in sections:
        if delta.section == "predict":
            if not isinstance(delta, section.StructureDelta):
                message = interact.handle_predict(delta, message)
            continue
        if delta.section == "tool":
            if isinstance(delta, section.StructureDelta):
                continue
            if handle_tools and provider.mode == "section_calling":
                next_turn, result, result_str = tools.handle_tool(delta)
                tool_next_turn = tool_next_turn or next_turn
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
    global message_queue
    while thread.is_alive():
        if interact.is_required_interrupt():
            interact.remove_required_interrupt()
            provider.interrupt()
            message_queue = None
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
    global message_chars, tool_call_index, tool_next_turn, message_queue
    interact.set_length_bar_value(message_length_sum)
    while True:
        if message_queue is None:
            message_queue = queue.Queue()
        section_reader.reset()
        tool_result_objects.clear()
        tool_call_ids.clear()
        tool_calls.clear()
        message = ""
        has_output = False
        tool_next_turn = False
        tool_call_index = 0
        executing_thread = ReturnThread(target=execute_thread, daemon=True)
        executing_thread.start()
        finish = wait_for_execute_done(executing_thread)
        handle_output('', dump_all=True)
        if provider.mode == "function_calling":
            if len(tool_calls) != 0:
                tool_result_objects.append({
                    'type': 'message',
                    'role': 'assistant',
                    'tool_calls': list(map(lambda x: {
                        'id': x.id,
                        'name': "",
                        'type': 'function',
                        'function': {
                            'name': x.function.name,
                            'arguments': x.function.arguments
                        }
                    }, tool_calls))
                })
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
        write_system()
        if not tool_next_turn:
            break


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
    except curses.error:
        pass
