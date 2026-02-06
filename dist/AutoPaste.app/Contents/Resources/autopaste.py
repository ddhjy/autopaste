#!/usr/bin/env python3
"""
AutoPaste - macOS menu bar app that receives text via HTTP and pastes it
into the active input field.

Send text:
    curl -X POST http://localhost:9999 -d 'your text here'
    curl -X POST http://localhost:9999 -H 'Content-Type: application/json' \
         -d '{"text": "your text here"}'
"""

import json
import subprocess
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import Quartz
from AppKit import (
    NSApplication,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSMenu,
    NSMenuItem,
    NSOnState,
    NSOffState,
    NSImage,
    NSObject,
    NSRunLoop,
    NSDefaultRunLoopMode,
    NSDate,
    NSTimer,
)
import objc
from PyObjCTools import AppHelper


# --------------- core paste logic ---------------

def press_key(key_code, flags=0, label=""):
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    down = Quartz.CGEventCreateKeyboardEvent(src, key_code, True)
    up = Quartz.CGEventCreateKeyboardEvent(src, key_code, False)
    if flags:
        Quartz.CGEventSetFlags(down, flags)
        Quartz.CGEventSetFlags(up, flags)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    time.sleep(0.02)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
    time.sleep(0.02)


def simulate_paste():
    press_key(9, Quartz.kCGEventFlagMaskCommand, label="Cmd+V")


def simulate_send():
    subprocess.run([
        "osascript", "-e",
        'tell application "System Events" to key code 36'
    ], check=True)
    time.sleep(0.1)
    subprocess.run([
        "osascript", "-e",
        'tell application "System Events" to key code 36 using command down'
    ], check=True)


def copy_and_paste(text: str, auto_send=False):
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    time.sleep(0.05)
    simulate_paste()
    if auto_send:
        time.sleep(0.15)
        simulate_send()


# --------------- HTTP server ---------------

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
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        pass


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True
    auto_send = False


# --------------- macOS menu bar app ---------------

class AppDelegate(NSObject):
    def initWithPort_autoSend_(self, port, auto_send):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self._port = port
        self._auto_send = auto_send
        self._server = None
        self._server_thread = None
        self._running = False
        return self

    def applicationDidFinishLaunching_(self, notification):
        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        self._status_item.setTitle_("📋")
        self._status_item.setHighlightMode_(True)

        self._build_menu()
        self._start_server()

    def _build_menu(self):
        menu = NSMenu.alloc().init()

        title = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"AutoPaste  :{self._port}", None, ""
        )
        title.setEnabled_(False)
        menu.addItem_(title)
        menu.addItem_(NSMenuItem.separatorItem())

        self._toggle_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Auto Send", "toggleAutoSend:", ""
        )
        self._toggle_item.setTarget_(self)
        self._toggle_item.setState_(NSOnState if self._auto_send else NSOffState)
        menu.addItem_(self._toggle_item)

        self._server_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Server: Running", "toggleServer:", ""
        )
        self._server_item.setTarget_(self)
        menu.addItem_(self._server_item)

        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "quitApp:", "q"
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        self._status_item.setMenu_(menu)

    # --- actions ---

    def toggleAutoSend_(self, sender):
        self._auto_send = not self._auto_send
        sender.setState_(NSOnState if self._auto_send else NSOffState)
        if self._server:
            self._server.auto_send = self._auto_send

    def toggleServer_(self, sender):
        if self._running:
            self._stop_server()
        else:
            self._start_server()

    def quitApp_(self, sender):
        self._stop_server()
        NSApplication.sharedApplication().terminate_(self)

    # --- server lifecycle ---

    def _start_server(self):
        if self._running:
            return
        self._server = ReusableHTTPServer(("0.0.0.0", self._port), Handler)
        self._server.auto_send = self._auto_send
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()
        self._running = True
        self._server_item.setTitle_("Server: Running")
        self._status_item.setTitle_("📋")
        print(f"AutoPaste listening on http://0.0.0.0:{self._port}")

    def _stop_server(self):
        if not self._running:
            return
        self._server.shutdown()
        self._server_thread.join(timeout=3)
        self._server = None
        self._server_thread = None
        self._running = False
        self._server_item.setTitle_("Server: Stopped")
        self._status_item.setTitle_("📋⏸")


# --------------- main ---------------

DEFAULT_PORT = 9999

def main():
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().initWithPort_autoSend_(DEFAULT_PORT, False)
    app.setDelegate_(delegate)
    app.setActivationPolicy_(1)  # NSApplicationActivationPolicyAccessory — no dock icon
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
