import uuid
import xmltodict

class Messages:
    def __init__(self):
        self.messages = []
        self.tool_results = []

    def add_message(self, role, message):
        self.messages.append({
            "id": uuid.uuid4().hex,
            "role": role,
            "content": message
        })

    def add_tool_result(self, results):
        self.tool_results += [results]

    def get_messages(self):
        return self.messages

    def get_tool_result(self, index):
        return self.tool_results[index] \
            if index < len(self.tool_results) else None

    def save_session(self):
        output = []
        split = '=====' + uuid.uuid4().hex + '====='
        output.append(split)
        for index in range(len(self.messages)):
            message = self.messages[index]
            output.append(message["id"])
            output.append(message["role"])
            output.append(message["content"])
            output.append(split)
        string = '\n'.join(output)
        output = ['']
        subsplit = '-----' + uuid.uuid4().hex + '-----'
        output.append("tool_results")
        output.append(subsplit)
        for result in self.tool_results:
            for key in result:
                output.append(key)
                output.append(str(result[key]))
                output.append(subsplit)
            output.append(split)
        string += '\n'.join(output)
        return string

    def load_session(self, iterable):
        self.messages = []
        self.tool_results = []
        iterator = iter(iterable)
        split = None
        id = None
        role = None
        buffer = []
        for line in iterator:
            if line.endswith('\n'):
                line = line[:-1]
            if split is None:
                split = line
                continue
            if id is None:
                id = line
                if id == "tool_results":
                    break
                continue
            if role is None:
                role = line
                continue
            if line == split:
                string = '\n'.join(buffer)
                self.messages.append({
                    "id": id,
                    "role": role,
                    "content": string
                })
                id = None
                role = None
                buffer = []
                continue
            buffer.append(line)
        buffer = []
        result = {}
        subsplit = None
        key = None
        for line in iterator:
            if line.endswith('\n'):
                line = line[:-1]
            if subsplit is None:
                subsplit = line
                continue
            if line == subsplit:
                result[key] = '\n'.join(buffer)
                key = None
                buffer = []
                continue
            if line == split:
                self.tool_results.append(result)
                result = {}
                continue
            if key is None:
                key = line
                continue
            buffer.append(line)
