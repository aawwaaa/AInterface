import uuid
import xmltodict

class Messages:
    def __init__(self):
        self.messages = []
        self.message_chars = []

    def add_message(self, role, message, message_chars = None):
        self.messages.append({
            "id": uuid.uuid4().hex,
            "role": role,
            "content": message
        })
        if message_chars is None:
            message_chars = [message]
        self.message_chars.append(message_chars)

    def get_messages(self):
        return self.messages

    def save_session(self):
        output = []
        split = '=====' + uuid.uuid4().hex + '====='
        output.append(split)
        for index in range(len(self.messages)):
            message = self.messages[index]
            output.append(message["id"])
            output.append(message["role"])
            output.append('\u200b'.join(self.get_chars(index)))
            output.append(split)
        return '\n'.join(output)

    def load_session(self, iterator):
        self.messages = []
        self.message_chars = []
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
                continue
            if role is None:
                role = line
                continue
            if line == split:
                string = '\n'.join(buffer)
                self.messages.append({
                    "id": id,
                    "role": role,
                    "content": string.replace('\u200b', '')
                })
                self.message_chars.append(string.split('\u200b'))
                id = None
                role = None
                buffer = []
                continue
            buffer.append(line)

    def get_chars(self, index):
        return self.message_chars[index]
