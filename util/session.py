import uuid

class Session:
    def __init__(self):
        self.next_message_id = uuid.uuid4().hex
        self.objects = []
        self.tool_calls = {}
        self.tool_results = {}
        self.messages = []

    def add_message(self, role, message, metadata = {}):
        message = {
            'type': 'message',
            "role": role,
            "content": message,
            **metadata
        }
        self.add_object(message)

    def add_tool_result_binded(self, call_id, result):
        result = {
            'id': self.next_message_id + '|' + call_id,
            'type': 'tool_result',
            **result
        }
        self.add_object(result)

    def add_object(self, obj):
        self.objects += [obj]
        if obj['type'] == 'message':
            if 'id' not in obj:
                obj['id'] = self.next_message_id
                self.next_message_id = uuid.uuid4().hex
            self.messages.append(cast_to_pure_object(obj))
        if obj['type'] == 'tool_call':
            self.tool_calls[obj['id']] = cast_to_pure_object(obj)
        if obj['type'] == 'tool_result':
            self.tool_results[obj['id']] = cast_to_pure_object(obj)

    def get_tool_call(self, call_id):
        return self.tool_calls.get(call_id)

    def get_tool_result(self, call_id):
        return self.tool_results.get(call_id)

    def get_tool_result_binded(self, message_id, call_id):
        return self.tool_results.get(message_id + "|" + call_id)

    def get_messages(self):
        return self.messages

    def get_objects(self):
        return self.objects

    def save_session(self):
        yield from unparse(self.objects)

    def load_session(self, iterable):
        self.objects = []
        self.messages = []
        self.tool_calls = {}
        self.tool_results = {}
        for id, result in parse(iterable):
            result['id'] = id
            self.add_object(result)

def parse(iterator):
    split = None
    subsplit = None
    id = None
    key = None
    result = {}
    buffer = []
    for line in iterator:
        if line.endswith('\n'):
            line = line[:-1]
        if split is None:
            split = line
            continue
        if subsplit is None:
            subsplit = line
            continue
        if line == subsplit:
            result[key] = '\n'.join(buffer)
            key = None
            buffer = []
            continue
        if line == split:
            yield id, result
            id = None
            result = {}
            continue
        if id is None:
            id = line
            continue
        if key is None:
            key = line
            continue
        buffer.append(line)

def unparse(array):
    split = '=====' + uuid.uuid4().hex + '====='
    subsplit = '---' + uuid.uuid4().hex + '---'
    yield split + "\n"
    yield subsplit + "\n"
    for item in array:
        yield str(item['id']) + "\n"
        for key in item:
            if key == 'id':
                continue
            yield key + "\n"
            yield str(item[key]) + "\n"
            yield subsplit + "\n"
        yield split + "\n"

def cast_to_pure_object(obj):
    obj = dict(obj)
    t = obj['type']
    del obj['type']
    keys = []
    for key in obj:
        if key.startswith("metadata."):
            keys += [key]
    for key in keys:
        del obj[key]
    if t == 'message':
        return obj
    if t == 'tool_result':
        del obj['id']
    if t == 'tool_call':
        del obj['id']
    return obj


