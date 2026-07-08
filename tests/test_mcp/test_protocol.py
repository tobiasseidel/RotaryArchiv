"""Tests for MCP JSON-RPC 2.0 Protocol."""

import io
import json
import sys
from unittest.mock import patch

import pytest

from src.rotary_archiv.mcp.protocol import (
    make_error,
    make_response,
    read_message,
    write_message,
)


class TestMakeResponse:
    """Tests für make_response."""

    def test_response_with_string_id(self):
        response = make_response("req-123", {"tools": []})
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "req-123"
        assert response["result"] == {"tools": []}

    def test_response_with_int_id(self):
        response = make_response(42, "hello")
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 42
        assert response["result"] == "hello"

    def test_response_with_none_id(self):
        response = make_response(None, {"key": "value"})
        assert response["id"] is None
        assert response["result"] == {"key": "value"}

    def test_response_with_complex_result(self):
        complex_result = {
            "serverInfo": {"name": "rotary-archiv", "version": "1.0.0"},
            "capabilities": {"tools": {"listChanged": False}},
        }
        response = make_response(1, complex_result)
        assert response["result"] == complex_result


class TestMakeError:
    """Tests für make_error."""

    def test_error_with_string_id(self):
        response = make_error("req-1", -32601, "Method not found")
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "req-1"
        assert response["error"]["code"] == -32601
        assert response["error"]["message"] == "Method not found"

    def test_error_with_int_id(self):
        response = make_error(1, -32600, "Invalid Request")
        assert response["id"] == 1
        assert response["error"]["code"] == -32600

    def test_error_with_none_id(self):
        response = make_error(None, -32700, "Parse error")
        assert response["id"] is None
        assert response["error"]["code"] == -32700


class TestWriteMessage:
    """Tests für write_message."""

    def test_write_message(self, capsys):
        msg = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        write_message(msg)
        captured = capsys.readouterr()
        assert captured.out.strip() == json.dumps(msg)

    def test_write_message_newline_delimited(self, capsys):
        msg = {"jsonrpc": "2.0", "id": 1, "result": {}}
        write_message(msg)
        captured = capsys.readouterr()
        assert captured.out.endswith("\n")


class TestReadMessage:
    """Tests für read_message."""

    def test_read_message_success(self):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        mock_stdin = io.StringIO(json.dumps(msg) + "\n")
        with patch.object(sys, "stdin", mock_stdin):
            result = read_message()
        assert result == msg

    def test_read_message_eof(self):
        mock_stdin = io.StringIO("")
        with patch.object(sys, "stdin", mock_stdin), pytest.raises(EOFError):
            read_message()

    def test_read_message_invalid_json(self):
        mock_stdin = io.StringIO("not json\n")
        with (
            patch.object(sys, "stdin", mock_stdin),
            pytest.raises(json.JSONDecodeError),
        ):
            read_message()
