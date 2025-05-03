import os
import subprocess

from util.tools import ToolNamespace
import util.section as section

tools = ToolNamespace("fsop")

cwd = os.getcwd()

def get_cwd_str():
    return cwd

def get_cwd():
    return {'result': cwd}
tools += {
    "name": "get_cwd",
    "description": "Get current working directory",
    "args": {},
    "func": get_cwd
}

def set_cwd(relative):
    global cwd
    cwd = os.path.join(cwd, relative)
    return {'result': cwd}
tools += {
    "name": "set_cwd",
    "description": "Set current working directory",
    "args": {
        "relative": "string|The relative path to the new working directory"
    },
    "func": set_cwd
}

def list_files(path = "", all = False, list = True):
    path = os.path.join(cwd, path)
    if all:
        result = subprocess.run(['ls', '-al', path], capture_output=True, text=True)
    else:
        result = subprocess.run(['ls', '-l', path], capture_output=True, text=True)
    
    if not list:
        lines = result.stdout.split('\n')[1:]
        result = '\n'.join([line.split()[-1] for line in lines if line.strip()])
    else:
        result = result.stdout
    
    return {'result': result}
tools += {
    "name": "list_files",
    "description": "List files",
    "args": {
        "all": "bool?",
        "list": "bool?",
        "path": "string:pathA?|Allows relative path from cwd."
    },
    "func": list_files
}

def file_tree(path = "."):
    result = subprocess.run(['tree', "-L", "2", path], 
                          cwd=os.path.join(path, cwd),
                          capture_output=True, 
                          text=True)
    return {'result': result.stdout}
tools += {
    "name": "file_tree",
    "description": "File tree",
    "args": {
        "path": "string:pathA?|Allows relative path from cwd."
    },
    "func": file_tree
}

def read_file(path):
    with open(os.path.join(cwd, path), 'r', encoding='utf-8') as f:
        content = f.read()
    return {'result': content}
tools += {
    "name": "read_file",
    "description": "Read file",
    "args": {
        "path": "string:pathA|Allows relative path from cwd."
    },
    "func": read_file
}

def write_file(path, data):
    with open(os.path.join(cwd, path), 'w', encoding='utf-8') as f:
        f.write(data)
    return {'result': True}
tools += {
    "name": "write_file",
    "description": "Write file",
    "args": {
        "path": "string:pathA|Allows relative path from cwd.",
        "data": "string"
    },
    "func": write_file
}

def replace_file(path, pattern, replace):
    with open(os.path.join(cwd, path), 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(pattern, replace)
    with open(os.path.join(cwd, path), 'w', encoding='utf-8') as f:
        f.write(content)
    return {'result': True}
tools += {
    "name": "replace_file",
    "description": "Replace file. Use this first.",
    "args": {
        "path": "string:pathA|Allows relative path from cwd.",
        "pattern": "string|RAW text, replace all",
        "replace": "string|RAW text"
    },
    "func": replace_file
}

def make_dir(path):
    os.makedirs(os.path.join(cwd, path), exist_ok=True)
    return {'result': True}
tools += {
    "name": "make_dir",
    "description": "Make directory",
    "args": {
        "path": "string:pathA|Allows relative path from cwd."
    },
    "func": make_dir
}

def remove(path):
    os.unlink(os.path.join(cwd, path))
    return {'result': True}
tools += {
    "name": "remove",
    "description": "Remove file",
    "args": {
        "path": "string:pathA|Allows relative path from cwd."
    },
    "func": remove
}

def remove_dir(path):
    import shutil
    shutil.rmtree(os.path.join(cwd, path))
    return {'result': True}
tools += {
    "name": "remove_dir",
    "description": "Remove directory",
    "args": {
        "path": "string:pathA|Allows relative path from cwd."
    },
    "func": remove_dir
}

def copy_file(src, dst):
    import shutil
    shutil.copy2(os.path.join(cwd, src), os.path.join(cwd, dst))
    return {'result': True}
tools += {
    "name": "copy_file",
    "description": "Copy file",
    "args": {
        "src": "string:pathA|Allows relative path from cwd.",
        "dst": "string:pathA|Allows relative path from cwd."
    },
    "func": copy_file
}

def move_file(src, dst):
    os.rename(os.path.join(cwd, src), os.path.join(cwd, dst))
    return {'result': True}
tools += {
    "name": "move_file",
    "description": "Move file",
    "args": {
        "src": "string:pathA|Allows relative path from cwd.",
        "dst": "string:pathA|Allows relative path from cwd."
    },
    "func": move_file
}

def input_data():
    return section.unparse('fsop:status', '', {
        'cwd': get_cwd_str()
    })

__all__ = ["tools", "get_cwd_str", "input_data"]

