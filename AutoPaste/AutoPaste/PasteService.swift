import Cocoa
import CoreGraphics

enum PasteService {
    private static func pressKey(_ keyCode: CGKeyCode, flags: CGEventFlags = [], delay: useconds_t = 20_000) {
        let src = CGEventSource(stateID: .hidSystemState)
        guard let down = CGEvent(keyboardEventSource: src, virtualKey: keyCode, keyDown: true),
              let up = CGEvent(keyboardEventSource: src, virtualKey: keyCode, keyDown: false) else { return }
        if !flags.isEmpty {
            down.flags = flags
            up.flags = flags
        }
        down.post(tap: .cghidEventTap)
        usleep(delay)
        up.post(tap: .cghidEventTap)
        usleep(delay)
    }

    private static func simulatePaste() {
        pressKey(9, flags: .maskCommand)
    }

    private static func simulateSend() {
        let enterScript = "tell application \"System Events\" to key code 36"
        let cmdEnterScript = "tell application \"System Events\" to key code 36 using command down"

        let p1 = Process()
        p1.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
        p1.arguments = ["-e", enterScript]
        try? p1.run()
        p1.waitUntilExit()

        usleep(100_000)

        let p2 = Process()
        p2.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
        p2.arguments = ["-e", cmdEnterScript]
        try? p2.run()
        p2.waitUntilExit()
    }

    static func copyAndPaste(text: String, autoSend: Bool) {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)

        usleep(50_000)
        simulatePaste()

        if autoSend {
            usleep(150_000)
            simulateSend()
        }
    }
}
