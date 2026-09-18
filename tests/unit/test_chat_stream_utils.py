"""Tests for streaming chat JSON preview helper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from llm.chat_stream_utils import preview_json_content_field


def test_preview_partial_content_field():
    partial = '{"content": "Hello wor'
    assert preview_json_content_field(partial) == "Hello wor"


def test_preview_decodes_newlines():
    partial = '{"content": "Line one\\nLine two'
    assert preview_json_content_field(partial) == "Line one\nLine two"


def test_preview_empty_without_content_key():
    assert preview_json_content_field('{"references": []') == ""


if __name__ == "__main__":
    test_preview_partial_content_field()
    test_preview_decodes_newlines()
    test_preview_empty_without_content_key()
    print("Chat stream utils tests: PASSED")
