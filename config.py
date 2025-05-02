import shutil
import platformdirs
import os
import os.path as path
import toml

config_file_name = path.join(platformdirs.user_config_dir("AInterface"), "config.toml")

os.makedirs(path.dirname(config_file_name), exist_ok=True)
_config = toml.load(config_file_name) if path.exists(config_file_name) else {}
_config_comments = {}
_config_changed = False

def get_config(keys, default_value, caster=lambda x: x, comment=None):
    if isinstance(keys, str):
        keys = keys.split(".")
    global _config_changed
    current = _config
    current_comments = _config_comments
    for key in keys:
        if key not in current:
            if key != keys[-1]:
                current[key] = {}
            else:
                current[key] = default_value
                _config_changed = True
        if key not in current_comments:
            if key != keys[-1]:
                current_comments[key] = {}
            else:
                current_comments[key] = comment
        current = current[key]
        current_comments = current_comments[key]
    value = caster(current)
    return value
def update_config():
    global _config_changed
    if not _config_changed:
        return
    _config_changed = False
    def iterate(di, f, comment_dict = {}):
        for key, value in di.items():
            if isinstance(value, dict):
                f.write(f"\n[{key}]\n")
                iterate(value, f, comment_dict[key] if key in comment_dict else {})
            else:
                if key in comment_dict:
                    f.write(f"# {comment_dict[key]}\n")
                if isinstance(value, str):
                    f.write(f"{key} = \"{value}\"\n")
                elif isinstance(value, bool):
                    f.write(f"{key} = {"true" if value else "false"}\n")
                else:
                    f.write(f"{key} = {value}\n")
    with open(config_file_name, "w") as f:
        iterate(_config, f, _config_comments)
def edit_config():
    if _has_command("editor"):
        os.system(f"editor {config_file_name}")
    else:
        os.system(f"notepad {config_file_name}")

def _has_command(command):
    return shutil.which(command) is not None

provider = get_config("base.provider", "grok", comment="AI提供者")

show_internal = get_config("base.show_internal", True, caster=lambda x: bool(x),
                           comment="显示内部输出，如思考过程和调用过程")

logging = get_config("base.logging", False, caster=lambda x: bool(x),
                     comment="将日志写入文件")

max_length_bar = get_config("base.max_length_bar", 100000, caster=int,
                            comment="长度条的最大值")

# Command to open a console window
# ["kdialog", "--msgbox", "Request"] if True else \
console_window_command = get_config("base.console_window_command",
    ["konsole", "--title", "{title}", "--nofork", "-e"] \
        if _has_command("konsole") else \
    ["gnome-terminal", "-e"] if _has_command("gnome-terminal") else \
    ["xterm", "-e"] if _has_command("xterm") else \
    ["start", "cmd", "/k"] if _has_command("cmd") else "",
    comment="打开新的控制台窗口所用的指令，{title}将被替换为标题")


# Time to wait for stdout
stdout_timeout = get_config("base.stdout_timeout", 6, caster=float,
                            comment="等待来自子进程stdout输出所用的时间")

history_length = get_config("base.history_length", 2000, caster=int,
                            comment="历史记录的长度(行)")

update_config()

