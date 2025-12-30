"""
Tests for file operations tool.
"""

import json
import os
import tempfile
from pathlib import Path
from tools.native.file_ops import read_file, write_file, READ_FILE_SCHEMA, WRITE_FILE_SCHEMA


def test_write_file_overwrite():
    """Test writing a new file with overwrite mode"""
    # Use a test file within the workspace
    test_file = "tests/test_temp_write.txt"
    content = "Hello, World!\nThis is a test file."

    result = write_file(test_file, content, mode="overwrite")
    data = json.loads(result)

    assert data["status"] == "success"
    assert data["mode"] == "overwrite"
    assert data["bytes_written"] == len(content)
    assert data["lines_written"] == 2

    # Verify file was created
    assert Path(test_file).exists()
    with open(test_file, 'r') as f:
        assert f.read() == content

    # Clean up
    Path(test_file).unlink(missing_ok=True)

    print("✅ Write file overwrite test passed")


def test_write_file_append():
    """Test appending to an existing file"""
    test_file = "tests/test_temp_append.txt"
    initial_content = "Initial content\n"
    append_content = "Appended content\n"

    # Write initial content
    write_file(test_file, initial_content, mode="overwrite")

    # Append more content
    result = write_file(test_file, append_content, mode="append")
    data = json.loads(result)

    assert data["status"] == "success"
    assert data["mode"] == "append"
    assert data["bytes_written"] == len(append_content)

    # Verify content
    with open(test_file, 'r') as f:
        full_content = f.read()
        assert full_content == initial_content + append_content

    # Clean up
    Path(test_file).unlink(missing_ok=True)

    print("✅ Write file append test passed")


def test_read_file_full():
    """Test reading entire file"""
    test_file = "tests/test_temp_read.txt"
    content = "Line 1\nLine 2\nLine 3\n"

    with open(test_file, 'w') as f:
        f.write(content)

    result = read_file(test_file)
    data = json.loads(result)

    assert data["status"] == "success"
    assert data["content"] == content
    assert data["lines_read"] == 3
    assert data["total_lines"] == 3

    # Clean up
    Path(test_file).unlink(missing_ok=True)

    print("✅ Read file full test passed")


def test_read_file_partial():
    """Test reading partial file content"""
    test_file = "tests/test_temp_partial.txt"
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"

    with open(test_file, 'w') as f:
        f.write(content)

    result = read_file(test_file, start_line=2, end_line=4)
    data = json.loads(result)

    assert data["status"] == "success"
    assert data["content"] == "Line 2\nLine 3\nLine 4\n"
    assert data["lines_read"] == 3
    assert data["total_lines"] == 5

    # Clean up
    Path(test_file).unlink(missing_ok=True)

    print("✅ Read file partial test passed")


def test_read_file_nonexistent():
    """Test reading nonexistent file"""
    result = read_file("nonexistent_file.txt")
    data = json.loads(result)

    assert data["status"] == "error"
    assert "does not exist" in data["message"]

    print("✅ Read nonexistent file test passed")


def test_write_file_empty_path():
    """Test writing with empty path"""
    result = write_file("", "content")
    data = json.loads(result)

    assert data["status"] == "error"
    assert "empty" in data["message"].lower()

    print("✅ Write empty path test passed")


def test_read_file_empty_path():
    """Test reading with empty path"""
    result = read_file("")
    data = json.loads(result)

    assert data["status"] == "error"
    assert "empty" in data["message"].lower()

    print("✅ Read empty path test passed")


def test_write_file_invalid_mode():
    """Test writing with invalid mode"""
    result = write_file("test.txt", "content", mode="invalid")
    data = json.loads(result)

    assert data["status"] == "error"
    assert "Invalid mode" in data["message"]

    print("✅ Write invalid mode test passed")


def test_tool_schemas():
    """Test tool schemas are valid"""
    assert READ_FILE_SCHEMA["type"] == "function"
    assert READ_FILE_SCHEMA["function"]["name"] == "read_file"

    assert WRITE_FILE_SCHEMA["type"] == "function"
    assert WRITE_FILE_SCHEMA["function"]["name"] == "write_file"

    print("✅ Tool schemas test passed")


if __name__ == "__main__":
    print("\n🧪 Running File Operations Tests...\n")

    test_write_file_overwrite()
    test_write_file_append()
    test_read_file_full()
    test_read_file_partial()
    test_read_file_nonexistent()
    test_write_file_empty_path()
    test_read_file_empty_path()
    test_write_file_invalid_mode()
    test_tool_schemas()

    print("\n🎉 All file operations tests passed!\n")