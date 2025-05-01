import sys
from websockets.sync.client import connect
import subprocess
import threading
import os
import pyfiglet
import time
import re
import signal
import termios
import tty
from queue import Queue, Empty

exit_event = threading.Event()

# Try to use winpty if on Windows
try:
    import pty
except ImportError:
    try:
        import pywinpty as pty
    except ImportError:
        print("Error: Neither pty and winpty is available.")
        sys.exit(1)

def remove_ansi_escape_sequences(text):
    """移除字符串中的ANSI转义序列"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def handle_websocket(websocket, process, master_fd):
    # Forward websocket messages to process stdin
    while True:
        try:
            message = websocket.recv()
            os.write(master_fd, message.encode())
        except BrokenPipeError:
            break
        except Exception:
            pass

def forward_output(websocket, process, master_fd):
    while True:
        try:
            stdout = os.read(master_fd, 1024)
            if stdout:
                os.write(1, stdout)
                removed = remove_ansi_escape_sequences(stdout.decode())
                websocket.send(removed)
        except BrokenPipeError:
            break
        except BlockingIOError:
            pass
        
        # Check if process has terminated
        if process.poll() is not None:
            break
        
        time.sleep(0.05)
    websocket.close()
    exit_event.set()


def handle_stdin(process, master_fd):
    # Save original terminal settings
    old_settings = termios.tcgetattr(0)
    
    try:
        # Set terminal to raw mode to get all keypresses
        tty.setraw(0, termios.TCSANOW)
        
        while True:
            if exit_event.is_set():
                break
            try:
                # Read one byte at a time to properly capture control sequences
                stdin = os.read(0, 1)
                if stdin:
                    os.write(master_fd, stdin)
            except BrokenPipeError:
                break
            except BlockingIOError:
                # Small sleep to prevent CPU spinning
                time.sleep(0.01)
            except KeyboardInterrupt:
                process.send_signal(signal.SIGINT)
                continue
    finally:
        # Restore terminal settings
        termios.tcsetattr(0, termios.TCSANOW, old_settings)
    
    input("Press ENTER to exit...")

def main(connect_target, cwd, command):
    sys.stdout.write("\x1b]2;[AI. Subprocess] [" + connect_target + "]" + command + "\a")

    sys.stdout.write(pyfiglet.figlet_format("AI. Subprocess") + "\n")
    sys.stdout.write("Connecting to " + connect_target + "\n")
    sys.stdout.write("Command: " + command + "\n")
    sys.stdout.write("CWD: " + cwd + "\n")
    sys.stdout.flush()

    master_fd, slave_fd = pty.openpty()
    os.set_blocking(master_fd, False)

    # Create the subprocess
    process = subprocess.Popen(
        command,
        shell=True,
        cwd=cwd,
        stdin = slave_fd,
        stdout = slave_fd,
        stderr = slave_fd,
        text=False,
        bufsize=0
    )

    os.close(slave_fd)
    
    with connect(connect_target) as websocket:
        sys.stdout.write("Connected.\n")
        sys.stdout.write("------------------------\n")

        # Start stdout and stderr forwarding threads
        stderr_thread = threading.Thread(target=forward_output, args=(websocket, process, master_fd), daemon=True)
        stderr_thread.start()

        # Start websocket handling thread
        websocket_thread = threading.Thread(target=handle_websocket, args=(websocket, process, master_fd), daemon=True)
        websocket_thread.start()
        
        handle_stdin(process, master_fd)


connect_target = sys.argv[2]
cwd = sys.argv[3]
command = sys.argv[4]

main(connect_target, cwd, command)
