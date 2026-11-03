// Draws the Scout Advancement Tool app icon (1024x1024 PNG). Usage: swift make_icon.swift out.png
import AppKit

let size: CGFloat = 1024
let out = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "icon.png"

let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(size), pixelsHigh: Int(size),
                           bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                           colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)

// macOS-style rounded square with a navy gradient
let inset: CGFloat = 100
let body = NSRect(x: inset, y: inset, width: size - 2 * inset, height: size - 2 * inset)
let shape = NSBezierPath(roundedRect: body, xRadius: 185, yRadius: 185)
NSGraphicsContext.saveGraphicsState()
let shadow = NSShadow()
shadow.shadowColor = NSColor.black.withAlphaComponent(0.3)
shadow.shadowBlurRadius = 30
shadow.shadowOffset = NSSize(width: 0, height: -12)
shadow.set()
NSColor(red: 0.07, green: 0.19, blue: 0.35, alpha: 1).setFill()
shape.fill()
NSGraphicsContext.restoreGraphicsState()
NSGradient(starting: NSColor(red: 0.20, green: 0.40, blue: 0.68, alpha: 1),
           ending: NSColor(red: 0.07, green: 0.19, blue: 0.35, alpha: 1))!.draw(in: shape, angle: -90)

// A checklist: three rows of box + bar, using the report's category colors
let rowColors = [NSColor(red: 0.42, green: 0.30, blue: 0.58, alpha: 1),   // Discuss
                 NSColor(red: 0.18, green: 0.49, blue: 0.20, alpha: 1),   // Outdoor
                 NSColor(red: 0.85, green: 0.48, blue: 0.02, alpha: 1)]   // On Own
for (i, color) in rowColors.enumerated() {
    let y = 640 - CGFloat(i) * 170
    let box = NSRect(x: 245, y: y, width: 120, height: 120)
    NSColor.white.setFill()
    NSBezierPath(roundedRect: box, xRadius: 24, yRadius: 24).fill()
    if i < 2 {  // first two rows checked off
        let check = NSBezierPath()
        check.move(to: NSPoint(x: box.minX + 26, y: box.minY + 62))
        check.line(to: NSPoint(x: box.minX + 52, y: box.minY + 34))
        check.line(to: NSPoint(x: box.minX + 96, y: box.minY + 90))
        check.lineWidth = 20
        check.lineCapStyle = .round
        check.lineJoinStyle = .round
        NSColor(red: 0.13, green: 0.59, blue: 0.95, alpha: 1).setStroke()
        check.stroke()
    }
    color.setFill()
    NSBezierPath(roundedRect: NSRect(x: 410, y: y + 30, width: 370, height: 60), xRadius: 30, yRadius: 30).fill()
}

try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: out))
