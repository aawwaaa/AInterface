import asyncio
import websockets
import sys
import threading
import termios
import os
import tty

exists = False
async def handler(websocket):
    global exists
    if exists:
        return
    exists = True
    settings = termios.tcgetattr(0)
    print("Client connected")
    loop = asyncio.get_running_loop()
    
    def stdin_forwarder(loop):
        tty.setraw(0, termios.TCSANOW)
        while True:
            stdin = os.read(0, 1)
            asyncio.run_coroutine_threadsafe(websocket.send(stdin.decode()), loop)
    
    thread = threading.Thread(target=stdin_forwarder, args=(loop,), daemon=True)
    thread.start()
    
    try:
        async for message in websocket:
            message = message.replace('\n', '\r\n')
            sys.stdout.write(message)
            sys.stdout.flush()
            # print in hex, such as in hexdump
            # for char in message:
            #     print(hex(ord(char))[2:].zfill(2), end=' ')
            # print("\r\n", end='')
        termios.tcsetattr(0, termios.TCSANOW, settings)
    except Exception as e:
        termios.tcsetattr(0, termios.TCSANOW, settings)
        print(f"Error: {e}")
    finally:
        print("Client disconnected")
        sys.exit(0)
        exists = False

async def main():
    async with websockets.serve(handler, "localhost", 50001):
        print("Hosted in localhost:50001")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        tty.setcbreak(0)
