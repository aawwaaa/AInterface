import sys
import curses
import locale
import re
import time
import platformdirs
import threading
import os
import os.path as path
import math
from wcwidth import wcswidth
from typing import List, Dict, Union, Optional, Tuple

import config as config

locale.setlocale(locale.LC_ALL, '')

# Try to use windows-curses if on Windows
try:
    import curses
except ImportError:
    try:
        import windows_curses as curses
    except ImportError:
        print("Error: Neither curses nor windows-curses is available.")
        sys.exit(1)

log_file_name = path.join(platformdirs.user_cache_dir("AInterface"), "log.txt")

# Global variables
stdscr = None
pad = None
pad_bottom = 0
pad_scroll = -1
curs_enabled = True
inserted = False
current_layer = 0
layer_stack = []
progress_bar = None
progress_bar_height = 1
status_bar = None
status_bar_height = 2
last_output_type = None  # 'thinking', 'normal', 'output', None
cursor_pos_stored = (0, 0)
max_y, max_x = 0, 0
content_start_y = 0
save_session_implement = lambda: "none"
announce_text = ""
announce_duration = 0
predicts = []
getch_queue = []

length_bar_value = 0

required_interrupt = False

if config.logging:
    os.makedirs(path.dirname(log_file_name), exist_ok=True)
    log_file = open(log_file_name, "w", encoding="utf-8")

# Color definitions
COLOR_RESET = 0
COLOR_CYAN = 1
COLOR_YELLOW = 2
COLOR_GRAY = 3
COLOR_ORANGE = 4
COLOR_DARKCYAN = 5
COLOR_WHITE = 6
COLOR_SCARLET = 7
COLOR_MAGENTA = 8
COLOR_GREEN = 9

COLOR_STATUS_WHITE = 20

def set_save_session_implement(func):
    global save_session_implement
    save_session_implement = func

def get_shortkey_str() -> str:
    shortkey_str = ""
    # shortkeys
    if last_output_type is not None and current_layer == 1 and layer_stack[0][0] != "输入":
        shortkey_str += "[^T]中断 "

    shortkey_str += "[^R]保存 "
    shortkey_str += "[^C]退出 "

    return shortkey_str

shortkeys = [i for i in range(32)] + [curses.KEY_RESIZE]

def handle_shortkey(key):
    global required_interrupt
    if last_output_type is not None and current_layer == 1 and layer_stack[0][0] != "输入":
        if key == ord('T') - ord('A') + 1:
            required_interrupt = True
            return True
    if key == ord('R') - ord('A') + 1:
        name = save_session_implement()
        announce(f"保存成功：{name}")
        return True
    if key == curses.KEY_RESIZE:
        init_status_bar()
        refresh()
        return True
    return False

def is_required_interrupt() -> bool:
    return required_interrupt
def remove_required_interrupt():
    global required_interrupt
    required_interrupt = False

def scroll_line():
    global pad_scroll
    pad.scroll(1)
    pad.move(max_y - 1, 0)
    if pad_scroll != -1:
        pad_scroll = max(0, pad_scroll - 1)

def log_to_file(output):
    if not config.logging:
        return
    log_file.write(output)

def flush_log_file():
    if not config.logging:
        return
    log_file.flush()

# Initialize colors
def init_colors():
    curses.start_color()
    curses.use_default_colors()
    
    # Define color pairs (foreground, background)
    curses.init_pair(COLOR_CYAN, 51, -1)
    curses.init_pair(COLOR_YELLOW, 226, -1)
    curses.init_pair(COLOR_GRAY, 244, -1)
    curses.init_pair(COLOR_ORANGE, 214, -1)
    curses.init_pair(COLOR_DARKCYAN, 31, -1)
    curses.init_pair(COLOR_WHITE, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_SCARLET, 9, -1)  # Scarlet/red
    curses.init_pair(COLOR_MAGENTA, 164, -1)
    curses.init_pair(COLOR_GREEN, 46, -1)

def is_show_internal() -> bool:
    """Control whether to show thinking and call outputs"""
    return config.show_internal

def init_status_bar():
    global status_bar
    max_y, max_x = stdscr.getmaxyx()
    status_bar = curses.newwin(status_bar_height, max_x, max_y - status_bar_height, 0)
    status_bar.refresh()

def init_progress_bar():
    global progress_bar
    max_y, max_x = stdscr.getmaxyx()
    progress_bar = curses.newwin(progress_bar_height, max_x, 0, 0)
    progress_bar.refresh()

def update_windows():
    update_status_bar()
    update_progress_bar()

def update_status_bar():
    """Update the status bar (no operation for now)"""
    global status_bar
    max_y, max_x = stdscr.getmaxyx()
    y, x = stdscr.getyx()
    status_bar.clear()
    status_bar.addstr(0, 0, ' ' * max_x)
    if announce_duration > time.time():
        status_bar.addstr(1, 0, announce_text, curses.color_pair(COLOR_GREEN))
    else:
        status_bar.addstr(1, 0, 'Len ', curses.A_BOLD)
        dsp_str = str(length_bar_value)
        if length_bar_value > 1000:
            dsp_str = str(int(length_bar_value / 100)/10) + 'k'
        if length_bar_value > 1000000:
            dsp_str = str(int(length_bar_value / 100000)/10) + 'M'
        status_bar.addstr(1, max_x - (len(dsp_str) + 1), dsp_str, curses.A_BOLD)
        length = max_x - 5 - 6
        strs = min(int(length_bar_value / config.max_length_bar * length), length)
        status_bar.addstr(1, 4, '=' * strs, curses.color_pair(COLOR_ORANGE))
        status_bar.addstr(1, 4+strs, '-'*(length - strs), curses.color_pair(COLOR_GRAY))

    shortkey_str = ""

    shortkey_str += get_shortkey_str()

    status_bar.addstr(0, 0, shortkey_str[:max_x], curses.color_pair(COLOR_YELLOW))

    status_bar.refresh()
    stdscr.move(y, x)

def update_progress_bar():
    """Update the progress bar (no operation for now)"""
    global progress_bar
    max_y, max_x = stdscr.getmaxyx()
    pad_max_y = pad.getmaxyx()[0]
    y, x = stdscr.getyx()
    progress_bar.clear()
    filled = math.ceil(pad_bottom / pad_max_y * (max_x-1))
    progress_bar.addstr(0, 0, '-' * (max_x - 1), curses.color_pair(COLOR_GRAY))
    progress_bar.addstr(0, 0, '-' * filled, curses.color_pair(COLOR_CYAN))
    pad_scroll_1 = pad_scroll if pad_scroll != -1 else pad_bottom
    scroll = int(pad_scroll_1 / pad_max_y * (max_x-1))
    progress_bar.addstr(0, scroll, '|', curses.color_pair(COLOR_YELLOW))
    progress_bar.refresh()
    stdscr.move(y, x)

def announce(text):
    global announce_text, announce_duration
    announce_text = text
    announce_duration = time.time() + 3

def set_length_bar_value(value):
    global length_bar_value
    length_bar_value = value

def get_current_position() -> Tuple[int, int]:
    """Get the current cursor position in the pad window"""
    return pad.getyx()

def move_to_position(y: int, x: int):
    """Move cursor to specified position in pad window"""
    global pad_bottom
    try:
        pad.move(y, x)
        pad_bottom = max(y, pad_bottom)
    except curses.error:
        # Handle edge cases where position might be out of bounds
        max_y, max_x = pad.getmaxyx()
        pad.move(min(y, max_y-1), min(x, max_x-1))
        pad_bottom = max(min(y, max_y-1), pad_bottom)

def handle_pad_scroll_delta(delta):
    global pad_scroll
    max_y, max_x = stdscr.getmaxyx()
    max_y -= status_bar_height + progress_bar_height
    if pad_scroll == -1:
        pad_scroll = pad_bottom - max_y + 1
    pad_scroll += delta
    if pad_scroll < 0:
        pad_scroll = 0
    if pad_scroll > pad_bottom - max_y + 1:
        pad_scroll = -1

def handle_pad_scroll_key(key):
    if key == curses.KEY_MOUSE:
        _, x, y, _, bstate = curses.getmouse()
        if bstate & curses.BUTTON4_PRESSED:
            handle_pad_scroll_delta(-5)
            refresh()
            return True
        elif bstate & curses.BUTTON5_PRESSED:
            handle_pad_scroll_delta(5)
            refresh()
            return True
    if key == curses.KEY_PPAGE:
        max_y, max_x = stdscr.getmaxyx()
        max_y -= status_bar_height + progress_bar_height + 5
        handle_pad_scroll_delta(-max_y)
        refresh()
        return True
    if key == curses.KEY_NPAGE:
        max_y, max_x = stdscr.getmaxyx()
        max_y -= status_bar_height + progress_bar_height + 5
        handle_pad_scroll_delta(max_y)
        refresh()
        return True
    return False

def refresh():
    """Refresh the pad window"""
    max_y, max_x = stdscr.getmaxyx()
    max_y -= status_bar_height + progress_bar_height + 1
    if pad_scroll == -1:
        top = max(pad_bottom - max_y, 0)
    else:
        top = min(max(0, pad_scroll), pad_bottom)
    pad.refresh(
        top, 0,
        progress_bar_height, 0,
        progress_bar_height + max_y, max_x - 1
    )
    cursor_y, cursor_x = get_current_position()
    cursor_y -= top
    cursor_y += progress_bar_height
    if 0 <= cursor_y <= max_y and curs_enabled:
        curses.curs_set(1)
        stdscr.move(cursor_y, cursor_x)
    else:
        curses.curs_set(0)
    stdscr.refresh()

def get_max_yx() -> Tuple[int, int]:
    """Get the maximum y and x coordinates of the pad window"""
    max_x = stdscr.getmaxyx()[1]
    y, x = pad.getmaxyx()
    return y, min(x, max_x)

def idle_getch():
    stdscr.nodelay(1)
    key = stdscr.getch()
    if key != -1:
        if handle_pad_scroll_key(key):
            pass
        else:
            handle_shortkey(key)
    stdscr.nodelay(0)

# '''
def output(chars: str, *, color = COLOR_WHITE, prefix = '|  '):
    """Output content at the current layer, supporting line breaks and appending to current position"""
    global current_layer, content_start_y, cursor_pos_stored, pad_bottom
    max_y, max_x = get_max_yx()
    current_y, current_x = get_current_position()
    
    lines = chars.split('\n')
    for i, line in enumerate(lines):
        if i > 0:
            # For new lines after the first one, move to next line
            current_y += 1
            current_x = 0
            while current_y >= max_y - 1:
                # Scroll up if we're at the bottom
                scroll_line()
                cursor_pos_stored = (cursor_pos_stored[0] - 1,
                                             cursor_pos_stored[1])
                current_y = max(0, current_y - 1)
            indent_width = current_layer * 4
            indent = " |  " * (current_layer - 1) + " "
            pad.addstr(current_y, 0, f"{indent}{prefix}")
            log_to_file(f"\n{indent}{prefix}")
            current_x = indent_width
            
        while len(line) > 0:
            while current_y >= max_y - 1:
                # Scroll up if we're at the bottom
                scroll_line()
                cursor_pos_stored = (cursor_pos_stored[0] - 1,
                                             cursor_pos_stored[1])
                current_y = max(0, current_y - 1)
            
            # Calculate available space
            indent_width = current_layer * 4
            available_width = max_x - indent_width - current_x
            if available_width <= 0:
                # Move to next line if no space left
                current_y += 1
                current_x = 0
                available_width = max_x - indent_width
                if available_width <= 0:
                    available_width = max_x - 2

            chunk = ""
            length = 0

            while wcswidth(chunk) <= available_width and length <= len(line):
                chunk = line[0:length]
                length += 1
            line = line[length-1:]
            
            # Add layer indentation if at start of line
            if current_x == 0:
                indent = " |  " * (current_layer - 1) + " "
                pad.addstr(current_y, 0, f"{indent}{prefix}")
                log_to_file(f"\n{indent}{prefix}")
                current_x = indent_width
            
            # Add the content at current position
            pad.addstr(current_y, current_x, chunk, curses.color_pair(color))
            log_to_file(chunk)
            current_x += wcswidth(chunk)
    
    # Move cursor to final position
    move_to_position(current_y, current_x)
    refresh()
    update_windows()
    idle_getch()
# '''

'''
def output(chars: str, *, color = COLOR_WHITE, pad = '|  '):
    """Output content at the current layer, supporting line breaks and appending to current position"""
    stdscr.addstr(chars, curses.color_pair(color))
    stdscr.refresh()
'''

def enter_layer(name: str, color: int, label: str):
    """Enter a new layer"""
    global current_layer, layer_stack, inserted, pad_bottom, max_y, max_x
    max_y, max_x = get_max_yx()
    
    # Save current cursor position
    current_y, current_x = get_current_position()
    
    # Output the layer header
    indent = " |  " * current_layer
    if current_y != 0:
        pad.addstr("\n")
    current_y, current_x = get_current_position()
    if current_y >= max_y - 1:
        scroll_line()
        current_y = max(0, current_y - 1)
        pad_bottom = max(current_y, pad_bottom)
    pad.addstr(current_y, 0, f"{indent}[")
    pad.addstr(name, curses.color_pair(color))
    pad.addstr(f"] {label}\n")
    log_to_file(f"\n{indent}[{name}] {label}\n")
    
    # Update layer tracking
    current_layer += 1
    layer_stack.append((name, color, label))
    
    refresh()
    inserted = True

def exit_layer():
    """Exit the current layer"""
    global current_layer, layer_stack
    
    if current_layer > 0:
        current_layer -= 1
        layer_stack.pop()
    
    refresh()

def get_user_input(embed: bool = True, label = "") -> str:
    """Get multi-line user input with proper formatting, supporting Chinese input"""
    global current_layer

    if not embed:
        while current_layer >= 1:
            exit_layer()
    
    enter_layer("输入", COLOR_CYAN, label)
    
    lines = [""]
    current_line = 0
    current_pos = 0  # Current cursor position within the line
    max_y, max_x = get_max_yx()
    input_start_y, _ = get_current_position()
    indent = " |  " * (current_layer - 1) + " "
    
    # Store wrapped line information for navigation
    wrapped_lines_info = []  # List of tuples (original_line_idx, start_pos, end_pos)
    
    # For IME composition
    composing = False
    compose_str = ""

    def current_pos_dsp():
        return wcswidth(lines[current_line][:current_pos])
    
    def calculate_wrapped_lines():
        nonlocal wrapped_lines_info
        wrapped_lines_info = []
        prefix_len = len(indent) + 3  # "|> " or "|. " or "|  "
        available_width = max_x - prefix_len - 1  # -1 for safety margin
        
        for line_idx, line in enumerate(lines):
            line_start = 0
            line_start_dsp = 0
            while line_start < len(line):
                # Handle multi-byte characters properly
                line_end = line_start
                line_end_dsp = line_start_dsp
                width_used = 0
                while line_end < len(line):
                    char = line[line_end]
                    char_width = max(1, wcswidth(char))
                    if width_used + char_width > available_width:
                        break
                    width_used += char_width
                    line_end += 1
                    line_end_dsp += wcswidth(char)
                
                wrapped_lines_info.append((line_idx, line_start, line_end, line_start_dsp, line_end_dsp))
                line_start = line_end
                line_start_dsp = line_end_dsp
            if len(line) == 0:  # Empty line still needs one wrapped line
                wrapped_lines_info.append((line_idx, 0, 0, 0, 0))
    
    def check_scroll(y):
        nonlocal input_start_y
        global pad_bottom
        if y >= max_y - 1:
            while y >= max_y:
                input_start_y -= 1
                scroll_line()
                y -= 1
        pad_bottom = max(y, pad_bottom)

    def redraw_input():
        nonlocal input_start_y
        check_scroll(input_start_y)
        move_to_position(input_start_y, 0)
        
        # Clear the input area
        for i in range(len(wrapped_lines_info) + 1):
            check_scroll(input_start_y + i)
            move_to_position(input_start_y + i, 0)
            pad.clrtoeol()
        
        # Calculate wrapped lines info
        calculate_wrapped_lines()

        check_scroll(input_start_y + len(wrapped_lines_info))
        
        # Redraw all lines with proper formatting
        for i, (line_idx, start_pos, end_pos, _, _) in enumerate(wrapped_lines_info):
            is_first_segment = (start_pos == 0)
            
            # Build the prefix
            prefix = indent
            if is_first_segment:
                prefix_char = '>' if line_idx == 0 else '.'
                prefix += "|"
                pad.addstr(input_start_y + i, 0, prefix, curses.color_pair(COLOR_WHITE))
                pad.addstr(input_start_y + i, len(prefix), prefix_char + ' ', curses.color_pair(COLOR_CYAN))
            else:
                prefix += "|  "
                pad.addstr(input_start_y + i, 0, prefix, curses.color_pair(COLOR_WHITE))
            
            # Draw the text segment
            text_segment = lines[line_idx][start_pos:end_pos]
            if composing and line_idx == current_line and start_pos <= current_pos <= end_pos:
                # Highlight the composition text
                comp_start = max(start_pos, current_pos - len(compose_str))
                comp_end = min(end_pos, current_pos)
                if comp_start < comp_end:
                    # Draw text before composition
                    pad.addstr(text_segment[:comp_start-start_pos])
                    # Draw composition text with highlight
                    pad.addstr(text_segment[comp_start-start_pos:comp_end-start_pos], 
                                curses.A_REVERSE)
                    # Draw text after composition
                    pad.addstr(text_segment[comp_end-start_pos:])
                else:
                    pad.addstr(text_segment)
            else:
                pad.addstr(text_segment)
        
        # Position the cursor correctly
        cursor_wrapped_line = 0
        cursor_pos_in_wrapped = 0
        remaining_pos = current_pos_dsp()
        
        # Find which wrapped line the cursor is on
        for i, (line_idx, start_pos, end_pos, start_pos_dsp, end_pos_dsp) in enumerate(wrapped_lines_info):
            if line_idx == current_line:
                segment_length = end_pos_dsp - start_pos_dsp
                if remaining_pos <= segment_length:
                    cursor_wrapped_line = i
                    cursor_pos_in_wrapped = remaining_pos
                    break
                remaining_pos -= segment_length
        
        try:
            prefix_len = len(indent) + 3  # "|> " or "|. " or "|  "
            move_to_position(
                input_start_y + cursor_wrapped_line,
                prefix_len + cursor_pos_in_wrapped
            )
        except curses.error:
            move_to_position(max_y - 1, max_x - 1)
        refresh()
        update_windows()
    
    redraw_input()  # Initial draw to show prompt

    def get_current_wrapped_line():
        # Find current position in wrapped lines
        current_wrapped_idx = None
        for i, (line_idx, start_pos, end_pos, _, _) in enumerate(wrapped_lines_info):
            if line_idx == current_line and start_pos <= current_pos < end_pos + (current_pos == end_pos):
                current_wrapped_idx = i
                break
        return current_wrapped_idx, line_idx, start_pos, end_pos
    
    while True:
        update_windows()
        global curs_enabled
        curs_enabled = True
        key = stdscr.getch()
        
        if composing:
            # Handle IME composition
            if key == curses.KEY_ENTER or key == 10 or key == 13:
                # Commit the composition
                lines[current_line] = (
                    lines[current_line][:current_pos - len(compose_str)] + 
                    compose_str + 
                    lines[current_line][current_pos:]
                )
                current_pos = current_pos - len(compose_str) + len(compose_str)
                composing = False
                compose_str = ""
                redraw_input()
                continue
            elif key == curses.KEY_BACKSPACE or key == 127:
                if len(compose_str) > 0:
                    compose_str = compose_str[:-1]
                    current_pos -= 1
                    redraw_input()
                else:
                    composing = False
                    redraw_input()
                continue
            elif 32 <= key <= 126:
                # Add to composition string
                compose_str += chr(key)
                current_pos += 1
                redraw_input()
                continue
        
        if key in shortkeys and handle_shortkey(key):
            pass
        elif handle_pad_scroll_key(key) or key == curses.KEY_MOUSE:
            pass
        elif key == curses.KEY_UP:
            current_wrapped_idx, line_idx, start_pos, end_pos = get_current_wrapped_line()
            if current_wrapped_idx is not None and current_wrapped_idx > 0:
                prev_line_idx, prev_start, prev_end, _, _ = wrapped_lines_info[current_wrapped_idx - 1]
                target_pos = prev_start + (current_pos - start_pos)
                target_pos = min(target_pos, len(lines[prev_line_idx]))
                current_line = prev_line_idx
                current_pos = target_pos
            redraw_input()
        elif key == curses.KEY_DOWN:
            current_wrapped_idx, line_idx, start_pos, end_pos = get_current_wrapped_line()
            if current_wrapped_idx is not None and current_wrapped_idx < len(wrapped_lines_info) - 1:
                next_line_idx, next_start, next_end, _, _ = wrapped_lines_info[current_wrapped_idx + 1]
                target_pos = next_start + (current_pos - start_pos)
                target_pos = min(target_pos, len(lines[next_line_idx]))
                current_line = next_line_idx
                current_pos = target_pos
            redraw_input()
        elif key == curses.KEY_LEFT:
            if current_pos > 0:
                current_pos -= 1
            elif current_line > 0:
                current_line -= 1
                current_pos = len(lines[current_line])
            redraw_input()
        elif key == curses.KEY_RIGHT:
            if current_pos < len(lines[current_line]):
                current_pos += 1
            elif current_line < len(lines) - 1:
                current_line += 1
                current_pos = 0
            redraw_input()
        elif key == curses.KEY_HOME:
            current_wrapped_idx, line_idx, start_pos, end_pos = get_current_wrapped_line()
            current_pos = start_pos
            redraw_input()
        elif key == curses.KEY_END:
            current_wrapped_idx, line_idx, start_pos, end_pos = get_current_wrapped_line()
            current_pos = end_pos
            redraw_input()
        elif key == curses.KEY_BACKSPACE or key == 127:
            if current_pos > 0:
                lines[current_line] = lines[current_line][:current_pos-1] + lines[current_line][current_pos:]
                current_pos -= 1
            elif current_line > 0:
                prev_line_len = len(lines[current_line-1])
                lines[current_line-1] += lines[current_line]
                lines.pop(current_line)
                current_line -= 1
                current_pos = prev_line_len
            redraw_input()
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            if current_line == len(lines) - 1 and len(lines) > 1 and len(lines[-1]) == 0:
                break
            else:
                new_line = lines[current_line][current_pos:]
                lines[current_line] = lines[current_line][:current_pos]
                lines.insert(current_line + 1, new_line)
                current_line += 1
                current_pos = 0
            redraw_input()
        elif key >= 0x80:  # Possible start of multi-byte character
            # Try to handle Chinese input
            try:
                # Get the full character (may need multiple getch() calls)
                char = chr(key)
                bytes = key.to_bytes(1, 'big')
                # Some input methods may send multiple bytes for one character
                # We'll assume the terminal is in UTF-8 mode
                if key >= 0x80:
                    # This might be a multi-byte character
                    bytes_needed = 0
                    if (key & 0xE0) == 0xC0:
                        bytes_needed = 1
                    elif (key & 0xF0) == 0xE0:
                        bytes_needed = 2
                    elif (key & 0xF8) == 0xF0:
                        bytes_needed = 3
                    
                    for _ in range(bytes_needed):
                        next_key = stdscr.getch()
                        if next_key == -1:
                            break
                        bytes += next_key.to_bytes(1, 'big')
                    char = bytes.decode('utf-8')
                
                # Insert the character
                lines[current_line] = (
                    lines[current_line][:current_pos] + 
                    char + 
                    lines[current_line][current_pos:]
                )
                current_pos += len(char)
                redraw_input()
            except Exception as e:
                # Fallback for invalid characters
                pass
        elif 32 <= key <= 126:
            # Printable ASCII character
            char = chr(key)
            lines[current_line] = (
                lines[current_line][:current_pos] + 
                char + 
                lines[current_line][current_pos:]
            )
            current_pos += 1
            redraw_input()
        elif key == 27:
            ch = stdscr.getch()
            if 0 <= ch - 49 < len(predicts):
                predict = predicts[ch - 49]
                lines[current_line] = (
                    lines[current_line][:current_pos] + 
                    predict + 
                    lines[current_line][current_pos:]
                )
                current_pos += len(predict)
                redraw_input()
    
    exit_layer()
    for line in lines:
        log_to_file(line + "\n")
    return '\n'.join(lines)

def request_approve() -> Union[bool, str]:
    """Request user approval with y/N/r options"""
    global current_layer, cursor_pos_stored
    
    # Save cursor position
    cursor_pos_stored = get_current_position()
    
    enter_layer("审批", COLOR_YELLOW, "")
    output("同意? ")
    output("[y/N/r]", color=COLOR_CYAN)

    def clear():
        exit_layer()
        move_to_position(cursor_pos_stored[0]+1, cursor_pos_stored[1])
        stdscr.clrtoeol()
        move_to_position(*cursor_pos_stored)
        stdscr.clrtoeol()
    
    while True:
        key = stdscr.getch()
        if handle_pad_scroll_key(key):
            continue
        if key == ord('y') or key == ord('Y'):
            clear()
            return True
        elif key == ord('n') or key == ord('N') or key == 27 or key == 10:  # 27 is ESC
            clear()
            return False
        elif key == ord('r') or key == ord('R'):
            clear()
            return get_user_input()

def ask_for_information(label, message) -> str:
    enter_layer("操作", COLOR_YELLOW, "输入信息: " + label)
    output(message+"\n")
    exit_layer()
    input = get_user_input()
    return input

def ask_for_user_operate(label, message) -> None:
    enter_layer("操作", COLOR_YELLOW, "需要介入: " + label)
    output(message+"\n")
    output("完成? ")
    output("[任意键]", color=COLOR_CYAN)
    
    while True:
        key = stdscr.getch()
        if handle_pad_scroll_key(key):
            continue
        if handle_shortkey(key):
            continue
        if key == curses.KEY_MOUSE:
            continue
        break
    exit_layer()

def breakable_process(label, func) -> None:
    global current_layer, cursor_pos_stored
    
    # Save cursor position
    cursor_pos_stored = get_current_position()
    
    enter_layer("处理", COLOR_GREEN, label)
    output("打断? ")
    output("[c]         ", color=COLOR_CYAN)

    def clear():
        exit_layer()
        move_to_position(cursor_pos_stored[0]+1, cursor_pos_stored[1])
        stdscr.clrtoeol()
        move_to_position(*cursor_pos_stored)
        stdscr.clrtoeol()
    def check():
        stdscr.nodelay(1)
        key = stdscr.getch()
        if handle_pad_scroll_key(key):
            stdscr.nodelay(0)
            return False
        stdscr.nodelay(0)
        return key == ord('c') or key == ord('C')

    func(check)
    clear()

def output_thinking(chars: str, *, ignore_show_internal = False):
    """Output thinking content with proper formatting"""
    global last_output_type, current_layer, inserted
    
    if not is_show_internal() and not ignore_show_internal:
        if last_output_type != 'thinking':
            if last_output_type is not None:
                exit_layer()
            enter_layer("思考", COLOR_GRAY, "")
            output("思考中...", color=COLOR_GRAY)
            exit_layer()
        last_output_type = 'thinking'
        return
    
    if last_output_type != 'thinking':
        if last_output_type is not None:
            exit_layer()
        enter_layer("思考", COLOR_GRAY, "")
        output(f"{chars}", color=COLOR_GRAY)
        inserted = False
    else:
        if inserted:
            inserted = False
            output("\n")
        output(f"{chars}", color=COLOR_GRAY)
    
    last_output_type = 'thinking'

def output_normal(chars: str):
    """Output normal content with proper formatting"""
    global last_output_type, current_layer, inserted
    
    if not is_show_internal():
        if last_output_type != 'normal':
            if last_output_type is not None:
                exit_layer()
            enter_layer("调用", COLOR_DARKCYAN, "")
            output("思考中...", color=COLOR_DARKCYAN)
            exit_layer()
        last_output_type = 'normal'
        return
    
    if last_output_type != 'normal':
        if last_output_type is not None:
            exit_layer()
        enter_layer("调用", COLOR_DARKCYAN, "")
        output(f"{chars}", color=COLOR_DARKCYAN)
        inserted = False
    else:
        if inserted:
            inserted = False
            output("\n")
        output(f"{chars}", color=COLOR_DARKCYAN)
    
    last_output_type = 'normal'

def output_input(chars: str):
    global last_output_type, current_layer, inserted
    
    if last_output_type != 'input':
        if last_output_type is not None:
            exit_layer()
        enter_layer("输入", COLOR_CYAN, "")
        output(f"{chars}")
        inserted = False
    else:
        if inserted:
            inserted = False
            output("\n")
        output(f"{chars}")
    
    last_output_type = 'input'

def output_output(chars: str):
    """Output content with proper formatting (always shown)"""
    global last_output_type, current_layer, inserted
    
    if last_output_type != 'output':
        if last_output_type is not None:
            exit_layer()
        enter_layer("输出", COLOR_WHITE, "")
        output(f"{chars}")
        inserted = False
    else:
        if inserted:
            inserted = False
            output("\n")
        output(f"{chars}")
    
    last_output_type = 'output'

def output_error(message: str):
    """Output error message with proper formatting"""
    global current_layer
    
    enter_layer("错误", COLOR_SCARLET, "")
    output(message)
    exit_layer()

def tool_using(name: str, args: Dict[str, str]):
    """Display tool usage with arguments"""
    global current_layer
    
    enter_layer("工具", COLOR_MAGENTA, name)
    first_line = True
    for arg_name, arg_value in args.items():
        if not first_line:
            output("\n", prefix="|- ")
        first_line = False
        output(arg_name, color=COLOR_GREEN, prefix="|- ")
        arg_value = str(arg_value)
        if '\n' in arg_value:
            # Multi-line argument
            output(": \n")
            output(arg_value)
        else:
            # Single-line argument
            output(f": {arg_value}")
    
    exit_layer()

def tool_using_result(result: Dict[str, str]):
    """Display tool result"""
    global current_layer
    
    enter_layer("结果", COLOR_ORANGE, "")
    
    first_line = True
    for key, value in result.items():
        if not first_line:
            output("\n", prefix="|- ")
        first_line = False
        output(key, color=COLOR_ORANGE, prefix="|- ")
        value = str(value)
        if '\n' in value:
            # Multi-line result
            output(": \n")
            output(value)
        else:
            # Single-line result
            output(f": {value}")
    
    exit_layer()

def tool_using_error(error: str):
    """Display tool error"""
    output_error(error)

def show_predicts():
    global last_output_type
    if current_layer != 0:
        exit_layer()
        last_output_type = None
    enter_layer("预测", COLOR_CYAN, "")
    index = 1
    for predict in predicts:
        output("[")
        output(f"Alt-{index}", color=COLOR_CYAN)
        output("] ")
        output(predict)
        if predict is not predicts[-1]:
            output("\n")
        index += 1
    exit_layer()

def init_stdscr(stdscr1):
    global stdscr, pad, curs_enabled
    
    stdscr = stdscr1
    
    curs_enabled = True
    stdscr.clear()
    stdscr.scrollok(1)
    stdscr.idlok(1)
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
    init_colors()
    pad = curses.newpad(config.history_length, 200)
    pad.scrollok(1)
    init_status_bar()
    init_progress_bar()
    update_windows()

PREDICT = r"\u00a7predict\|?\u00a7(\n?\u00a7\.[0-9]+\|?\u00a7.+)+(\n?\u00a7predict:end\u00a7)?"

def handle_predict(section, message):
    global predicts
    predicts = []
    for index in section.subsections:
        predicts.append(section.subsections[index])
    show_predicts()
    match = re.search(PREDICT, message)
    if not match:
        return message
    message = message[:match.start()] + message[match.end():]
    return message
