import subprocess
import sys
import shutil
from websockets.sync.server import serve
import websockets
import threading
import random
import os
import time

import util.interact as interact
from util.section import unparse
import tool.fsop as fsop
import config as config
from util.tools import ToolNamespace

subprocesses = {}
current = None
host = '127.0.0.1'
port = 0

process_operation = False

if getattr(sys, 'frozen', False):
    connect_command = [sys.executable, '__connect__']
else:
    connect_command = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../main.py'), '__connect__']
connect_command = config.console_window_command + connect_command

def ws_handler(websocket):
    path = websocket.request.path
    try:
        path = int(path[1:])
        if path not in subprocesses:
            websocket.close()
            return
        process = subprocesses[path]
        process.websocket = websocket
        process.post_stdin()
        for message in websocket:
            process.stdout_queue.append(message)
            interact.log_to_file("\n[Subprocess] StdOut: " + str(process.id) + " | " + message + "\n")
    except ValueError:
        websocket.close()
        return
    except websockets.ConnectionClosed:
        websocket.close()
        return
    finally:
        process.remove()

def websocket_thread():
    global port
    websocket_server = None
    while websocket_server is None:
        port = random.randint(50000, 60000)
        try:
            websocket_server = serve(ws_handler, host, port)
        except OSError:
            pass
    interact.log_to_file("\n[Subprocess] Websocket port: " + str(port) + "\n")
    interact.flush_log_file()
    websocket_server.serve_forever()

def start_websocket():
    threading.Thread(target=websocket_thread, daemon=True).start()

class SubProcess:
    id = 1
    def __init__(self, command, cwd):
        global current
        self.id = SubProcess.id
        SubProcess.id += 1
        args = connect_command \
            + ["ws://" + host + ":" + str(port) + "/" + str(self.id), cwd, command]
        for i in range(len(args)):
            if args[i] == "{title}":
                args[i] = "[AI.Subprocess] <" + str(self.id) + "> " + command
        self.process = subprocess.Popen(args)
        interact.log_to_file("\n[Subprocess] Create process: " + str(self.id) + ': ' + ' '.join(args)+"\n")
        interact.flush_log_file()
        subprocesses[self.id] = self
        current = self
        self.websocket = None
        self.command = command
        self.danger_stdin = False
        self.cwd = cwd
        self.stdin_queue = []
        self.stdout_queue = []

        self.removed = False

    def remove(self):
        global current
        if self.removed:
            return
        self.removed = True
        if current == self:
            current = None

    def pull_stdout(self):
        global current
        ret = ''.join(self.stdout_queue)
        self.stdout_queue = []
        if self.removed:
            ret += '\n\nPROCESS REMOVED.\n'
            if current == self:
                current = None
        return ret

    def kill(self):
        global current
        interact.log_to_file("\n[Subprocess] Kill process: " + str(self.id) + "\n")
        if self.websocket:
            self.websocket.send(chr(9))
            self.websocket.close()
        self.process.kill()
        del subprocesses[self.id]
        if current == self:
            current = None
        return True

    def write_stdin(self, data):
        global process_operation
        interact.log_to_file("\n[Subprocess] Write stdin: " + str(self.id) + "\n" + data + "\n")
        process_operation = True
        if self.websocket:
            self.websocket.send(data)
            return True
        self.stdin_queue.append(data)
        return True
    
    def write_signal(self, signal):
        global process_operation
        interact.log_to_file("\n[Subprocess] Write signal: " + str(self.id) + "\n" + str(signal) + "\n")
        process_operation = True
        if self.websocket:
            self.websocket.send(chr(signal))
            return True
        self.stdin_queue.append(chr(signal))
        return True

    def post_stdin(self):
        for data in self.stdin_queue:
            self.websocket.send(data)
        self.stdin_queue = []

    def wait_for_connect(self):
        def loop(check):
            while self.websocket is None:
                if check():
                    break
                time.sleep(0.01)

        interact.breakable_process(f"等待子进程连接: <{self.id}> {self.command}", loop)

tools = ToolNamespace("subprocess")

def add_to_platform_if_has(name, danger_stdin = False, args = ''):
    global tools
    if args != '':
        args = ' ' + args
    global platform
    if shutil.which(name) is None:
        return
    def start(cwd = '', stdin = None, stdin_append_ln = False):
        global process_operation
        process_operation = True
        if cwd != '':
            if cwd[0] != '/':
                cwd = os.path.join(fsop.get_cwd_str(), cwd)
        if cwd == '':
            cwd = fsop.get_cwd_str()
        approved = interact.request_approve()
        if approved is False:
            return {
                'result': False,
                'reason': 'Canceled by user'
            }
        if approved is not True:
            return {
                'result': False,
                'reason': 'Canceled by user with reason',
                'user_followed_reason': approved
            }
        process = SubProcess(name + args, cwd)
        process.danger_stdin = danger_stdin
        process.wait_for_connect()
        if stdin is not None:
            if stdin_append_ln:
                stdin += '\n'
            process.write_stdin(stdin)
        return {'result': True, 'process_id': process.id}
    tools += {
        "name": 'start_'+name,
        "description": 'Start ' + name + ' in interactive mode and select it.',
        "args": {
            "cwd": "string:path?",
            "stdin": "string?|This param is RAW, it means all the thing will be passed to stdin directly.",
            "stdin_append_ln": "bool?|If the `stdin` is whole line, " \
                "set this to `true`, or it will just type chars in as a partial line."
        },
        "func": start
    }

def pull_stdout():
    global process_operation
    duration = 0
    ret = {}
    if process_operation:
        process_operation = False
        duration = time.time() + config.stdout_timeout
    def loop(check):
        nonlocal ret, duration
        while True:
            if check():
                return
            time.sleep(0.05)
            removes = []
            for process in subprocesses.values():
                stdout = process.pull_stdout()
                if stdout:
                    if process.id not in ret:
                        ret[process.id] = stdout
                    else:
                        ret[process.id] += stdout
                    duration = time.time() + config.stdout_timeout
                if process.removed:
                    removes.append(process)
            for process in removes:
                del subprocesses[process.id]
            if time.time() > duration:
                return
            time.sleep(0.45)
    interact.breakable_process("拉取stdout中...", loop)
    ret2 = ""
    for process_id in ret:
        ret2 += unparse("stdout", "[" + str(process_id) + "] " \
            + subprocesses[process_id].command, {
                'data': ret[process_id]
            }, end="stdout_end")
    return ret2

if sys.platform == "win32":
    add_to_platform_if_has("cmd", True)
    add_to_platform_if_has("pwsh", True)
elif sys.platform == "linux":
    add_to_platform_if_has("bash", True)

add_to_platform_if_has("python3", True)

def get_processes():
    ret = []
    for process in subprocesses.values():
        ret.append({
            'process_id': process.id,
            'command': process.command,
            'cwd': process.cwd,
            'removed': process.removed
        })
    return ret
tools += {
    'name': 'get_processes',
    'description': 'Get list of running processes',
    'args': {},
    'func': get_processes
}

def check_selected(func):
    def wrapper(*args, **kwargs):
        if current is None:
            return {
                'result': False,
                'output': 'No process selected'
            }
        return func(*args, **kwargs)
    return wrapper

@check_selected
def kill_process():
    return {
        'result': current.kill()
    }
tools += {
    'name': 'kill_process',
    'description': 'Kill selected process',
    'args': { },
    'func': kill_process
}

@check_selected
def stdin_write(data, append_ln = False):
    if current.danger_stdin:
        approved = interact.request_approve()
        if approved is False:
            return {
                'result': False,
                'reason': 'Canceled by user'
            }
        if approved is not True:
            return {
                'result': False,
                'reason': 'Canceled by user with reason',
                'user_followed_reason': approved
            }
    if append_ln:
        data += '\n'
    return {
        'result': current.write_stdin(data)
    }
tools += {
    'name': 'stdin_write',
    'description': 'Write to stdin to selected process',
    'args': {
        'data': 'string|This param is RAW, it means all the thing will be passed to stdin directly.',
        "append_ln": "bool?|If the `stdin` is whole line, " \
            "set this to `true`, or it will just type chars in as a partial line."
    },
    'func': stdin_write
}

@check_selected
def signal_write(signal):
    return {
        'result': current.write_signal(signal)
    }
tools += {
    'name': 'signal_write',
    'description': 'Write signal to selected process, such as ^C(3), ^Z(26) etc.',
    'args': {
        'signal': 'int'
    },
    'func': signal_write
}

def select_process(process_id):
    global current
    if process_id not in subprocesses:
        return {
            'result': False,
            'error': 'Process not found'
        }
    current = subprocesses[process_id]
    return {
        'result': True,
        'process_id': process_id,
        'command': current.command,
    }
tools += {
    'name': 'select_process',
    'description': 'Select process',
    'args': {
        'process_id': 'int'
    },
    'func': select_process
}

@check_selected
def ask_for_user_operate(message):
    interact.ask_for_user_operate("[" + str(current.id) + "] " + str(current.command), message)
    return {
        'result': True
    }
tools += {
    'name': 'ask_for_user_operate',
    'description': 'Ask for user to operate manually in selected process, such as password typing',
    'args': {
        'message': 'string'
    },
    'func': ask_for_user_operate
}

def wait_for_stdout():
    global process_operation
    process_operation = True
    return {
        'result': True
    }
tools += {
    'name': 'wait_for_stdout',
    'description': 'Wait for stdout of any process.',
    'args': {},
    'func': wait_for_stdout
}

__all__ = ["tools", "start_websocket"]
