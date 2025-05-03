import os.path as path

class Prompt:
    def __init__(self, name, content):
        self.name = name
        self.content = content

    def apply(self, placeholder, content):
        self.content = self.content.replace('{{' + placeholder + '}}', content)

    def get(self):
        return self.content

def import_prompt(name):
    with open(path.join(path.dirname(__file__), "../prompt", name + ".md")) as f:
        return Prompt(name, f.read())

