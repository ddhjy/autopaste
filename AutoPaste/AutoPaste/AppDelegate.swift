import Cocoa

class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private var titleItem: NSMenuItem!
    private var portItem: NSMenuItem!
    private var toggleItem: NSMenuItem!
    private var serverItem: NSMenuItem!

    private var port: UInt16 = 7788
    private var autoSend = false
    private var server: HTTPServer?
    private var serverRunning = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        updateIcon()
        buildMenu()
        startServer()
    }

    private func updateIcon() {
        statusItem.button?.image = StatusBarIcon.make(autoSend: autoSend, running: serverRunning)
    }

    private func buildMenu() {
        let menu = NSMenu()

        titleItem = NSMenuItem(title: "AutoPaste  :\(port)", action: nil, keyEquivalent: "")
        titleItem.isEnabled = false
        menu.addItem(titleItem)
        menu.addItem(.separator())

        portItem = NSMenuItem(title: "Port: \(port)", action: #selector(changePort(_:)), keyEquivalent: "")
        portItem.target = self
        menu.addItem(portItem)

        toggleItem = NSMenuItem(title: "Auto Send", action: #selector(toggleAutoSend(_:)), keyEquivalent: "")
        toggleItem.target = self
        toggleItem.state = autoSend ? .on : .off
        menu.addItem(toggleItem)

        serverItem = NSMenuItem(title: "Server: Running", action: #selector(toggleServer(_:)), keyEquivalent: "")
        serverItem.target = self
        menu.addItem(serverItem)

        menu.addItem(.separator())

        let quitItem = NSMenuItem(title: "Quit", action: #selector(quitApp(_:)), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem.menu = menu
    }

    @objc private func changePort(_ sender: NSMenuItem) {
        let alert = NSAlert()
        alert.messageText = "Change Port"
        alert.informativeText = "Enter the new port number:"
        alert.addButton(withTitle: "OK")
        alert.addButton(withTitle: "Cancel")

        let inputField = NSTextField(frame: NSRect(x: 0, y: 0, width: 200, height: 24))
        inputField.stringValue = String(port)
        alert.accessoryView = inputField
        alert.window.initialFirstResponder = inputField

        let response = alert.runModal()
        guard response == .alertFirstButtonReturn else { return }

        guard let newPort = UInt16(inputField.stringValue), newPort >= 1 else { return }
        guard newPort != port else { return }

        port = newPort
        titleItem.title = "AutoPaste  :\(port)"
        portItem.title = "Port: \(port)"

        if serverRunning {
            stopServer()
            startServer()
        }
    }

    @objc private func toggleAutoSend(_ sender: NSMenuItem) {
        autoSend = !autoSend
        sender.state = autoSend ? .on : .off
        server?.autoSend = autoSend
        updateIcon()
    }

    @objc private func toggleServer(_ sender: NSMenuItem) {
        if serverRunning {
            stopServer()
        } else {
            startServer()
        }
    }

    @objc private func quitApp(_ sender: NSMenuItem) {
        stopServer()
        NSApplication.shared.terminate(self)
    }

    private func startServer() {
        guard !serverRunning else { return }
        let srv = HTTPServer()
        srv.autoSend = autoSend
        srv.onRequest = { text, autoSend in
            PasteService.copyAndPaste(text: text, autoSend: autoSend)
        }
        do {
            try srv.start(port: port)
            server = srv
            serverRunning = true
            serverItem.title = "Server: Running"
            updateIcon()
            print("AutoPaste listening on http://0.0.0.0:\(port)")
        } catch {
            print("Failed to start server: \(error)")
        }
    }

    private func stopServer() {
        guard serverRunning else { return }
        server?.stop()
        server = nil
        serverRunning = false
        serverItem.title = "Server: Stopped"
        updateIcon()
    }
}
