import re
import os
import traceback

def format_lines(lines, begin, end, cursor = ((-1, 0), (-1, 0)), hidden_middle = False):
    begin = min(max(begin, 0), len(lines) + 1)
    end = min(max(end, 0), len(lines) + 1)
    output = "~~~~~~ " + str(begin+1) + " ======\n"
    first_middle = True
    for i in range(begin, end):
        if i >= len(lines) or i < 0:
            line = "\n"
        else:
            line = lines[i]
        offset = 0
        if i == cursor[0][0]:
            pos = cursor[0][1] + offset
            line = line[:pos] + "<|" + line[pos:]
            offset += 2
        if i == cursor[1][0]:
            pos = cursor[1][1] + offset
            line = line[:pos] + "|>" + line[pos:]
            offset += 2
        if not hidden_middle or i == cursor[0][0] or i == cursor[1][0]:
            output += line
        else:
            if first_middle:
                output += "......\n"
                first_middle = False
    output += "~~~~~~ " + str(end) + " ======"
    return output

def format_lines_list(lines, list, cursor = ((-1, 0), (-1, 0))):
    current = None
    ranges = []
    for begin, end in list:
        if current is None:
            current = (begin, end)
            continue
        if begin > current[1]:
            ranges.append(current)
            current = (begin, end)
            continue
        current = (current[0], end)
    if current is not None:
        ranges.append(current)
    output = ""
    for begin, end in ranges:
        if output == "" and begin != 0:
            output += "......\n"
        output += format_lines(lines, begin, end, cursor) + "\n"
    output = output[:-1]
    if len(ranges) != 0 and ranges[-1][1] != len(lines):
        output += "\n......"
    return output

class FileDescriptor:
    id = 1
    def __init__(self, path):
        self.path = path
        self.id = FileDescriptor.id
        # ((select line, select col), (end line, end col))
        last_line = len(self.read_lines())
        self.cursor = [(last_line, 0), (last_line, 0)]
        FileDescriptor.id += 1

    def read_lines(self):
        with open(self.path, "r") as f:
            return list(f.readlines())
    def write_lines(self, lines):
        with open(self.path, "w") as f:
            f.writelines(line for line in lines)

    def status(self):
        return {
            'path': self.path,
            'cursor': self.show_cursor(),
            'id': self.id
        }

    def show_cursor(self):
        return format_lines(self.read_lines(), self.cursor[0][0],
                            self.cursor[1][0] + 1, cursor=self.cursor, hidden_middle=True)

    def find(self, pattern, regex):
        with open(self.path, "r") as f:
            content = f.read()
        # ((row, col), (end row, end col))
        indexs = []
        current_pos = 0
        def process(start, end):
            nonlocal current_pos, indexs
            row = content[:start].count('\n')
            col = start - content[:start].rfind('\n')
            start_len = col + content[start:].find('\n')
            if start_len == col - 1:
                start_len = len(content[start:])
            end_row = content[:end].count('\n')
            end_col = end - content[:end].rfind('\n')
            end_len = end_col + content[end:].find('\n')
            if end_len == end_col - 1:
                end_len = len(content[end:])
            indexs += [((row, col, start_len), (end_row, end_col, end_len))]
            current_pos = end
        if regex:
            regex = re.compile(pattern)
            while (match := regex.search(content, pos=current_pos)):
                start = match.start()
                end = match.end()
                process(start, end)
        else:
            while (start := content.find(pattern, current_pos)) != -1:
                end = start + len(pattern)
                process(start, end)
        return indexs
    def find_get(self, pattern, regex, text_range):
        indexs = ((row - text_range, end_row + text_range)
            for ((row, col, _), (end_row, end_col, _)) in self.find(pattern, regex))
        return {'data': format_lines_list(self.read_lines(), indexs)}

    def seek(self, pattern, regex, position, select_second):
        indexs = self.find(pattern, regex)
        if len(indexs) == 0:
            return {'result': False, 'reason': 'No match found.'}
        if len(indexs) > 1:
            return {'result': False, 'reason': 'Multi pattern found.',
                    ** self.find_get(pattern, regex, 1)}
        start, end = (0, 0), (0, 0)
        (row, col, start_len), (end_row, end_col, end_len) = indexs[0]
        if position == "before":
            start = end = (row, col-1)
        if position == "first":
            if row != end_row:
                start = (row, col-1)
                end = (row, start_len-1)
            else:
                start = (row, col-1)
                end = (end_row, end_col-1)
        if position == "last":
            if row != end_row:
                start = (end_row, 0)
                end = (end_row, end_col-1)
            else:
                start = (row, col-1)
                end = (end_row, end_col-1)
        if position == "after":
            start = end = (end_row, end_col-1)
            if end_col == end_len:
                start = end = (end_row+1, 0)
        if position == "pattern":
            start, end = (row, col-1), (end_row, end_col-1)
        if select_second:
            self.cursor[1] = end
        else:
            self.cursor[0] = start
            self.cursor[1] = end
        return {'result': True, 'cursor': self.show_cursor()}
    def goto(self, row, col, select_second):
        self.cursor[1] = (row, col)
        if not select_second:
            self.cursor[0] = self.cursor[1]
        return {'result': True, 'cursor': self.show_cursor()}

    def read(self, text_range):
        return {'data': format_lines(self.read_lines(), self.cursor[0][0] - text_range,
                            self.cursor[1][0] + 1 + text_range, self.cursor)}
    def write(self, content):
        lines = self.read_lines()
        enter = False
        exit = False
        before = []
        after = []
        line_number = 0
        print(self.cursor[0])
        for line in lines:
            if exit:
                after.append(line)
            if line_number == self.cursor[0][0]:
                before.append(line[:self.cursor[0][1]])
                enter = True
            if not enter:
                before.append(line)
            if line_number == self.cursor[1][0]:
                after.append(line[self.cursor[1][1]:])
                exit = True
            line_number += 1
        if line_number <= self.cursor[0][0]:
            before += ['\n'] * (self.cursor[0][0] - line_number + 1)
        print(before)
        print(after)
        splited = [line + "\n" for line in content.split("\n")]
        if len(splited) != 0:
            splited[-1] = splited[-1][:-1]
            print(splited)
            if len(before) != 0:
                before[-1] += splited.pop(0)
            else:
                before.append(splited.pop(0))
        before += splited
        print(before)
        self.cursor[0] = self.cursor[1] = (len(before)-1, len(before[-1]))
        print(self.cursor[0])
        if len(after) != 0:
            if len(before) != 0:
                before[-1] += after.pop(0)
            else:
                before.append(after.pop(0))
        before += after
        self.write_lines(before)
        return {'result': True}
    def delete(self):
        self.write('')
        return {'result': True}


def main():
    fd = FileDescriptor("test.session.txt")
    print("File Editor - Interactive Mode")
    print("Available commands:")
    print("  r [range=5] - read around cursor")
    print("  w <text> - write at cursor position")
    print("  s <text> - seek text (non-regex)")
    print("  g <line> [col=0] - goto line (and column)")
    print("  st - show file status and cursor")
    print("  f <text> - find and show matches")
    print("  q - quit")
    
    while True:
        try:
            cmd = input("\n> ")
            if not cmd:
                continue
                
            # Read command
            if cmd.startswith('r'):
                parts = cmd.split()
                text_range = int(parts[1]) if len(parts) > 1 else 5
                result = fd.read(text_range)
                print(result['data'])
                
            # Write command
            elif cmd.startswith('w '):
                content = cmd[2:].replace("\\n", "\n")
                result = fd.write(content)
                if result.get('result'):
                    print("Write successful")
                    print(fd.show_cursor())
                else:
                    print(f"Write failed: {result.get('message', 'Unknown error')}")
            
            # Seek command
            elif cmd.startswith('s '):
                pattern = cmd[2:].strip()
                if not pattern:
                    print("Error: No search pattern provided")
                    continue
                result = fd.seek(pattern, regex=False, position='after', select_second=False)
                if result['result']:
                    print("Cursor moved:")
                    print(result['cursor'])
                else:
                    print(f"Error: {result['reason']}")
                    if 'found' in result:
                        print("Matches found:")
                        print(result['found']['data'])
            
            # Goto command
            elif cmd.startswith('g '):
                parts = cmd[2:].split()
                if not parts:
                    print("Error: No line number provided")
                    continue
                try:
                    line = int(parts[0]) - 1  # Convert to 0-based index
                    col = int(parts[1]) if len(parts) > 1 else 0
                    result = fd.goto(line, col, len(parts) > 2)
                    print("Cursor moved:")
                    print(result['cursor'])
                except ValueError:
                    print("Error: Line and column must be numbers")
            
            # Status command
            elif cmd == 'st':
                status = fd.status()
                print(f"File: {status['path']}")
                print("Current cursor position:")
                print(status['cursor'])
            
            # Find command
            elif cmd.startswith('f '):
                pattern = cmd[2:].strip()
                if not pattern:
                    print("Error: No search pattern provided")
                    continue
                result = fd.find_get(pattern, regex=False)
                print("Found matches:")
                print(result['data'])
            
            # Quit command
            elif cmd == 'q':
                print("Exiting...")
                break
                
            else:
                print("Unknown command. Available commands: r, w, s, g, st, f, q")
                
        except KeyboardInterrupt:
            print("\nUse 'q' to quit")
        except Exception:
            print(f"Error: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
