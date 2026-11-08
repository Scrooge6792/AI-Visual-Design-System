from __future__ import annotations

import json
import re
from pathlib import Path

from .errors import AVDSError


def _type_matches(value, expected):
    if isinstance(expected, list): return any(_type_matches(value, item) for item in expected)
    return {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str),
            "integer": isinstance(value, int) and not isinstance(value, bool), "null": value is None,
            "boolean": isinstance(value, bool)}.get(expected, True)


def _validate(value, schema, path="$", errors=None):
    errors = errors if errors is not None else []
    if "type" in schema and not _type_matches(value, schema["type"]):
        errors.append(f"{path}: type"); return errors
    if "const" in schema and value != schema["const"]: errors.append(f"{path}: const")
    if "enum" in schema and value not in schema["enum"]: errors.append(f"{path}: enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0): errors.append(f"{path}: minLength")
        if schema.get("pattern") and not re.fullmatch(schema["pattern"], value): errors.append(f"{path}: pattern")
    if isinstance(value, int) and value < schema.get("minimum", value): errors.append(f"{path}: minimum")
    if isinstance(value, list):
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True, ensure_ascii=False) for x in value}) != len(value): errors.append(f"{path}: uniqueItems")
        for index, item in enumerate(value): _validate(item, schema.get("items", {}), f"{path}[{index}]", errors)
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value: errors.append(f"{path}.{key}: required")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties: errors.append(f"{path}.{key}: additionalProperties")
        for key, subschema in properties.items():
            if key in value: _validate(value[key], subschema, f"{path}.{key}", errors)
    for subschema in schema.get("allOf", []): _validate(value, subschema, path, errors)
    if "oneOf" in schema:
        matches = sum(not _validate(value, item, path, []) for item in schema["oneOf"])
        if matches != 1: errors.append(f"{path}: oneOf")
    if "not" in schema and not _validate(value, schema["not"], path, []): errors.append(f"{path}: not")
    return errors


def validate(name: str, value):
    schema = json.loads((Path(__file__).with_name("schemas") / f"{name}.schema.json").read_text(encoding="utf-8"))
    errors = _validate(value, schema)
    if errors:
        raise AVDSError("VALIDATION_FAILED", "JSON Schema 校验失败：" + "; ".join(errors[:8]))
