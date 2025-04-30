import re
import xmltodict
import traceback

from util.interact import tool_using, tool_using_result, tool_using_error

TOOL_CALL = r"<tool>[\s\S\n]*?</tool>"

class Tools:
    def __init__(self):
        self.tools = {}
        self.tools_description = {}
        self.tools_args = {}

    def register_tool(self, name, description, args, func):
        self.tools[name] = func
        self.tools_description[name] = description
        self.tools_args[name] = args

    def import_tools(self, namespace, tools):
        for tool in tools:
            name = namespace + '.' + tool["name"]
            description = tool["description"]
            args = tool["args"]
            func = tool["func"]
            self.register_tool(name, description, args, func)
    
    def generate_prompt(self):
        prompt = ""
        for name, description in self.tools_description.items():
            prompt += " - " + name + "\n"
            prompt += "   - " + description + "\n"
            prompt += "   - Args: " + xmltodict.unparse({
                'tool': self.tools_args[name]
            }) + "\n"
        return prompt

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
    
    def handle_tools(self, response):
        results = []
        while True:
            match = re.search(TOOL_CALL, response)
            if not match:
                break
            response = response[0:match.start()] + response[match.end():]
            tool_call = match.group()
            try:
                obj = xmltodict.parse(tool_call)["tool"]
                name = obj["name"]
                del obj["name"]
                args = obj
                tool_using(name, args)
                self.check_args(name, args)
                args = self.cast_args(name, args)
                if '#text' in args:
                    del args['#text']
                result = self.tools[name](**args)
                tool_using_result(name, result)
                result = self.append_result(name, args, result)
                results += [xmltodict.unparse({ 'toolResult': result })]
            except Exception:
                msg = traceback.format_exc()
                tool_using_error("Unknown", msg)
                results += [xmltodict.unparse({ 'toolResult': { "error": msg } })]
        return response, "\n".join(results)
