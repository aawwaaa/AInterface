def parse_operation(operation):
    lines = operation.split('\n')
    buffer = []
    first_line = True
    for line in lines:
        if line == "~~~~~~":
            if len(buffer) > 0 or not first_line:
                yield 'data', buffer
            buffer.clear()
            first_line = False
            continue
        if line[0:7] == "~~~~~~ " and line[-7:] == " ======":
            yield 'data', buffer
            buffer.clear()
            yield 'anchor_keyword', line[7:-7]
            first_line = False
            continue
        if line == "======":
            yield 'anchor', buffer
            buffer.clear()
            first_line = False
            continue
        if line == ">>>>>>":
            yield 'replace', buffer
            buffer.clear()
            first_line = False
            continue
        buffer.append(line)
        first_line = False
    if len(buffer) > 0:
        if operation.endswith('\n'):
            buffer = buffer[:-1]
        yield 'data', buffer

def edit_lines(lines, operation):
    lines = iter(lines)
    output_lines = []
    data_buffer = None
    last_anchor = None
    line_number = 0
    for key, value in operation:
        # if isinstance(value, list):
            # print("OP", key)
            # print('\n'.join(value))
        # else:
            # print("OP", key, value)
        if key == 'data':
            if data_buffer is None:
                data_buffer = [line for line in value]
            else:
                data_buffer += value
            continue
        if key != 'replace':
            anchor_begin = 0
        if key == 'anchor':
            match_index = 0
            for line in lines:
                line_number += 1
                line = line[:-1]
                if line == value[match_index]:
                    if match_index == 0:
                        anchor_begin = len(output_lines)
                        # print("MA", "BEGIN")
                    match_index += 1
                else:
                    match_index = 0
                # print("FI", line_number, line)
                output_lines.append(line)
                if match_index == len(value):
                    # print("MA", "END")
                    break
            if match_index != len(value):
                raise Exception('Failed to find anchor: ' + '\n'.join(value))
        if key == 'anchor_keyword':
            if value == 'BEGIN':
                anchor_begin = 0
            elif value == 'END':
                for line in lines:
                    line_number += 1
                    output_lines.append(line[:-1])
                anchor_begin = len(output_lines)
            elif value == 'SPLIT':
                if data_buffer is not None:
                    output_lines += data_buffer
                    # for data in data_buffer:
                        # print("DAI", data)
                data_buffer = None
                last_anchor = None
                continue
            else:
                linenum = int(value)
                for line in lines:
                    line_number += 1
                    output_lines.append(line[:-1])
                    # print("FI", line_number, line[:-1])
                    if line_number == linenum:
                        # print("MA", linenum)
                        anchor_begin = len(output_lines)-1
                        break
                if line_number != linenum:
                    raise Exception('Failed to find line number: ' + str(linenum))
        if key == "replace":
            output_lines = output_lines[:anchor_begin] + value
        if data_buffer is not None:
            if last_anchor is None:
                # for data in data_buffer:
                #     print("DAI", data)
                output_lines = output_lines[:anchor_begin] + data_buffer \
                    + output_lines[anchor_begin:]
            else:
                # for data in data_buffer:
                #     print("DAR", data)
                output_lines = output_lines[:last_anchor] + data_buffer \
                    + output_lines[anchor_begin:]
            # for data in output_lines:
            #     print("O", data)
            anchor_begin += len(data_buffer)
            data_buffer = None
        last_anchor = len(output_lines)
    if data_buffer is not None:
        output_lines += data_buffer
        # for data in data_buffer:
            # print("DAI", data)
    for line in lines:
        line_number += 1
        output_lines.append(line[:-1])
        # print("FI", line_number, line[:-1])
    return map(lambda x: x + '\n', output_lines)

def edit(path, operation):
    operation = parse_operation(operation)
    output_lines = None
    with open(path, "r") as f:
        lines = f.readlines()
        output_lines = edit_lines(lines, operation)
        output_lines = list(output_lines)
    with open(path, "w") as f:
        f.writelines(output_lines)

if __name__ == "__main__":
    with open("../test.operation.session.txt", "r") as f:
        operation = f.read()
        edit("../test.content.session.txt", operation)
