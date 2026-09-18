"""Helpers to show chat JSON responses while they stream."""

from __future__ import annotations


def preview_json_content_field(partial_json: str) -> str:
    """Best-effort decode of the \"content\" string from incomplete JSON."""
    key = '"content"'
    pos = partial_json.find(key)
    if pos < 0:
        return ""

    index = pos + len(key)
    length = len(partial_json)
    while index < length and partial_json[index].isspace():
        index += 1
    if index >= length or partial_json[index] != ":":
        return ""
    index += 1
    while index < length and partial_json[index].isspace():
        index += 1
    if index >= length or partial_json[index] != '"':
        return ""
    index += 1

    chars: list[str] = []
    while index < length:
        char = partial_json[index]
        if char == "\\":
            if index + 1 >= length:
                break
            escape = partial_json[index + 1]
            decoded = {
                "n": "\n",
                "r": "\r",
                "t": "\t",
                '"': '"',
                "\\": "\\",
            }.get(escape)
            chars.append(decoded if decoded is not None else escape)
            index += 2
            continue
        if char == '"':
            break
        chars.append(char)
        index += 1
    return "".join(chars)
