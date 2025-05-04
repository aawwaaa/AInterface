import os
import subprocess
import re

from util.tools import ToolNamespace
import util.section as section
from tool.fsop import get_cwd_str
import util.edit

tools = ToolNamespace("edit")

def format_lines(lines, begin, end):
    output = "~~~~~~ " + str(begin+1) + " ======\n"
    for i in range(begin, end):
        output += lines[i]
    output += "~~~~~~ " + str(end) + " ======"
    return output

def find(path, pattern, regex=False, line_range=15):
    with open(path, "r") as f:
        lines = f.readlines()
        found = []
        for index in range(len(lines)):
            if regex:
                if re.search(pattern, lines[index]):
                    found.append(index)
            else:
                if pattern in lines[index]:
                    found.append(index)
        output = []
        line_range = int(line_range/2)
        for index in range(len(found)):
            line = found[index]
            begin = max(0, line - line_range)
            end = min(len(lines), line + line_range)
            found[index] = (begin, end)
            index += 1
        ranges = []
        current = None
        for begin, end in found:
            if current is None:
                current = (begin, end)
                continue
            if begin > current[1]:
                ranges.append(current)
                current = (begin, end)
                continue
            current = (current[0], end)
        if current is not None:
            ranges.append(current)
        for begin, end in ranges:
            output.append(format_lines(lines, begin, end))
        return {
            'result': '\n......\n'.join(output)
        }
    return {
        'error': 'Failed.'
    }
tools += {
    "name": "find",
    "description": "Find contents of a file",
    "args": {
        "path": "string:pathA|The path of the file",
        "pattern": "string|The pattern to search for",
        "regex": "bool?|Whether the pattern is a regular expression, notice the pattern is as RAW regex",
        "line_range": "int?|The range of lines to show, default is 20"
    },
    "func": find
}

def get_lines(path, line, line_range=15):
    with open(path, "r") as f:
        lines = f.readlines()
        line_range = int(line_range/2)
        begin = max(0, line - line_range)
        end = min(len(lines), line + line_range)
        return {
            'result': format_lines(lines, begin, end)
        }
    return {
        'error': 'Failed.'
    }
tools += {
    "name": "get_lines",
    "description": "Get lines of a file",
    "args": {
        "path": "string:pathA|The path of the file",
        "line": "int|The line to get",
        "line_range": "int?|The range of lines to show, default is 20"
    },
    "func": get_lines
}

def edit(path, operation):
    util.edit.edit(path, operation)
    return {'result': True}

tools += {
    "name": "edit",
    "description": "Edit a file",
    "args": {
        "path": "string:pathA|The path of the file",
        "operation": "string|The operation to perform, as followed guidelines."
    },
    "func": edit
}


__all__ = ["tools"]
