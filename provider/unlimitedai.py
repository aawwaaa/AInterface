import requests
import json
import uuid
import time
import traceback
import os
import os.path as path
import platformdirs

from provider import ProviderMetaclass
import config

endpoint = config.get_config("provider.unlimitedai.endpoint", "http://localhost:8080", caster=lambda x: x.strip(),
                             comment = "API端点")

config.update_config()

API_URL = endpoint + "/api/chat"
TOKEN_API_URL = endpoint + "/api/token"

cache_file_name = path.join(platformdirs.user_cache_dir("AInterface"), "unlimitedai.token.json")

class Provider(metaclass=ProviderMetaclass):
    name = "unlimitedai"
    mode = "section_calling"

    token = None
    token_expiry = 0

    def update_token(self):
        if self.token is None:
            if path.exists(cache_file_name):
                with open(cache_file_name) as f:
                    data = json.load(f)
                    self.token = data["token"]
                    self.token_expiry = data["token_expiry"]
        if time.time() < self.token_expiry:
            return
        response = requests.get(TOKEN_API_URL)
        text = response.text
        self.token = json.loads(text)["token"]
        self.token_expiry = time.time() + 240
        os.makedirs(path.dirname(cache_file_name), exist_ok=True)
        with open(cache_file_name, "w") as f:
            json.dump({"token": self.token, "token_expiry": self.token_expiry}, f)
    
    def execute(self, options, update, on_thinking, on_outputing):
        self.update_token()
        options = {
            "id": uuid.uuid4().hex,
            "messages": options["messages"],
            "selectedChatModel": "chat-model-reasoning",
        }
        response = requests.post(API_URL, headers={"X-API-Token": self.token}, json=options, stream=True)
        response.encoding = 'utf-8'
        self.last_response = response
        try:
            for chunk in response.iter_lines(decode_unicode=True):
                if chunk[0:2] == "g:":
                    on_thinking(json.loads(chunk[2:]))
                elif chunk[0:2] == "0:":
                    on_outputing(json.loads(chunk[2:]))
                elif chunk[0:2] == "e:":
                    return json.loads(chunk[2:])
            return {"finish_reason": "Error: " + str(response.status_code)}
        except Exception:
            e = traceback.format_exc()
            if self.last_response is None:
                return {"finish_reason": "stop"}
            return {"finish_reason": "Error: " + str(e)}
    def interrupt(self):
        self.last_response.close()
        self.last_response = None
    
