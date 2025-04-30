tools = []

def calculate(expression):
    return {
        "result": str(eval(expression))
    }
tools += [{
    "name": "calculate",
    "description": "计算表达式",
    "args": {
        "expression": "string"
    },
    "func": calculate
}]

