import sys
import os
from queue import Queue
import termios
import re
from select import select
import pyfiglet
import websockets.sync.client as client
import websockets
import threading
import fcntl
import tty
import signal
import struct

try:
    import pty
except ImportError:
    try:
        import pywinpty as pty
    except ImportError:
        print("Error: Neither pty and winpty is available.")
        sys.exit(1)

# 全局状态变量
websocket_active = False
process_running = True
master_fd = None
old_term_settings = None

def handle_sigwinch(signum, frame):
    """处理终端大小变化信号"""
    if master_fd:
        cols, rows = os.get_terminal_size()
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)

def handle_sigint(signum, frame):
    """处理Ctrl+C信号"""
    if master_fd:
        os.write(master_fd, b'\x03')  # 发送Ctrl+C到子进程

def setup_signal_handlers():
    """设置信号处理器"""
    signal.signal(signal.SIGWINCH, handle_sigwinch)
    signal.signal(signal.SIGINT, handle_sigint)
    # 忽略其他可能影响程序的信号
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    signal.signal(signal.SIGTTIN, signal.SIG_IGN)

def websocket_read(websocket, write):
    try:
        while process_running:
            message = websocket.recv()
            os.write(write, message.encode())
    except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK):
        pass
    finally:
        global websocket_active
        websocket_active = False

title_escape = re.compile(r"\x1b\][0-9]+;.*?(\x07)")
ansi_escape = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
control_codes = re.compile(r'[\x01-\x1f]')
def convert_to_text(data):
    text = data.decode(errors='ignore')
    text = title_escape.sub('', text)
    text = ansi_escape.sub('', text)
    text1 = ''
    while (match:=control_codes.search(text)):
        code = ord(match.group()[0])
        escaped = f'^{chr(code + 64)}'
        if code == 10:
            escaped = '\n'
        text1 += text[:match.start()] + escaped
        text = text[match.end():]
    text = text1 + text
    return text

def websocket_write(websocket, queue):
    try:
        while process_running:
            message = queue.get()
            websocket.send(message)
    except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK):
        pass
    finally:
        global websocket_active
        websocket_active = False

def start_websocket(target, write, queue):
    try:
        websocket = client.connect(target)
        sys.stdout.write("Connected.\n")
        sys.stdout.write("------------------\n")
        
        websocket_read_thread = threading.Thread(
            target=websocket_read,
            args=(websocket, write),
            daemon=True
        )
        websocket_write_thread = threading.Thread(
            target=websocket_write,
            args=(websocket, queue),
            daemon=True
        )
        
        websocket_read_thread.start()
        websocket_write_thread.start()
        
        global websocket_active
        websocket_active = True
        
        return websocket
        
    except Exception as e:
        sys.stdout.write(f"Connecting failed: {str(e)}\n")
        sys.stdout.write("------------------\n")
        return None

def create_pty():
    """创建PTY并设置初始终端属性"""
    global master_fd
    master_fd, slave_fd = pty.openpty()
    
    # 获取当前终端属性并应用到PTY
    new_attrs = termios.tcgetattr(0)
    termios.tcsetattr(master_fd, termios.TCSANOW, new_attrs)
    
    # 设置初始窗口大小
    handle_sigwinch(None, None)
    
    return master_fd, slave_fd

def create_subprocess(master_fd, slave_fd, cwd, command, args):
    """创建子进程"""
    args = [command] + args
    process_id = os.fork()
    
    if process_id == 0:  # 子进程
        os.setsid()
        
        # 设置控制终端
        if os.name != 'nt':  # 非Windows系统
            try:
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            except (AttributeError, OSError):
                pass  # 某些系统可能不支持

        os.close(master_fd)
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        os.close(slave_fd)
        os.chdir(cwd)
        os.execvp(command, args)
        sys.exit(0)
    
    os.close(slave_fd)
    return process_id

def set_raw():
    """设置终端为原始模式"""
    global old_term_settings
    old_term_settings = termios.tcgetattr(0)
    tty.setraw(0)
    new_settings = termios.tcgetattr(0)
    # 禁用EOF字符（通常是Ctrl+D）
    new_settings[6][termios.VEOF] = 0
    termios.tcsetattr(0, termios.TCSANOW, new_settings)
    return old_term_settings

def get_readable(fd, max_value=1024):
    """获取可读数据量"""
    buf = bytearray(4)
    fcntl.ioctl(fd, termios.FIONREAD, buf)
    return min(int.from_bytes(buf, 'little'), max_value)

def tee(source, target, queue):
    """复制数据流"""
    if (readable := get_readable(source)):
        data = os.read(source, readable)
        os.write(target, data)
        if queue is not None and not queue.full() and websocket_active:
            queue.put(convert_to_text(data))

def loop(process_id, master_fd, queue):
    """主数据转发循环"""
    global process_running
    fds = [0, master_fd]  # stdin 和 PTY master
    
    # 设置非阻塞
    for fd in fds:
        os.set_blocking(fd, False)
    while process_running:
        try:
            rlist, _, _ = select(fds, [], [], 0.5)
            for fd in rlist:
                if fd == 0:
                    tee(0, master_fd, None)
                elif fd == master_fd:
                    tee(master_fd, 1, queue)
        except (InterruptedError, KeyboardInterrupt) as e:
            continue
        except ValueError:  # 文件描述符关闭
            break
        
        if not is_process_running(process_id):
            process_running = False
            break
    os.set_blocking(0, True)

def is_process_running(pid):
    """检查进程是否在运行（包括是否为僵尸进程）"""
    try:
        # 检查进程是否存在
        os.kill(pid, 0)
        
        # 使用waitpid检查进程状态
        # WNOHANG选项表示非阻塞调用
        result = os.waitpid(pid, os.WNOHANG)
        
        # 如果返回的pid不是0，表示进程已经终止（可能是僵尸进程）
        if result[0] != 0:
            return False
            
        return True
    except OSError:
        return False

def cleanup(websocket, master_fd):
    """清理资源"""
    global process_running
    process_running = False
    
    if master_fd:
        os.close(master_fd)
    if websocket:
        websocket.close()
    if old_term_settings:
        termios.tcsetattr(0, termios.TCSANOW, old_term_settings)
    
    sys.stdout.write("\nSession terminated.\n")
    sys.stdout.flush()

def print_info(target, cwd, command, args):
    """打印启动信息"""
    id = target[target.rfind('/'):]
    sys.stdout.write(f"\x1b]0;[AI. Subprocess] <{id}> {command}\a")
    sys.stdout.write(pyfiglet.figlet_format("AI. Subprocess") + "\n")
    sys.stdout.write(f"Command: {command} {' '.join(args)}\n")
    sys.stdout.write(f"CWD: {cwd}\n")
    sys.stdout.write(f"Connecting to {target}\n")
    sys.stdout.flush()

def hint():
    """打印提示信息"""
    sys.stdout.write("Press ENTER to exit...\n")
    sys.stdout.flush()
    input()

def main(connect_target, cwd, command, args):
    """主函数"""
    global master_fd, process_running
    
    # 初始化信号处理
    setup_signal_handlers()
    print_info(connect_target, cwd, command, args)
    
    # 创建PTY和子进程
    master_fd, slave_fd = create_pty()
    output_queue = Queue(maxsize=100)
    
    # 启动WebSocket连接
    websocket = start_websocket(connect_target, master_fd, output_queue)
    process_id = create_subprocess(master_fd, slave_fd, cwd, command, args)
    
    # 设置终端模式
    set_raw()
    
    try:
        loop(process_id, master_fd, output_queue)
    finally:
        cleanup(websocket, master_fd)
        hint()

def run(base=2):
    """入口点"""
    if len(sys.argv) < base+3:
        print("Usage: python script.py <target> <cwd> <command> [args...]")
        sys.exit(1)
        
    connect_target = sys.argv[base+0]
    cwd = sys.argv[base+1]
    command = sys.argv[base+2]
    args = sys.argv[base+3:]
    
    main(connect_target, cwd, command, args)

if __name__ == "__main__":
    run(base=1)
