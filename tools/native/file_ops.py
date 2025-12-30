"""
File operations tool for reading and writing files on the local system.
Provides safe file access capabilities for the agent.
"""

import json
import logging
import os
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def read_file(file_path: str, start_line: int = 1, end_line: int = -1) -> str:
    """
    Read content from a file.

    Args:
        file_path: Path to the file to read
        start_line: Starting line number (1-based, default: 1)
        end_line: Ending line number (1-based, -1 for end of file, default: -1)

    Returns:
        JSON string containing file content with format:
        {
            "status": "success" | "error",
            "file_path": file path,
            "content": file content,
            "lines_read": number of lines,
            "total_lines": total lines in file
        }
    """
    try:
        # Validate inputs
        if not file_path or not file_path.strip():
            return json.dumps({
                "status": "error",
                "message": "File path cannot be empty",
                "file_path": file_path,
                "content": "",
                "lines_read": 0,
                "total_lines": 0
            })

        path = Path(file_path).resolve()

        # Security check - prevent access outside workspace
        workspace_root = Path.cwd()
        try:
            path.relative_to(workspace_root)
        except ValueError:
            return json.dumps({
                "status": "error",
                "message": "Access denied: File outside workspace",
                "file_path": file_path,
                "content": "",
                "lines_read": 0,
                "total_lines": 0
            })

        if not path.exists():
            return json.dumps({
                "status": "error",
                "message": "File does not exist",
                "file_path": file_path,
                "content": "",
                "lines_read": 0,
                "total_lines": 0
            })

        if not path.is_file():
            return json.dumps({
                "status": "error",
                "message": "Path is not a file",
                "file_path": file_path,
                "content": "",
                "lines_read": 0,
                "total_lines": 0
            })

        logger.info(f"Reading file: {file_path} (lines {start_line}-{end_line})")

        # Read file content
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Adjust line numbers
        start_line = max(1, min(start_line, total_lines))
        if end_line == -1:
            end_line = total_lines
        end_line = max(start_line, min(end_line, total_lines))

        # Extract requested lines
        selected_lines = lines[start_line-1:end_line]
        content = ''.join(selected_lines)
        lines_read = len(selected_lines)

        logger.info(f"File read successful: {lines_read} lines from {total_lines} total")

        return json.dumps({
            "status": "success",
            "file_path": str(path),
            "content": content,
            "lines_read": lines_read,
            "total_lines": total_lines
        }, indent=2)

    except Exception as e:
        error_msg = f"Failed to read file: {str(e)}"
        logger.error(f"{error_msg} (path: '{file_path}')")

        return json.dumps({
            "status": "error",
            "message": error_msg,
            "file_path": file_path,
            "content": "",
            "lines_read": 0,
            "total_lines": 0
        })


def write_file(file_path: str, content: str, mode: str = "overwrite") -> str:
    """
    Write content to a file.

    Args:
        file_path: Path to the file to write
        content: Content to write
        mode: Write mode - "overwrite" or "append" (default: "overwrite")

    Returns:
        JSON string containing write result with format:
        {
            "status": "success" | "error",
            "file_path": file path,
            "mode": write mode used,
            "bytes_written": number of bytes written,
            "lines_written": number of lines written
        }
    """
    try:
        # Validate inputs
        if not file_path or not file_path.strip():
            return json.dumps({
                "status": "error",
                "message": "File path cannot be empty",
                "file_path": file_path,
                "mode": mode,
                "bytes_written": 0,
                "lines_written": 0
            })

        if mode not in ["overwrite", "append"]:
            return json.dumps({
                "status": "error",
                "message": "Invalid mode. Use 'overwrite' or 'append'",
                "file_path": file_path,
                "mode": mode,
                "bytes_written": 0,
                "lines_written": 0
            })

        path = Path(file_path).resolve()

        # Security check - prevent access outside workspace
        workspace_root = Path.cwd()
        try:
            path.relative_to(workspace_root)
        except ValueError:
            return json.dumps({
                "status": "error",
                "message": "Access denied: File outside workspace",
                "file_path": file_path,
                "mode": mode,
                "bytes_written": 0,
                "lines_written": 0
            })

        logger.info(f"Writing file: {file_path} (mode: {mode})")

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        write_mode = 'w' if mode == "overwrite" else 'a'
        with open(path, write_mode, encoding='utf-8') as f:
            f.write(content)

        # Calculate stats
        lines_written = len(content.splitlines())
        bytes_written = len(content.encode('utf-8'))

        logger.info(f"File write successful: {bytes_written} bytes, {lines_written} lines")

        return json.dumps({
            "status": "success",
            "file_path": str(path),
            "mode": mode,
            "bytes_written": bytes_written,
            "lines_written": lines_written
        }, indent=2)

    except Exception as e:
        error_msg = f"Failed to write file: {str(e)}"
        logger.error(f"{error_msg} (path: '{file_path}', mode: '{mode}')")

        return json.dumps({
            "status": "error",
            "message": error_msg,
            "file_path": file_path,
            "mode": mode,
            "bytes_written": 0,
            "lines_written": 0
        })


# Tool schemas for OpenAI function calling

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read content from a file on the local system. Use this to examine existing files, read code, documentation, or any text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read (relative to workspace root)"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Starting line number (1-based). Default is 1.",
                    "default": 1,
                    "minimum": 1
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ending line number (1-based). Use -1 for end of file. Default is -1.",
                    "default": -1
                }
            },
            "required": ["file_path"]
        }
    }
}

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file on the local system. Use this to create new files, modify existing files, or append content.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write (relative to workspace root)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                },
                "mode": {
                    "type": "string",
                    "description": "Write mode: 'overwrite' (replace file) or 'append' (add to end). Default is 'overwrite'.",
                    "enum": ["overwrite", "append"],
                    "default": "overwrite"
                }
            },
            "required": ["file_path", "content"]
        }
    }
}

# For auto-discovery compatibility
TOOL_SCHEMAS = [READ_FILE_SCHEMA, WRITE_FILE_SCHEMA]

def execute_tool(operation: str, **kwargs) -> str:
    """
    Execute file operation tool.
    
    Args:
        operation: Either "read_file" or "write_file"
        **kwargs: Arguments for the operation
        
    Returns:
        JSON string result
    """
    if operation == "read_file":
        return read_file(**kwargs)
    elif operation == "write_file":
        return write_file(**kwargs)
    else:
        return json.dumps({
            "status": "error",
            "message": f"Unknown file operation: {operation}"
        })