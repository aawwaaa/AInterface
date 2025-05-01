import json
import time
import traceback
from provider import ProviderMetaclass
import config

class Provider(metaclass=ProviderMetaclass):
    name = "fakedata"
    mode = "section_calling"

    def execute(self, options, on_thinking, on_outputing):
        try:
            f = open("fakedata.txt", "r", encoding="utf-8")
            for chunk in f:
                time.sleep(0.001)
                if chunk[0:2] == "T:":
                    on_thinking(json.loads(chunk[2:]))
                elif chunk[0:2] == "C:":
                    on_outputing(json.loads(chunk[2:]))
                elif chunk[0:2] == "F:":
                    f.close()
                    return {"finishReason": json.loads(chunk[2:])}
            f.close()
            return {"finishReason": "stop"}
        except Exception:
            e = traceback.format_exc()
            return {"finishReason": "Error: " + str(e)}
    def interrupt(self):
        pass
    
