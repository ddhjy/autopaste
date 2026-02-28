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
        pressKey(9, flags: [.maskCommand]) // v
    }

    private static func simulateSend() {
        pressKey(36) // return
        usleep(100_000)
        pressKey(36, flags: [.maskCommand]) // cmd + return
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
