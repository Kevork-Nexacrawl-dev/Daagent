"""
Tests for partial success and checkpoint functionality.
"""

import sys
import os
import json
import tempfile
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.checkpoint import TaskCheckpoint
from agent.partial_result_handler import PartialResultHandler
from agent.errors import PartialSuccess


def test_checkpoint_creation():
    """Test checkpoint creation and basic operations"""
    print("\n🧪 Testing checkpoint creation...")

    checkpoint = TaskCheckpoint("test123")

    assert checkpoint.task_id == "test123"
    assert len(checkpoint.completed_steps) == 0
    assert len(checkpoint.failed_steps) == 0
    assert checkpoint.has_completed_steps() == False

    print("✅ Checkpoint creation working\n")


def test_checkpoint_step_tracking():
    """Test adding completed and failed steps"""
    print("\n🧪 Testing step tracking...")

    checkpoint = TaskCheckpoint("test456")

    # Add successful step
    checkpoint.add_step("Tool: web_search", {"results": ["result1", "result2"]}, success=True)
    assert checkpoint.has_completed_steps() == True
    assert len(checkpoint.completed_steps) == 1
    assert checkpoint.completed_steps[0] == "Tool: web_search"

    # Add failed step
    checkpoint.add_step("Tool: file_read", "File not found", success=False)
    assert len(checkpoint.failed_steps) == 1
    assert checkpoint.failed_steps[0]["step"] == "Tool: file_read"
    assert "File not found" in checkpoint.failed_steps[0]["error"]

    print("✅ Step tracking working\n")


def test_checkpoint_summary():
    """Test checkpoint summary generation"""
    print("\n🧪 Testing checkpoint summary...")

    checkpoint = TaskCheckpoint("test789")

    checkpoint.add_step("Tool: web_search", {"results": ["news1"]}, success=True)
    checkpoint.add_step("Tool: file_read", "Permission denied", success=False)

    summary = checkpoint.get_summary()

    assert summary["task_id"] == "test789"
    assert len(summary["completed_steps"]) == 1
    assert len(summary["failed_steps"]) == 1
    assert summary["total_steps"] == 2
    assert summary["success_rate"] == 0.5

    print("✅ Checkpoint summary working\n")


def test_checkpoint_save_load():
    """Test checkpoint file operations"""
    print("\n🧪 Testing checkpoint save/load...")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        checkpoint_dir = os.path.join(temp_dir, "checkpoints")

        # Create and save checkpoint
        checkpoint = TaskCheckpoint("test_save")
        checkpoint.add_step("Tool: test", {"data": "saved"}, success=True)

        checkpoint.save_to_file(checkpoint_dir)

        # Load checkpoint
        loaded = TaskCheckpoint.load_from_file("test_save", checkpoint_dir)

        assert loaded is not None
        assert loaded.task_id == "test_save"
        assert loaded.has_completed_steps() == True
        assert loaded.completed_steps[0] == "Tool: test"

    print("✅ Checkpoint save/load working\n")


def test_partial_result_handler():
    """Test partial result formatting"""
    print("\n🧪 Testing partial result handler...")

    checkpoint = TaskCheckpoint("partial_test")
    checkpoint.add_step("Tool: web_search", {"results": ["AI news found"]}, success=True)
    checkpoint.add_step("Tool: file_read", "File not found error", success=False)

    response = PartialResultHandler.format_response(
        checkpoint,
        "Tool 'file_read' failed: File not found"
    )

    # Check response contains expected sections
    assert "Task Partially Completed" in response
    assert "50% success" in response
    assert "What Worked" in response
    assert "What Failed" in response
    assert "Why It Stopped" in response
    assert "Suggested Next Steps" in response

    print("✅ Partial result handler working\n")


def test_result_preview_formatting():
    """Test result preview formatting"""
    print("\n🧪 Testing result preview formatting...")

    # Test dict with path
    preview = PartialResultHandler._format_result_preview({"path": "/test/file.txt"})
    assert "Saved to:" in preview

    # Test dict with data (long enough to truncate)
    long_data = "This is a very long piece of data that should definitely be truncated because it exceeds the maximum length limit for preview display"
    preview = PartialResultHandler._format_result_preview({"data": long_data})
    assert "Data:" in preview and "..." in preview  # Should truncate

    # Test string
    preview = PartialResultHandler._format_result_preview("short result")
    assert preview == "→ short result"

    print("✅ Result preview formatting working\n")


def test_next_steps_generation():
    """Test next steps generation based on error types"""
    print("\n🧪 Testing next steps generation...")

    # File error
    steps = PartialResultHandler._generate_next_steps({"completed_steps": ["step1"], "task_id": "test123"}, "File not found")
    assert any("file path" in step.lower() for step in steps)

    # Network error
    steps = PartialResultHandler._generate_next_steps({"completed_steps": ["step1"], "task_id": "test123"}, "Connection timeout")
    assert any("retry" in step.lower() for step in steps)

    # Permission error
    steps = PartialResultHandler._generate_next_steps({"completed_steps": ["step1"], "task_id": "test123"}, "Permission denied")
    assert any("permission" in step.lower() for step in steps)

    print("✅ Next steps generation working\n")


if __name__ == "__main__":
    test_checkpoint_creation()
    test_checkpoint_step_tracking()
    test_checkpoint_summary()
    test_checkpoint_save_load()
    test_partial_result_handler()
    test_result_preview_formatting()
    test_next_steps_generation()

    print("🎉 All partial success tests passed!")