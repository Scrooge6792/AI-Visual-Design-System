import AppKit
import Foundation
import LocalAuthentication

let context = LAContext()
var authError: NSError?
let biometricsAvailable = context.canEvaluatePolicy(
    .deviceOwnerAuthenticationWithBiometrics,
    error: &authError
)

let bitmap = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: 64,
    pixelsHigh: 64,
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: 0,
    bitsPerPixel: 0
)
if let bitmap {
    let blue = NSColor(calibratedRed: 0.10, green: 0.35, blue: 0.95, alpha: 1)
    let yellow = NSColor(calibratedRed: 1.0, green: 0.78, blue: 0.08, alpha: 1)
    for x in 0..<64 {
        for y in 0..<64 {
            bitmap.setColor(x < 32 ? blue : yellow, atX: x, y: y)
        }
    }
}
let pngData = bitmap?.representation(using: .png, properties: [:])
let pngDecodingAvailable = pngData != nil
if let pngData {
    try pngData.write(to: URL(fileURLWithPath: ".build/phase0/account-analysis-fixture.png"), options: .atomic)
}

print("macOS=\(ProcessInfo.processInfo.operatingSystemVersionString)")
print("biometrics=\(biometricsAvailable)")
print("biometryType=\(context.biometryType.rawValue)")
print("nativePNG=\(pngDecodingAvailable)")
if let authError {
    print("biometryError=\(authError.domain):\(authError.code)")
}
