import Foundation
import Vision

enum ToolError: Error { case usage, noObservation, incompatibleFeature }

func encode(imagePath: String, outputPath: String) throws {
    let request = VNGenerateImageFeaturePrintRequest()
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: imagePath), options: [:])
    try handler.perform([request])
    guard let observation = request.results?.first as? VNFeaturePrintObservation else { throw ToolError.noObservation }
    let data = try NSKeyedArchiver.archivedData(withRootObject: observation, requiringSecureCoding: true)
    try data.write(to: URL(fileURLWithPath: outputPath), options: .atomic)
    print("{\"engine\":\"apple-vision-featureprint\",\"revision\":\(request.revision)}")
}

func load(_ path: String) throws -> VNFeaturePrintObservation {
    let data = try Data(contentsOf: URL(fileURLWithPath: path))
    guard let value = try NSKeyedUnarchiver.unarchivedObject(ofClass: VNFeaturePrintObservation.self, from: data) else { throw ToolError.incompatibleFeature }
    return value
}

func distance(_ first: String, _ second: String) throws {
    let a = try load(first), b = try load(second)
    var value: Float = 0
    try a.computeDistance(&value, to: b)
    print(String(format: "%.9f", value))
}

do {
    let args = CommandLine.arguments
    guard args.count == 4 else { throw ToolError.usage }
    if args[1] == "encode" { try encode(imagePath: args[2], outputPath: args[3]) }
    else if args[1] == "distance" { try distance(args[2], args[3]) }
    else { throw ToolError.usage }
} catch {
    FileHandle.standardError.write("avds-vision: \(error)\n".data(using: .utf8)!)
    exit(2)
}
