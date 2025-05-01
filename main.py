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
from util.interact import get_user_input, output_thinking, \
    output_normal, output_output, output_error, init_stdscr, \
    set_length_bar_value, is_required_interrupt, remove_required_interrupt, \
    set_save_session_implement, handle_predict, output_input
from util.messages import Messages
from util.tools import Tools
import config

messages = Messages()
tools = Tools()
provider = None

tools.import_tools("base", tool.base.tools)
tools.import_tools("fsop", tool.fsop.tools)
tools.import_tools("subprocess", tool.subprocess.tools)

args = {}

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

    messages.add_message("system", f"""
You are an AI assistant. You can use the following tools: {tools.generate_prompt()}
Output <tool><name>TOOL_NAME</name><arg1>ARG1...</arg1><arg2>ARG2...</arg2>...</tool> \
with XML syntax and escaping when using tool.
Call proper tools when needed according to the user's statement with actual args with PROPER ORDER.
You may use A FEW of TURNS to finish the task.
""" + #As parallel as possible, such as use as many tools once as possible.
"""MUST output the important thinking in every output by <thought><plan>value</plan>...</thought>, including: your plan, analysis \
and important things.
Note: You can use multi tools in one output complexed with normal output.
NOTICE: REUSE the shell you opened before as much as possible.
When the task is done after the tool called, talk to the user.
The message presented to the user MUST be outputed by '<output>...</output>'.
Append some predicts about the statement of the user \
according to the context by <predict><predict1>...</predict1><predict2>...</predict2>...</predict> \
WITH ONLY direct command such as <predict><predict1>列出所有文件</predict1><predict2>讲个笑话</predict2>...</predict>.
Use Chinese to talk with user.""")

    if args.exported_file:
        with open(args.exported_file, "r") as f:
            messages.load_session(f.readlines())
            messages.add_message("system", f"This session is loaded from a file, ALL the processes ARE LOST!")
            global message_length_sum
            message_length_sum = sum([len(message["content"]) for message in messages.get_messages()])
            set_length_bar_value(message_length_sum)
    set_save_session_implement(save_session_implement)

def main(stdscr):
    global message_length_sum
    init_stdscr(stdscr)
    if args.exported_file:
        index = 0
        for message in messages.get_messages():
            if message["role"] == "assistant":
                for chars in messages.get_chars(index):
                    handle_output(chars, handle_tools=False)
                handle_output('', dump_all=True, handle_tools=False)
                reset_response()
            elif message["role"] == "user":
                output_input(message["content"])
            index += 1
        output_output(f"已从文件 {args.exported_file} 载入会话\n")
    else:
        output_output(pyfiglet.figlet_format("AInterface"))
        output_output("使用`!`输入系统指令,使用`!!`继续输出\n")
    while True:
        command = get_user_input(embed=False, label="<= " + tool.fsop.get_cwd_str())
        message_length_sum += len(command)
        if command[0:1] == "!":
            if command[1:2] != "!":
                messages.add_message("system", command[1:])
                continue
            messages.add_message("system", "Continue your output...")
            request_loop()
            continue
        messages.add_message("user", command)
        reset_response()
        request_loop()

def save_session_implement():
    filename = "session-" + time.strftime("%Y%m%d%H%M%S") + ".session.txt"
    with open(filename, "w") as f:
        f.write(messages.save_session())
    return filename

XML_ESCAPE = r"&(amp|lt|gt|quot|apos);"
XML_ESCAPES = {
    'amp': '&',
    'lt': '<',
    'gt': '>',
    'quot': '"',
    'apos': "'"
}

response = ""
response_buffer = ""
message = ""
message_chars = []
outputed = ""
message_cache = []
message_unescaped = ""
has_normal = False
has_output = False
outputing_output = False
outputing_predict = False
outputing_thought = False
tool_results = ""
message_length_sum = 0
def interrupt_wrapper(func):
    def __wrapper(*args, **kwargs):
        if is_required_interrupt():
            remove_required_interrupt()
            provider.interrupt()
        return func(*args, **kwargs)
    return __wrapper
def reset_response():
    global response
    response = ""
@interrupt_wrapper
def handle_output(chars, dump_all = False, handle_tools=True):
    global response, message, has_normal, has_output, tool_results, message_length_sum
    message += chars
    message_chars.append(chars)
    message_length_sum += len(chars)
    set_length_bar_value(message_length_sum)
    global message_cache, outputed, message_unescaped
    message_unescaped += chars.replace("<", "\x01").replace(">", "\x02")
    if '&' not in message_unescaped:
        message_cache.append((message_unescaped, chars))
        message_unescaped = ""
    else:
        while '&' in message_unescaped:
            match = re.search(XML_ESCAPE, message_unescaped)
            if not match:
                break
            escaped = message_unescaped[:match.start()] + XML_ESCAPES[match.group(1)]
            message_unescaped = message_unescaped[match.end():]
            message_cache.append((escaped, message_unescaped[:match.end()]
                                  .replace("\x01", "<").replace("\x02", ">")))

    while len(message_cache) > 5 or dump_all:
        if len(message_cache) == 0:
            break
        part = message_cache.pop(0)
        write_output(part[0], outputed, ''.join(map(lambda x: x[0], message_cache)))
        outputed += part[0]
        outputed = outputed[-30:]
        response += part[1]
        
        if handle_tools:
            response, result = tools.handle_tools(response)
            tool_results += result
def write_output(part, out, next_output):
    global response, has_output, tool_results, message_length_sum
    global outputing_predict, outputing_output, outputing_thought
    def check_and_consume(pattern):
        if pattern in out:
            global outputed
            outputed = outputed[outputed.find(pattern) + len(pattern):]
            return True
        return False
    if check_and_consume('\x01thought\x02'):
        outputing_thought = True
    elif check_and_consume('\x01/thought\x02'):
        outputing_thought = False
    elif not outputing_thought:
        if check_and_consume('\x01output\x02'):
            outputing_output = True
        elif (part+next_output).startswith('\x01predict\x02'):
            outputing_predict = True
        elif check_and_consume('\x01/predict\x02'):
            outputing_predict = False

    part = part.replace("\x01", "<").replace("\x02", ">")

    # if outputing_thought:
    #     output_thinking(part)
    if outputing_output:
        if not has_output:
            has_output = True
            output_normal("\n")
        output_output(part)
    elif not outputing_predict:
        output_normal(part)

    if not outputing_thought and "\x01/output\x02" in next_output:
        index = next_output.find("\x01/output\x02")
        removes = []
        for element in message_cache:
            if index >= 0:
                removes.append(element)
            index -= len(element[0])
        if len(removes) != 0:
            change = removes.pop(-1)
            for element in removes:
                message_cache.remove(element)
            message_cache[0] = (change[0][change[0].find('\x01'):], change[1])
        index = next_output.find("\x01/output\x02")
        output_output(next_output[:index])
        outputing_output = False
    
def request_loop():
    global message, has_normal, has_output, response, message_length_sum, tool_results
    global outputed, outputing_predict, outputing_output, outputing_thought, message_chars
    tool_results += tool.subprocess.pull_stdout()
    if tool_results:
        message_length_sum += len(tool_results)
        messages.add_message("system", tool_results)
    tool_results = ""
    set_length_bar_value(message_length_sum)
    while True:
        message = ""
        message_chars = []
        outputed = ""
        has_normal = False
        has_output = False
        outputing_output = False
        outputing_predict = False
        outputing_thought = False
        finish = provider.execute({
            "messages": messages.get_messages()
        }, interrupt_wrapper(output_thinking), handle_output)
        handle_output('', dump_all=True)
        message = handle_predict(message)
        messages.add_message("assistant", message, message_chars)
        if finish["finishReason"] != "stop":
            output_error("\nTerminated: " + finish["finishReason"])
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
