import os
from util.tools import ToolNamespace
from util.edit import FileDescriptor
from tool.fsop import get_cwd_str

import util.interact as interact

tools = ToolNamespace("edit")

fds = {}
current = None

def open(path):
    global current
    path = os.path.join(get_cwd_str(), path)
    fd = FileDescriptor(path)
    fds[fd.id] = fd
    current = fd
    return {'result': True, **current.status()}
tools += {
    'name': 'open',
    'description': 'Open a file as fd, then select it',
    'args': {
        'path': 'string:path'
    },
    'func': open
}

def select(id):
    global current
    if id not in fds:
        return {
            'result': False,
            'error': 'Fd not found.'
        }
    current = fds[id]
    return {'result': True, **current.status()}
tools += {
    'name': 'select',
    'description': 'Select a fd',
    'args': {
        'id': 'int'
    },
    'func': select
}

def select_wrapper(func):
    def __wrapper(*args, **kwargs):
        if current is None:
            return {'result': False, 'error': 'No fd selected.'}
        return func(current, *args, **kwargs)
    return __wrapper

@select_wrapper
def close(fd):
    del fds[fd.id]
    return {'result': True}
tools += {
    'name': 'close',
    'description': 'Close selected fd.',
    'args': { },
    'func': close
}

@select_wrapper
def status(fd):
    return fd.status()
tools += {
    'name': 'status',
    'description': 'Get the status of selected fd.',
    'args': { },
    'func': status
}
@select_wrapper
def read(fd, text_range):
    return fd.read(text_range)
tools += {
    'name': 'read',
    'description': 'Read the lines near cursor for selected fd.',
    'args': {
        'text_range': 'int=5|The range(lines) of the text section.'
    },
    'func': read
}
@select_wrapper
def find(fd, pattern, regex, text_range):
    return fd.find_get(pattern, regex, text_range)
tools += {
    'name': 'find',
    'description': 'Get the lines near pattern for selected fd.',
    'args': {
        'pattern': 'string|Raw data for string or regex.',
        'regex': 'bool=false|Use the regex to find',
        'text_range': 'int=3|The range(lines) of the text section.'
    },
    'func': find
}
@select_wrapper
def write(fd, data, append_newline):
    if append_newline:
        data += '\n'
    return fd.write(data)
tools += {
    'name': 'write',
    'description': 'Write the lines replacing selected text by cursor for selected fd.',
    'args': {
        'data': 'string',
        'append_newline': 'bool=false'
    },
    'func': write
}

@select_wrapper
def seek(fd, pattern, pattern_append_newline, regex, position, select_second):
    if pattern_append_newline:
        pattern += '\n'
    return fd.seek(pattern, regex, position, select_second)
tools += {
    'name': 'seek',
    'description': 'Move the cursor by pattern for selected fd.',
    'args': {
        'pattern': 'string|Raw data for string or regex.',
        'pattern_append_newline': 'bool=false',
        'regex': 'bool=false|Use the regex to find',
        'position': 'string:enum[before, first, last, after, pattern]=after|The position of cursor. '
            'before: <||>[pattern\\n], first: <|[pattern|>\\n], last: [pattern\\n<|]|>, after: [pattern\\n]\\n<||>after line'
            ', pattern: <|[pattern\\n]|>',
        'select_second': 'bool=false|Only change the section end cursor.'
    },
    'func': seek
}
@select_wrapper
def goto(fd, row, col, select_second):
    return fd.goto(row, col, select_second)
tools += {
    'name': 'goto',
    'description': 'Move the cursor by row and col for selected fd.',
    'args': {
        'row': 'int|The line number.',
        'col': 'int=0',
        'select_second': 'bool=false|Only change the section end cursor.'
    },
    'func': goto
}
