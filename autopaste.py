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


def press_key(key_code, flags=0, label=""):
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    print(f"  [key] {label} key_code={key_code} flags={flags:#x} src={src}")
    down = Quartz.CGEventCreateKeyboardEvent(src, key_code, True)
    up = Quartz.CGEventCreateKeyboardEvent(src, key_code, False)
    if flags:
        Quartz.CGEventSetFlags(down, flags)
        Quartz.CGEventSetFlags(up, flags)
    print(f"  [key] posting key_down={down} key_up={up}")
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    time.sleep(0.02)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
    time.sleep(0.02)
    print(f"  [key] {label} done")


def simulate_paste():
    print("[paste] simulating Cmd+V")
    press_key(9, Quartz.kCGEventFlagMaskCommand, label="Cmd+V")
    print("[paste] done")


def simulate_send():
    print("[send] simulating Enter via osascript")
    subprocess.run([
        "osascript", "-e",
        'tell application "System Events" to key code 36'
    ], check=True)
    print("[send] Enter done")
    time.sleep(0.1)
    print("[send] simulating Cmd+Enter via osascript")
    subprocess.run([
        "osascript", "-e",
        'tell application "System Events" to key code 36 using command down'
    ], check=True)
    print("[send] Cmd+Enter done")
    print("[send] done")


def copy_and_paste(text: str, auto_send=False):
    print(f"[copy_and_paste] text={text[:80]!r} auto_send={auto_send}")
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    print("[copy_and_paste] clipboard set")
    time.sleep(0.05)
    simulate_paste()
    if auto_send:
        print("[copy_and_paste] waiting before auto-send...")
        time.sleep(0.15)
        simulate_send()
    else:
        print("[copy_and_paste] auto_send is OFF, skipping send")
    print("[copy_and_paste] finished")


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
            copy_and_paste(text, auto_send=self.server.auto_send)
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
    parser.add_argument("--auto-send", action="store_true",
                        help="After pasting, simulate Enter and Cmd+Enter to send")
    args = parser.parse_args()

    class ReusableHTTPServer(HTTPServer):
        allow_reuse_address = True
        auto_send = False

    server = ReusableHTTPServer(("0.0.0.0", args.port), Handler)
    server.auto_send = args.auto_send
    print(f"AutoPaste listening on http://0.0.0.0:{args.port}")
    if args.auto_send:
        print("Auto-send ENABLED (Enter + Cmd+Enter after paste)")
    print("Send text:  curl -X POST http://<your-ip>:{} -d 'hello'".format(args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
