SPLIT = "\u00a7"

class Delta:
    def __init__(self, section, subsection, data):
        self.section = section
        self.subsection = subsection
        self.data = data
    def __repr__(self):
        return f"[{self.section}] [{self.subsection}] {self.data}"

class SectionDelta:
    def __init__(self, section, data, subsections):
        self.section = section
        self.data = data
        self.subsections = subsections
    def __repr__(self):
        return f"[{self.section}] {self.data}" + '\n'.join(map(
            lambda x: f"{x[0]}={x[1]}", self.subsections.items()
        ))

class StructureDelta:
    def __init__(self, structure, section):
        self.section = section
        self.data = structure
    def __repr__(self):
        return self.data

class SectionReader:
    def __init__(self, modes = {}):
        # {"name": "through" / "whole" / "blocked"}
        self.modes = modes 
        self.reset()

    def reset(self):
        self.buffer = ""
        self.chars_left = ""
        self.data_buffer = ""
        # "data", "section"
        self.state = "data"
        self.current_section = None
        self.remove_ln_flag = False
        self.section_buffer = ""
        self.subsections = {}
        self.current_subsection = None

    def current(self):
        return self.current_section, self.current_subsection

    def get_mode(self, name=""):
        if name == "":
            name = self.current_section
        if name is None:
            return "through"
        if name in self.modes:
            return self.modes[name]
        return "through"

    def add(self, chars, keep = 5):
        return_value = []
        chars = self.chars_left + chars
        if keep != 0:
            if '\n'+SPLIT in chars:
                chars_out = ""
                while (index := chars.find('\n'+SPLIT)) != -1:
                    chars_out += chars[:index] + SPLIT + "`"
                    chars = chars[index+2:]
                self.chars_left = chars
                chars = chars_out
            else:
                index = max(0, len(chars) - keep)
                self.chars_left = chars[index:]
                chars = chars[:index]
                if index == 0:
                    return return_value
        else:
            self.chars_left = ""
        while len(chars) > 0:
            if self.remove_ln_flag:
                if chars[0] == '\n':
                    chars = chars[1:]
                self.remove_ln_flag = False
            chars = self.consume(chars, return_value)
        return return_value

    def dump(self):
        return_value = []
        if len(self.chars_left) != 0:
            return_value += self.add("", 0)
        if self.get_mode() == "through":
            if self.state == "data":
                return_value.append(Delta(*self.current(), self.buffer))
        if self.get_mode() == "whole":
            if self.current_subsection is None:
                self.section_buffer = self.buffer
            else:
                self.subsections[self.current_subsection] = self.buffer
            return_value.append(SectionDelta(self.current_section,
                                    self.section_buffer, self.subsections))
        return return_value

    def consume(self, chars, return_value):
        index = chars.find(SPLIT)
        if index == -1:
            self.buffer += chars
            if self.state == "data" and self.get_mode() == "through":
                data = self.buffer
                self.buffer = ""
                return_value.append(Delta(*self.current(), data))
            return ""
        self.buffer += chars[:index]
        if self.state == "data":
            if self.get_mode() == "through":
                return_value.append(Delta(*self.current(), self.buffer))
            else:
                self.data_buffer = self.buffer
            self.buffer = ""
            self.state = "section"
            return chars[index+1:]
        if self.state == "section":
            section = self.buffer
            self.buffer = ""
            if self.current_subsection is None:
                self.section_buffer = self.data_buffer
            else:
                self.subsections[self.current_subsection] = self.data_buffer
            self.data_buffer = ""
            ln_removed = False
            if section.startswith("`"):
                section = section[1:]
                ln_removed = True
            if (subsection := section.startswith(".")):
                section = section[1:]
            if section.endswith("|"):
                section = section[:-1]
                self.remove_ln_flag = True
            if subsection:
                self.current_subsection = section
            else:
                if self.get_mode() == "whole":
                    return_value.append(SectionDelta(self.current_section,
                                        self.section_buffer, self.subsections))
                self.section_buffer = ""
                self.current_subsection = None
                self.subsections = {}
                self.current_section = section
            if self.get_mode() != "block":
                return_value.append(StructureDelta(("\n" if ln_removed else "") + 
                                    SPLIT + section + SPLIT,
                                    self.current_section))
            self.state = "data"
            return chars[index+1:]

def unparse(section, data, subsections, end = ""):
    if '\n' in data:
        string = SPLIT + section + "|" + SPLIT + "\n"
        string += data + "\n"
    else:
        string = SPLIT + section + SPLIT + data + "\n"
    for subsection in subsections:
        data = str(subsections[subsection])
        if '\n' in data:
            string += SPLIT + '.' + subsection + "|" + SPLIT + "\n" + data + "\n"
        else:
            string += SPLIT + '.' + subsection + SPLIT + data + "\n"
    if end != "":
        string += SPLIT + end + SPLIT + "\n"
    return string

if __name__ == "__main__":
    test_data = """
§sectionA§This is data!
§.subsection§Subsection
§.subsection2§Subsection2
§sectionB§ThisIsData!
Multi Line!
§sectionC§This is data!
§sectionD§This is data!
"""
    reader = SectionReader({
        'sectionC': 'through',
        'sectionD': 'whole'
    })
    for index in range(len(test_data)):
        a = reader.add(test_data[index:index+1])
        if len(a) != 0:
            print(a)
    print(reader.dump())
