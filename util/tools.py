import traceback
import json

from util.interact import tool_using, tool_using_result, tool_using_error
from util.section import unparse

SPLIT = "\u00a7"
def generate_prompt(tools):
    output = ["All available tools:"]
    for tool in tools.tools.values():
        args = {}
        for arg in tool.args.values():
            args[arg.name] = arg.type
            if arg.optional:
                args[arg.name+":optional"] = "true"
            if arg.description is not None:
                args[arg.name + ":description"] = arg.description
        output.append(unparse("tool", tool.name, {
            "description": tool.description,
            **args
        }))
    return "\n".join(output)

class ToolNamespace:
    def __init__(self, name):
        self.name = name
        self.tools = []

    def __add__(self, tool):
        if isinstance(tool, dict):
            tool = Tool(tool)
        if isinstance(tool, Tool):
            tool.name = self.name + "." + tool.name
            tool.formatted["function"]["name"] = tool.name
            self.tools.append(tool)
        return self

class ToolArg:
    def __init__(self, options):
        self.name = options["name"]
        self.type = options["type"]
        self.description = options["description"]
        
        self.optional = False
        self.feedback = False
        while self.type[-1] in ("?", "A"):
            flag = self.type[-1]
            self.type = self.type[:-1]
            if flag == "?":
                self.optional = True
            elif flag == "A":
                self.feedback = True

        self.formatted = {
            self.name: {
                "type": self.type,
                "description": self.description
            }
        }
        if "formatted" in options:
            self.formatted |= options["formatted"]

    def check_arg(self, arg):
        if arg is None:
            if not self.optional:
                return "Missing argument"
            # Do nothing
            return None
        if self.type == "string:path":
            if ".." in arg:
                return "Insecure path: " + arg
        if self.type == "bool":
            if arg not in (True, False, "true", "false"):
                return "Invalid bool: " + arg
        return None

    def cast_arg(self, arg):
        if self.type == "bool":
            return bool(arg)
        if self.type == "int":
            return int(arg)
        if self.type == "float":
            return float(arg)
        return arg

class Tool:
    def __init__(self, options):
        self.name = options["name"]
        self.description = options["description"]
        self.args = {}
        self.func = options["func"]
        properties = {}
        required = []
        for key, text in options["args"].items():
            if isinstance(text, str):
                text += "|"
                t, description, *_ = text.split("|")
                arg = ToolArg({
                    "name": key,
                    "type": t,
                    "description": description
                })
            else:
                arg = ToolArg(text)
            self.args[key] = arg
            properties |= arg.formatted
            if not arg.optional:
                required.append(key)

        self.formatted = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False
                }
            }
        }

class Tools:
    def __init__(self):
        self.tools = {}
        self.openai_tools = None

    def register_tool(self, tool):
        self.tools[tool.name] = tool

    def import_tools(self, tools):
        for tool in tools.tools:
            self.register_tool(tool)

    def generate_prompt(self):
        return generate_prompt(self)
    
    def check_args(self, name, args):
        if name not in self.tools:
            raise Exception("Unknown tool: " + name)
        tool = self.tools[name]
        errors = []
        for arg in tool.args.values():
            error = arg.check_arg(args.get(arg.name, None))
            if error is not None:
                errors.append(arg.name + ": " + error)
        if len(errors) > 0:
            raise Exception('\n'.join(errors))
        return True

    def cast_args(self, name, args):
        tool = self.tools[name]
        for arg in tool.args.values():
            if arg.name in args:
                args[arg.name] = arg.cast_arg(args[arg.name])
        return args

    def append_result(self, name, args, result):
        for arg in self.tools[name].args.values():
            if arg.name in args and arg.feedback:
                result[arg.name] = args[arg.name]
        return result
    
    def handle_tool(self, section):
        try:
            name = section.data
            args = section.subsections
            tool_using(name, args)
            self.check_args(name, args)
            args = self.cast_args(name, args)
            result = self.tools[name].func(**args)
            tool_using_result(result)
            result = self.append_result(name, args, result)
            return result, unparse("tool_result", name, result, end="tool_result_end")
        except Exception:
            msg = traceback.format_exc()
            tool_using_error(msg)
            return {"error": msg}, unparse("tool_error", msg, {}, 
                                           end="tool_error_end")

    def handle_openai_tool_calling(self, call):
        name = call.function.name
        args = {'raw_args': call.function.arguments}
        try:
            args = json.loads(call.function.arguments)
            tool_using(name, args)
            self.check_args(name, args)
            args = self.cast_args(name, args)
            result = self.tools[name].func(**args)
            tool_using_result(result)
            result = self.append_result(name, args, result)
            return name, args, result, call.id, json.dumps(result)
        except Exception:
            msg = traceback.format_exc()
            tool_using_error(msg)
            error = {"error": msg}
            return name, args, error, call.id, json.dumps(error)

    def add_example_tool(self):
        add_example_tool(self)

    def add_example(self, messages):
        add_example(self, messages)
    
    def to_openai_tools(self):
        return to_openai_tools(self)

def add_example_tool(self):
    def echo(input, optional_input = ""):
        return {
            "input": input,
            "optional_input": optional_input
        }
    self.register_tool(Tool({
        "name": "example_tool", 
        "description": "Example tool, which will echo the input",
        "args": {
            "input": "string",
            "optional_input": "string?",
        },
        "func": echo
    }))

def add_example(self, messages):
        messages.add_tool_result({
            "input": "Hello world!",
        })
        messages.add_message("assistant", unparse("tool", "example_tool", {
            "input": "Hello world!",
            "optional_input": ""
        }, end="tool_end"))
        messages.add_message("system", unparse("tool_result", "example_tool", {
            "input": "Hello world!",
        }, end="tool_result_end"))
        messages.add_tool_result({
            "input": "Hello world,\ntoo.",
            "optional_input": "Hi world!",
        })
        messages.add_message("assistant", unparse("tool", "example_tool", {
            "input": "Hello world,\ntoo.",
            "optional_input": "Hi world!",
        }, end="tool_end"))
        messages.add_message("system", unparse("tool_result", "example_tool", {
            "input": "Hello world,\ntoo.",
            "optional_input": "Hi world!",
        }, end="tool_result_end"))

def to_openai_tools(self):
    if self.openai_tools is not None:
        return self.openai_tools
    array = []
    for name, tool in self.tools.items():
        array += [tool.formatted]
    self.openai_tools = array
    return array

