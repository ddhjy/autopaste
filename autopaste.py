#!/usr/bin/env python3
"""
AutoPaste - receives text via HTTP and pastes it into the active input field on macOS.

Usage:
    python3 autopaste.py [--port PORT]

Send text:
    curl -X POST http://localhost:9999 -d 'your text here'
    curl -X POST http://localhost:9999 -H 'Content-Type: application/json' -d '{"text": "your text here"}'
"""

import argparse
import json
import subprocess
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

import Quartz


def simulate_paste():
    # Key code 9 = 'v', command flag
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    cmd_down = Quartz.CGEventCreateKeyboardEvent(src, 9, True)
    cmd_up = Quartz.CGEventCreateKeyboardEvent(src, 9, False)
    Quartz.CGEventSetFlags(cmd_down, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventSetFlags(cmd_up, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_up)


def copy_and_paste(text: str):
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    time.sleep(0.05)
    simulate_paste()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                data = json.loads(body)
                text = data.get("text", "")
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "invalid json"}')
                return
        else:
            text = body.decode("utf-8")

        if not text:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "empty text"}')
            return

        try:
            copy_and_paste(text)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
            print(f"Pasted: {text[:80]}{'...' if len(text) > 80 else ''}")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="AutoPaste server")
    parser.add_argument("--port", type=int, default=9999)
    args = parser.parse_args()

    class ReusableHTTPServer(HTTPServer):
        allow_reuse_address = True

    server = ReusableHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"AutoPaste listening on http://0.0.0.0:{args.port}")
    print("Send text:  curl -X POST http://<your-ip>:{} -d 'hello'".format(args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
