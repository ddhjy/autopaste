import Cocoa
import ApplicationServices
import SystemConfiguration

class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private var titleItem: NSMenuItem!
    private var ipItem: NSMenuItem!
    private var portItem: NSMenuItem!
    private var toggleItem: NSMenuItem!
    private var serverItem: NSMenuItem!
    private var accessibilityItem: NSMenuItem!

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

    private func checkAccessibilityPermission() -> Bool {
        return AXIsProcessTrusted()
    }

    private func buildMenu() {
        let menu = NSMenu()
        menu.delegate = self

        titleItem = NSMenuItem(title: "AutoPaste  :\(port)", action: nil, keyEquivalent: "")
        titleItem.isEnabled = false
        menu.addItem(titleItem)
        menu.addItem(.separator())

        ipItem = NSMenuItem(title: "IP: \(localIPSummary())", action: nil, keyEquivalent: "")
        ipItem.isEnabled = false
        menu.addItem(ipItem)

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

        accessibilityItem = NSMenuItem(title: "Accessibility: Checking...", action: #selector(openAccessibilitySettings(_:)), keyEquivalent: "")
        accessibilityItem.target = self
        menu.addItem(accessibilityItem)
        updateAccessibilityStatus()

        menu.addItem(.separator())

        let quitItem = NSMenuItem(title: "Quit", action: #selector(quitApp(_:)), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem.menu = menu
    }

    private func updateAccessibilityStatus() {
        let granted = checkAccessibilityPermission()
        if granted {
            accessibilityItem.title = "Accessibility: Granted"
            accessibilityItem.image = NSImage(systemSymbolName: "checkmark.circle.fill", accessibilityDescription: "Granted")
        } else {
            accessibilityItem.title = "Accessibility: Not Granted (Click to Fix)"
            accessibilityItem.image = NSImage(systemSymbolName: "xmark.circle.fill", accessibilityDescription: "Not Granted")
        }
    }

    @objc private func openAccessibilitySettings(_ sender: NSMenuItem) {
        let granted = checkAccessibilityPermission()
        if !granted {
            // 触发系统权限请求对话框
            let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
            AXIsProcessTrustedWithOptions(options)
        }
        // 打开系统设置的辅助功能页面
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
            NSWorkspace.shared.open(url)
        }
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

    private func localIPSummary() -> String {
        let entries = localIPAddresses()
        guard !entries.isEmpty else { return "Unknown" }
        return entries.map { "\($0.label): \($0.address)" }.joined(separator: "  |  ")
    }

    private func localIPAddresses() -> [(label: String, address: String, rank: Int)] {
        var addresses: [(label: String, address: String, rank: Int)] = []
        var seen = Set<String>()
        let interfaceKinds = networkInterfaceKinds()
        var ifaddr: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifaddr) == 0, let firstAddr = ifaddr else { return addresses }
        defer { freeifaddrs(ifaddr) }

        for ptr in sequence(first: firstAddr, next: { $0.pointee.ifa_next }) {
            guard let addrPointer = ptr.pointee.ifa_addr else { continue }
            let flags = Int32(ptr.pointee.ifa_flags)
            guard (flags & IFF_UP) != 0, (flags & IFF_RUNNING) != 0, (flags & IFF_LOOPBACK) == 0 else { continue }

            let sa = addrPointer.pointee
            guard sa.sa_family == UInt8(AF_INET) else { continue }

            let name = String(cString: ptr.pointee.ifa_name)
            guard let info = displayInfo(for: name, kinds: interfaceKinds) else { continue }

            var addr = addrPointer.withMemoryRebound(to: sockaddr_in.self, capacity: 1) { $0.pointee }
            var buf = [CChar](repeating: 0, count: Int(INET_ADDRSTRLEN))
            guard inet_ntop(AF_INET, &addr.sin_addr, &buf, socklen_t(INET_ADDRSTRLEN)) != nil else { continue }

            let ip = String(cString: buf)
            let key = "\(name)|\(ip)"
            guard seen.insert(key).inserted else { continue }

            addresses.append((label: "\(info.label)(\(name))", address: ip, rank: info.rank))
        }

        return addresses.sorted {
            if $0.rank != $1.rank { return $0.rank < $1.rank }
            if $0.label != $1.label { return $0.label < $1.label }
            return $0.address < $1.address
        }
    }

    private func networkInterfaceKinds() -> [String: String] {
        guard let interfaces = SCNetworkInterfaceCopyAll() as? [SCNetworkInterface] else { return [:] }
        var kinds: [String: String] = [:]

        for interface in interfaces {
            guard let bsdName = SCNetworkInterfaceGetBSDName(interface) as String?,
                  let interfaceType = SCNetworkInterfaceGetInterfaceType(interface) as String? else {
                continue
            }

            if interfaceType == kSCNetworkInterfaceTypeIEEE80211 as String {
                kinds[bsdName] = "Wi-Fi"
            } else if interfaceType == kSCNetworkInterfaceTypeEthernet as String {
                kinds[bsdName] = "Ethernet"
            }
        }

        return kinds
    }

    private func displayInfo(for bsdName: String, kinds: [String: String]) -> (label: String, rank: Int)? {
        if let kind = kinds[bsdName] {
            return kind == "Wi-Fi" ? ("Wi-Fi", 0) : ("Ethernet", 1)
        }

        if bsdName.hasPrefix("en") {
            return ("Ethernet", 1)
        }

        return nil
    }

    private func refreshIPItem() {
        ipItem.title = "IP: \(localIPSummary())"
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

extension AppDelegate: NSMenuDelegate {
    func menuWillOpen(_ menu: NSMenu) {
        refreshIPItem()
        updateAccessibilityStatus()
    }
}
