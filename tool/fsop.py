import os
import subprocess

cwd = os.getcwd()

def get_cwd_str():
    return cwd

def get_cwd():
    return {'result': cwd}

def set_cwd(relative):
    global cwd
    cwd = os.path.join(cwd, relative)
    return {'result': cwd}

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

def file_tree(path = "."):
    result = subprocess.run(['tree', "-L", "2", path], 
                          cwd=os.path.join(path, cwd),
                          capture_output=True, 
                          text=True)
    return {'result': result.stdout}

def read_file(path):
    with open(os.path.join(cwd, path), 'r', encoding='utf-8') as f:
        content = f.read()
    return {'result': content}

def write_file(path, data):
    with open(os.path.join(cwd, path), 'w', encoding='utf-8') as f:
        f.write(data)
    return {'result': True}

def replace_file(path, pattern, replace):
    with open(os.path.join(cwd, path), 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(pattern, replace)
    with open(os.path.join(cwd, path), 'w', encoding='utf-8') as f:
        f.write(content)
    return {'result': True}

def make_dir(path):
    os.makedirs(os.path.join(cwd, path), exist_ok=True)
    return {'result': True}

def remove(path):
    os.unlink(os.path.join(cwd, path))
    return {'result': True}

def remove_dir(path):
    import shutil
    shutil.rmtree(os.path.join(cwd, path))
    return {'result': True}

def copy_file(src, dst):
    import shutil
    shutil.copy2(os.path.join(cwd, src), os.path.join(cwd, dst))
    return {'result': True}

def move_file(src, dst):
    os.rename(os.path.join(cwd, src), os.path.join(cwd, dst))
    return {'result': True}

tools = [
    {
        "name": "get_cwd",
        "description": "Get current working directory",
        "args": {},
        "func": get_cwd
    },
    {
        "name": "set_cwd",
        "description": "Set current working directory",
        "args": {
            "relative": "string"
        },
        "func": set_cwd
    },
    {
        "name": "list_files",
        "description": "List files",
        "args": {
            "all": "bool?",
            "list": "bool?",
            "path": "string:pathA?"
        },
        "func": list_files
    },
    {
        "name": "file_tree",
        "description": "File tree",
        "args": {
            "path": "string:pathA?"
        },
        "func": file_tree
    },
    {
        "name": "read_file",
        "description": "Read file",
        "args": {
            "path": "string:pathA"
        },
        "func": read_file
    },
    {
        "name": "write_file",
        "description": "Write file",
        "args": {
            "path": "string:pathA",
            "data": "string"
        },
        "func": write_file
    },
    {
        "name": "replace_file",
        "description": "Replace file",
        "args": {
            "path": "string:pathA",
            "pattern": "string",
            "replace": "string"
        },
        "func": replace_file
    },
    {
        "name": "make_dir",
        "description": "Make directory",
        "args": {
            "path": "string:pathA"
        },
        "func": make_dir
    },
    {
        "name": "remove",
        "description": "Remove file",
        "args": {
            "path": "string:pathA"
        },
        "func": remove
    },
    {
        "name": "remove_dir",
        "description": "Remove directory",
        "args": {
            "path": "string:pathA"
        },
        "func": remove_dir
    },
    {
        "name": "copy_file",
        "description": "Copy file",
        "args": {
            "src": "string:pathA",
            "dst": "string:pathA"
        },
        "func": copy_file
    },
    {
        "name": "move_file",
        "description": "Move file",
        "args": {
            "src": "string:pathA",
            "dst": "string:pathA"
        },
        "func": move_file
    }
]
