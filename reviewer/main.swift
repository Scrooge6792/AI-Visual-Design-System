import AppKit
import Darwin
import Foundation
import LocalAuthentication

final class CoreClient {
    let socketPath: String
    init(socketPath: String) { self.socketPath = socketPath }

    func send(_ object: [String: Any]) throws -> [String: Any] {
        let fd = Darwin.socket(AF_UNIX, SOCK_STREAM, 0)
        guard fd >= 0 else { throw NSError(domain: NSPOSIXErrorDomain, code: Int(errno)) }
        defer { Darwin.close(fd) }
        var address = sockaddr_un()
        address.sun_family = sa_family_t(AF_UNIX)
        let maxLength = MemoryLayout.size(ofValue: address.sun_path)
        guard socketPath.utf8.count < maxLength else { throw NSError(domain: "AVDS", code: 1, userInfo: [NSLocalizedDescriptionKey: "Socket path too long"]) }
        withUnsafeMutableBytes(of: &address.sun_path) { bytes in
            bytes.initializeMemory(as: UInt8.self, repeating: 0)
            for (index, byte) in socketPath.utf8.enumerated() { bytes[index] = byte }
        }
        let result = withUnsafePointer(to: &address) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.connect(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
            }
        }
        guard result == 0 else { throw NSError(domain: NSPOSIXErrorDomain, code: Int(errno)) }
        var data = try JSONSerialization.data(withJSONObject: object)
        data.append(0x0A)
        try data.withUnsafeBytes { raw in
            var offset = 0
            while offset < raw.count {
                let count = Darwin.write(fd, raw.baseAddress!.advanced(by: offset), raw.count - offset)
                if count <= 0 { throw NSError(domain: NSPOSIXErrorDomain, code: Int(errno)) }
                offset += count
            }
        }
        var response = Data()
        var byte: UInt8 = 0
        while Darwin.read(fd, &byte, 1) == 1 {
            if byte == 0x0A { break }
            response.append(byte)
        }
        guard let value = try JSONSerialization.jsonObject(with: response) as? [String: Any] else {
            throw NSError(domain: "AVDS", code: 2, userInfo: [NSLocalizedDescriptionKey: "Invalid Core response"])
        }
        return value
    }
}

final class ReviewerController: NSObject, NSApplicationDelegate, NSTableViewDataSource, NSTableViewDelegate {
    let client: CoreClient
    var proposals: [[String: Any]] = []
    let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 980, height: 680),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
    let table = NSTableView()
    let detail = NSTextView()
    let imageView = NSImageView()
    let status = NSTextField(labelWithString: "")

    init(socketPath: String) { self.client = CoreClient(socketPath: socketPath); super.init() }

    func applicationDidFinishLaunching(_ notification: Notification) {
        window.title = "AI Visual Design Reviewer"
        window.center()
        let root = NSSplitView(frame: window.contentView!.bounds)
        root.autoresizingMask = [.width, .height]
        root.isVertical = true
        let left = NSScrollView(); left.hasVerticalScroller = true; left.documentView = table
        let column = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("proposal")); column.title = "待审提案"; column.width = 280
        table.addTableColumn(column); table.headerView = nil; table.delegate = self; table.dataSource = self
        table.allowsMultipleSelection = true
        let right = NSView()
        imageView.imageScaling = .scaleProportionallyUpOrDown
        let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.documentView = detail
        detail.isEditable = false; detail.font = .monospacedSystemFont(ofSize: 12, weight: .regular)
        let approve = button("批准所选", #selector(approve)); let reject = button("拒绝", #selector(reject))
        let changes = button("退回修改", #selector(requestChanges)); let deferButton = button("稍后", #selector(deferCurrent))
        let deferRemaining = button("本批次后续全部稍后", #selector(deferRemainingBatch))
        let reloadButton = button("刷新", #selector(reload))
        let buttons = NSStackView(views: [approve, reject, changes, deferButton, deferRemaining, reloadButton]); buttons.orientation = .horizontal; buttons.spacing = 8
        let stack = NSStackView(views: [imageView, scroll, buttons, status]); stack.orientation = .vertical; stack.spacing = 8
        stack.translatesAutoresizingMaskIntoConstraints = false; right.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: right.leadingAnchor, constant: 10), stack.trailingAnchor.constraint(equalTo: right.trailingAnchor, constant: -10),
            stack.topAnchor.constraint(equalTo: right.topAnchor, constant: 10), stack.bottomAnchor.constraint(equalTo: right.bottomAnchor, constant: -10),
            imageView.heightAnchor.constraint(equalToConstant: 220), scroll.heightAnchor.constraint(greaterThanOrEqualToConstant: 280)
        ])
        root.addArrangedSubview(left); root.addArrangedSubview(right); root.setPosition(300, ofDividerAt: 0)
        window.contentView = root; window.makeKeyAndOrderFront(nil); reload()
    }

    func button(_ title: String, _ action: Selector) -> NSButton {
        let value = NSButton(title: title, target: self, action: action); value.bezelStyle = .rounded; return value
    }
    func numberOfRows(in tableView: NSTableView) -> Int { proposals.count }
    func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
        let field = NSTextField(labelWithString: "\(proposals[row]["operation"] ?? "")\n\(proposals[row]["proposal_id"] ?? "")")
        field.lineBreakMode = .byTruncatingMiddle; return field
    }
    func tableViewSelectionDidChange(_ notification: Notification) { showSelected() }

    @objc func reload() {
        do {
            let response = try client.send(["command": "review.list"])
            guard response["ok"] as? Bool == true,
                  let result = response["result"] as? [String: Any],
                  let items = result["items"] as? [[String: Any]] else { throw responseError(response) }
            proposals = items; table.reloadData(); if !items.isEmpty { table.selectRowIndexes(IndexSet(integer: 0), byExtendingSelection: false) }
            status.stringValue = "待审 \(items.count) 项"
        } catch { status.stringValue = "读取失败：\(error.localizedDescription)" }
    }

    func showSelected() {
        guard table.selectedRow >= 0, table.selectedRow < proposals.count else { return }
        let proposal = proposals[table.selectedRow]
        if let data = try? JSONSerialization.data(withJSONObject: proposal, options: [.prettyPrinted, .sortedKeys]), let text = String(data: data, encoding: .utf8) { detail.string = text }
        imageView.image = nil
        if let body = proposal["body"] as? [String: Any], let queueID = body["queue_item_id"] as? String,
           let response = try? client.send(["command": "queue.preview", "queue_item_id": queueID]),
           let result = response["result"] as? [String: Any], let path = result["content_path"] as? String { imageView.image = NSImage(contentsOfFile: path) }
        else if let body = proposal["body"] as? [String: Any], let assetID = body["asset_id"] as? String,
                let response = try? client.send(["command": "asset.preview", "asset_id": assetID]),
                let result = response["result"] as? [String: Any], let path = result["content_path"] as? String { imageView.image = NSImage(contentsOfFile: path) }
    }

    func responseError(_ response: [String: Any]) -> NSError {
        let error = response["error"] as? [String: Any]
        return NSError(domain: "AVDS", code: 3, userInfo: [NSLocalizedDescriptionKey: error?["message"] ?? "Core request failed"])
    }

    func authenticateAndPerform(action: String, remainingBatch: Bool = false) {
        let indexes = table.selectedRowIndexes.isEmpty ? IndexSet(integer: max(table.selectedRow, 0)) : table.selectedRowIndexes
        let selected = indexes.compactMap { $0 < proposals.count ? proposals[$0] : nil }
        guard !selected.isEmpty else { return }
        let context = LAContext(); context.localizedFallbackTitle = ""
        var error: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            status.stringValue = "Touch ID 不可用：\(error?.localizedDescription ?? "unknown")"; return
        }
        let identifiers = selected.compactMap { $0["proposal_id"] as? String }.joined(separator: ", ")
        let reason = "确认对 \(selected.count) 个提案执行“\(action)”：\(identifiers)"
        context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: reason) { [weak self] success, authError in
            DispatchQueue.main.async {
                guard let self else { return }
                guard success else { self.status.stringValue = "未授权：\(authError?.localizedDescription ?? "Touch ID failed")"; return }
                do {
                    var completed = 0
                    for proposal in selected {
                        let proposalID = proposal["proposal_id"] as! String
                        let proposalRevision = proposal["revision"] as! Int
                        var effectiveAction = action
                        var request: [String: Any]
                        if (remainingBatch || action == "defer_current"),
                           let body = proposal["body"] as? [String: Any], let queueID = body["queue_item_id"] as? String {
                            let queueResponse = try self.client.send(["command": "queue.get", "queue_item_id": queueID])
                            guard queueResponse["ok"] as? Bool == true,
                                  let queue = queueResponse["result"] as? [String: Any], let batchID = queue["batch_id"] else { throw self.responseError(queueResponse) }
                            if remainingBatch {
                                effectiveAction = "defer_remaining_batch"
                                request = ["command": "review.action", "action": effectiveAction, "batch_id": batchID,
                                           "operation_id": "review_batch_\(batchID)"]
                            } else {
                                request = ["command": "review.action", "action": "defer_current", "queue_item_id": queueID,
                                           "operation_id": "review_defer_\(queueID)"]
                            }
                        } else {
                            let stableOperationID = "review_\(proposalID)_r\(proposalRevision)_\(effectiveAction)"
                            request = ["command": "review.action", "action": effectiveAction,
                                "proposal_id": proposalID, "revision": proposalRevision,
                                "proposal_hash": proposal["proposal_hash"]!, "target_revision": (proposal["body"] as? [String: Any])?["target_revision"] ?? 0,
                                "operation_id": stableOperationID]
                            if let body = proposal["body"] as? [String: Any], let hash = body["file_hash"] { request["file_hash"] = hash }
                        }
                        let response = try self.client.send(request)
                        guard response["ok"] as? Bool == true else { throw self.responseError(response) }
                        completed += 1
                        if remainingBatch { break }
                    }
                    self.status.stringValue = "已完成 \(completed) 项动作"; self.reload()
                } catch { self.status.stringValue = "动作失败：\(error.localizedDescription)" }
            }
        }
    }
    @objc func approve() { authenticateAndPerform(action: "approve") }
    @objc func reject() { authenticateAndPerform(action: "reject") }
    @objc func requestChanges() { authenticateAndPerform(action: "request_changes") }
    @objc func deferCurrent() { authenticateAndPerform(action: "defer_current") }
    @objc func deferRemainingBatch() { authenticateAndPerform(action: "defer_remaining_batch", remainingBatch: true) }
}

let app = NSApplication.shared
app.setActivationPolicy(.regular)
let args = CommandLine.arguments
let socketPath: String
if let index = args.firstIndex(of: "--socket"), index + 1 < args.count { socketPath = args[index + 1] }
else { socketPath = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/AIVisualDesign/core.sock").path }
let delegate = ReviewerController(socketPath: socketPath)
app.delegate = delegate
app.run()
