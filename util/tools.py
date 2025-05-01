import traceback

from util.interact import tool_using, tool_using_result, tool_using_error
from util.section import unparse

TOOL_CALLING_PROMPT = """
Call proper tools when needed according to the user's statement with REAL args and PROPER ORDER.
You may use A FEW of TURNS to finish the task, with a SERIAL tool calling.
Note: You can use multi tools in one output complexed with normal output.
NOTICE: REUSE the shell you opened before as much as possible.
When the task is done after the tool called, talk to the user.
When using the tool, follow the STRUCTURE and WITHOUT ANY COMMENT:
To use default value, DO NOT add the key into body.
```
\u00a7tool\u00a7{tool_name}
\u00a7.arg1\u00a7{tool_arg1}
\u00a7.arg2_multiline|\u00a7
{tool_arg2}
...
\u00a7end_tool\u00a7
```
MUST output the tool calling in EVERY TURN when you used it.
Believe every tool calling in OUTPUT area will be responded by the REAL system.
"""
# As parallel as possible, such as use as many tools once as possible.
SPLIT = "\u00a7"
def generate_prompt(tools):
    output = ["All available tools:"]
    for tool in tools.tools:
        args = {}
        for key, t in tools.tools_args[tool].items():
            args[key] = t
            if tools.tools_args_description[tool][key] is not None:
                args[key + ":description"] = tools.tools_args_description[tool][key]
        output.append(unparse("tool", tool, {
            "description": tools.tools_description[tool],
            **args
        }))
    return "\n".join(output)

class Tools:
    def __init__(self):
        self.tools = {}
        self.tools_description = {}
        self.tools_args = {}
        self.tools_args_description = {}

    def register_tool(self, name, description, args, func):
        self.tools[name] = func
        self.tools_description[name] = description
        self.tools_args[name] = {}
        self.tools_args_description[name] = {}
        for key, t in args.items():
            t = t.split("|")
            self.tools_args[name][key] = t[0]
            self.tools_args_description[name][key] = None if len(t) == 1 else t

    def import_tools(self, namespace, tools):
        for tool in tools:
            name = namespace + '.' + tool["name"]
            description = tool["description"]
            args = tool["args"]
            func = tool["func"]
            self.register_tool(name, description, args, func)

    def generate_prompt(self):
        return generate_prompt(self)
    
    def check_args(self, name, args):
        if name not in self.tools_args:
            raise ValueError("Tool not found: " + name)
        errors = []
        for key, t in self.tools_args[name].items():
            if key not in args or args[key] is None:
                if '?' not in t[-3:]:
                    errors += ["Missing argument: " + key]
                continue
            if t[0:len("string:path")] == "string:path":
                if ".." in args[key]:
                    errors += ["Insecure path: " + args[key]]
                    continue
            if t[0:len("bool")] == "bool":
                if args[key] != "true" and args[key] != "false":
                    errors += ["Invalid argument: " + key]
                    continue
        if len(errors) > 0:
            raise Exception('\n'.join(errors))
        return True

    def cast_args(self, name, args):
        for key, t in self.tools_args[name].items():
            if key not in args:
                continue
            if t[0:3] == "int":
                args[key] = int(args[key])
            if t[0:4] == "bool":
                args[key] = args[key] == "true"
            if t[0:6] == "string":
                args[key] = '' if args[key] is None else str(args[key])
        return args

    def append_result(self, name, args, result):
        for key, t in self.tools_args[name].items():
            if 'A' in t[-3:] and key in args:
                result[key] = str(args[key])
        return result
    
    def handle_tool(self, section):
        try:
            name = section.data
            args = section.subsections
            tool_using(name, args)
            self.check_args(name, args)
            args = self.cast_args(name, args)
            result = self.tools[name](**args)
            tool_using_result(result)
            result = self.append_result(name, args, result)
            return result, unparse("tool_result", name, result, end="tool_result_end")
        except Exception:
            msg = traceback.format_exc()
            tool_using_error(msg)
            return {"error": msg}, unparse("tool_error", msg, {}, 
                                           end="tool_error_end")

    def add_example_tool(self):
        def echo(input, optional_input = ""):
            return {
                "input": input,
                "optional_input": optional_input
            }
        self.register_tool("example_tool", "Example tool, which will echo the input", {
            "input": "string",
            "optional_input": "string?",
        }, echo)
    def add_example(self, messages):
        messages.add_message("assistant", unparse("tool", "example_tool", {
            "input": "Hello world!",
            "optional_input": ""
        }, end="tool_end"))
        messages.add_message("system", unparse("tool_result", "example_tool", {
            "input": "Hello world!",
        }, end="tool_result_end"))
        messages.add_tool_result({
            "input": "Hello world!",
        })
        messages.add_message("assistant", unparse("tool", "example_tool", {
            "input": "Hello world,\ntoo.",
            "optional_input": "Hi world!",
        }, end="tool_end"))
        messages.add_message("system", unparse("tool_result", "example_tool", {
            "input": "Hello world,\ntoo.",
            "optional_input": "Hi world!",
        }, end="tool_result_end"))
        messages.add_tool_result({
            "input": "Hello world,\ntoo.",
            "optional_input": "Hi world!",
        })
