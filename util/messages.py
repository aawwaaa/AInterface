import uuid
import xmltodict

class Messages:
    def __init__(self):
        self.messages = []

    def add_message(self, role, message):
        self.messages.append({
            "id": uuid.uuid4().hex,
            "role": role,
            "content": message
        })

    def get_messages(self):
        return self.messages

    def save_session(self):
        obj = {}
        for index in range(len(self.messages)):
            message = self.messages[index]
            obj["message" + str(index)] = {
                "id": message["id"],
                "role": message["role"],
                "content": message["content"]
            }
        return xmltodict.unparse({"messages": obj})

    def load_session(self, session):
        self.messages.clear()
        data = xmltodict.parse(session)["messages"]
        for message in data:
            self.messages.append(data[message])
