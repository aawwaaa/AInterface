from util.tools import ToolNamespace
import os
from os import path
import time
import calendar
import random
import platformdirs
import config as config

tools = ToolNamespace("memory")

LOOKUP_AMOUNT = 10
ENABLE_MEMORY = config.get_config("tool.memory.enable", False, caster=bool, 
                                  comment="启用记忆模块")

memory_dir = path.join(platformdirs.user_data_dir("AInterface"), "memory")
os.makedirs(memory_dir, exist_ok=True)

def get_timestamp():
    return time.strftime("%y%m%d.%H%M%S")
def combine_name(name, keywords):
    name = name[:25]
    keywords = ','.join(map(lambda x: x.strip(), keywords.split(',')))
    keywords = keywords[:75]
    return f"{get_timestamp()}-{name}-{keywords}.m"
def get_time(name):
    # returns the UTC
    return calendar.timegm(time.strptime(name.split('-')[0], '%y%m%d.%H%M%S'))

def get_timestamp_wrapper():
    return {
        'result': get_timestamp
    }
tools += {
    "name": "get_timestamp",
    "description": "Get timestamp in yymmdd.HHMMSS",
    "args": { },
    "func": get_timestamp_wrapper,
}

def create(name, keywords, content):
    name = combine_name(name, keywords).replace("/", "_")
    content = content.split("\n")
    content = "\n".join(content[:5])[:300]
    with open(path.join(memory_dir, name), "w") as f:
        f.write(content)
    return {
        'result': True
    }
tools += {
    "name": "create",
    "description": "Create a memory",
    "args": {
        'name': 'string|The name of the memory, MAX 25 characters with NO space',
        'keywords': 'string|A list in string splited by `,`, MAX 75 characters, AT LEAST 7 keywords with NO space',
        'content': 'string|The content of the memory, MAX 5 lines and 300 characters'
    },
    "func": create,
    "next_turn": False
}

def lookup(pattern):
    found_list = []
    pattern = tuple(map(lambda x: x.strip().replace("/", "_"), pattern.lower().split(',')))
    for name in os.listdir(memory_dir):
        for part in pattern:
            if part in name.lower():
                with open(path.join(memory_dir, name), "r") as f:
                    time = get_time(name)
                    found_list += [(time, name, f.read())]
                    break
    found_list.sort(key=lambda x: x[0])
    random.seed(get_timestamp())
    while len(found_list) > LOOKUP_AMOUNT:
        del found_list[random.randint(0, len(found_list) - 1)]
    found = {}
    for time, name, content in found_list:
        found[name] = content
    if len(found) == 0:
        found['None.m'] = 'No memories found'
    return found
tools += {
    "name": "lookup",
    "description": "Lookup memories",
    "args": {
        'pattern': 'string|The pattern to search for, a list splited by `,` in string, AT LEAST 3 keywords in a word'
    },
    "func": lookup,
}
tools += {
    "name": "lookup_predictive",
    "description": "Lookup memories for predicting actions",
    "args": {
        'pattern': 'string|The pattern to search for, a list splited by `,` in string, AT LEAST 3 keywords in a word'
    },
    "func": lookup,
    "next_turn": False
}

def lookup_recently(timestamp = ''):
    if timestamp == '':
        timestamp = get_timestamp()
    timestamp = get_time(timestamp)
    found_list = [(1000000, 'None.m', 'No memories found')] * LOOKUP_AMOUNT
    for name in os.listdir(memory_dir):
        time = timestamp - get_time(name)
        if time < 0:
            # prefer for history
            time *= -5
        if found_list[-1][0] < time:
            continue
        if time == 0:
            continue
        with open(path.join(memory_dir, name), "r") as f:
            found_list += [(time, name, f.read())]
        found_list.sort(key = lambda x: x[0])
        if len(found_list) > LOOKUP_AMOUNT:
            found_list = found_list[:LOOKUP_AMOUNT]
    found = {}
    for time, name, content in found_list:
        if name == 'None.m' and found_list[0][0] != time:
            continue
        found[name] = content
    return found
tools += {
    "name": "lookup_recently",
    "description": "Lookup memories in recent time",
    "args": {
        'timestamp': 'string?|The timestamp of the memories you want to find nearby, " \
            "in format of yymmdd.HHMMSS, default is now'
    },
    "func": lookup_recently,
}
tools += {
    "name": "lookup_recently_predictive",
    "description": "Lookup memories in recent time for predicting actions",
    "args": {
        'timestamp': 'string?|The timestamp of the memories you want to find nearby, " \
            "in format of yymmdd.HHMMSS, default is now'
    },
    "func": lookup_recently,
    "next_turn": False
}

__all__ = ["tools"]
