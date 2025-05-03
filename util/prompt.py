import os.path as path

class Prompt:
    def __init__(self, name, content):
        self.name = name
        self.content = content

    def apply(self, placeholder, content):
        self.content = self.content.replace('{{' + placeholder + '}}', content)

    def get(self):
        return self.content

main_path = ""
def set_main_path(path):
    global main_path
    main_path = path

def import_prompt(name):
    with open(path.join(main_path, "prompt", name + ".md")) as f:
        return Prompt(name, f.read())

