from util.tools import ToolNamespace
from util.interact import ask_for_information
import math

tools = ToolNamespace("base")

def calculate(expression):
    return {
        "result": str(eval(expression, dict(math)))
    }
tools += {
    "name": "calculate",
    "description": "Calculate expression",
    "args": {
        "expression": "string"
    },
    "func": calculate
}

def ask_for_information_wrapper(label, message):
    return {
        'result': ask_for_information(label, message)
    }
tools += {
    "name": "ask_for_information",
    "description": "Ask for information, NOTE you "\
        "can request a few of information in once calling.\n" \
        "Use this only the information IS REALLY NO WAY TO KNOW, not "\
        "something you can get or find by tools.",
    "args": {
        "label": "string|The label of the request",
        "message": "string|The hint message of the request"
    },
    "func": ask_for_information_wrapper
}

__all__ = ["tools"]
