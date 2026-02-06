#!/usr/bin/env python3
"""
AutoPaste - macOS menu bar app that receives text via HTTP and pastes it
into the active input field.

Send text:
    curl -X POST http://localhost:7788 -d 'your text here'
    curl -X POST http://localhost:7788 -H 'Content-Type: application/json' \
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
    NSAlert,
    NSApplication,
    NSBezierPath,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSGraphicsContext,
    NSMakeRect,
    NSMakeSize,
    NSMenu,
    NSMenuItem,
    NSImage,
    NSObject,
    NSOffState,
    NSOnState,
    NSRunLoop,
    NSDefaultRunLoopMode,
    NSDate,
    NSStatusBar,
    NSTextField,
    NSTimer,
    NSVariableStatusItemLength,
)
from Foundation import NSDictionary, NSPoint, NSSize
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


# --------------- status bar icon ---------------

def _make_status_icon(auto_send=False, running=True):
    s = 18
    img = NSImage.alloc().initWithSize_(NSMakeSize(s, s))
    img.lockFocus()

    color = NSColor.blackColor()

    # clipboard body
    bp = NSBezierPath.bezierPath()
    r = NSMakeRect(2, 0.5, 14, 15)
    bp.appendBezierPathWithRoundedRect_xRadius_yRadius_(r, 2, 2)
    bp.setLineWidth_(1.4)
    color.set()
    bp.stroke()

    # clipboard clip (top center)
    clip = NSBezierPath.bezierPath()
    clip.appendBezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(6, 13, 6, 4.5), 1.5, 1.5
    )
    clip.setLineWidth_(1.4)
    color.set()
    clip.stroke()

    # lines on clipboard
    color.set()
    for y_off in [4, 7, 10]:
        line = NSBezierPath.bezierPath()
        line.moveToPoint_(NSPoint(5.5, y_off))
        line.lineToPoint_(NSPoint(12.5, y_off))
        line.setLineWidth_(1.2)
        line.stroke()

    if auto_send:
        # draw a small upward arrow (send indicator) at bottom-right
        bg = NSColor.whiteColor()
        bg_circle = NSBezierPath.bezierPath()
        bg_circle.appendBezierPathWithOvalInRect_(NSMakeRect(10, -1, 9, 9))
        bg.set()
        bg_circle.fill()

        arrow = NSBezierPath.bezierPath()
        cx, cy = 14.5, 3.5
        arrow.moveToPoint_(NSPoint(cx, cy + 3.2))  # tip
        arrow.lineToPoint_(NSPoint(cx - 2.4, cy + 0.2))
        arrow.moveToPoint_(NSPoint(cx, cy + 3.2))
        arrow.lineToPoint_(NSPoint(cx + 2.4, cy + 0.2))
        arrow.moveToPoint_(NSPoint(cx, cy + 3.2))
        arrow.lineToPoint_(NSPoint(cx, cy - 1.5))
        arrow.setLineWidth_(1.6)
        color.set()
        arrow.stroke()

    if not running:
        # draw a small pause icon at bottom-right
        color.set()
        for dx in [0, 3]:
            bar = NSBezierPath.bezierPath()
            bar.appendBezierPathWithRect_(NSMakeRect(11 + dx, 0, 1.8, 5))
            bar.fill()

    img.unlockFocus()
    img.setTemplate_(True)
    return img


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

    def _update_icon(self):
        icon = _make_status_icon(auto_send=self._auto_send, running=self._running)
        self._status_item.setImage_(icon)
        self._status_item.setTitle_("")

    def applicationDidFinishLaunching_(self, notification):
        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        self._status_item.setHighlightMode_(True)
        self._update_icon()

        self._build_menu()
        self._start_server()

    def _build_menu(self):
        menu = NSMenu.alloc().init()

        self._title_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"AutoPaste  :{self._port}", None, ""
        )
        self._title_item.setEnabled_(False)
        menu.addItem_(self._title_item)
        menu.addItem_(NSMenuItem.separatorItem())

        self._port_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"Port: {self._port}", "changePort:", ""
        )
        self._port_item.setTarget_(self)
        menu.addItem_(self._port_item)

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

    def changePort_(self, sender):
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Change Port")
        alert.setInformativeText_("Enter the new port number:")
        alert.addButtonWithTitle_("OK")
        alert.addButtonWithTitle_("Cancel")

        input_field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 200, 24))
        input_field.setStringValue_(str(self._port))
        alert.setAccessoryView_(input_field)
        alert.window().setInitialFirstResponder_(input_field)

        response = alert.runModal()
        if response != 1000:  # NSAlertFirstButtonReturn
            return

        try:
            new_port = int(input_field.stringValue())
            if not (1 <= new_port <= 65535):
                raise ValueError
        except ValueError:
            return

        if new_port == self._port:
            return

        self._port = new_port
        self._title_item.setTitle_(f"AutoPaste  :{self._port}")
        self._port_item.setTitle_(f"Port: {self._port}")
        if self._running:
            self._stop_server()
            self._start_server()

    def toggleAutoSend_(self, sender):
        self._auto_send = not self._auto_send
        sender.setState_(NSOnState if self._auto_send else NSOffState)
        if self._server:
            self._server.auto_send = self._auto_send
        self._update_icon()

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
        self._update_icon()
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
        self._update_icon()


# --------------- main ---------------

DEFAULT_PORT = 7788

def main():
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().initWithPort_autoSend_(DEFAULT_PORT, False)
    app.setDelegate_(delegate)
    app.setActivationPolicy_(1)  # NSApplicationActivationPolicyAccessory — no dock icon
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
