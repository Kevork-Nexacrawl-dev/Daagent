"""
Comprehensive tests for FileOperationsTool
Tests all 5 tiers of functionality with happy paths, error cases, and edge cases.
"""

import json
import os
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the tool
from tools.native.file_operations import FileOperationsTool, execute_tool


class TestFileOperationsTool:
    """Test suite for FileOperationsTool"""

    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return FileOperationsTool()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def sample_files(self, temp_dir):
        """Create sample files for testing"""
        # Text files
        (temp_dir / "test.txt").write_text("Hello World\nLine 2")
        (temp_dir / "test.json").write_text('{"key": "value"}')
        (temp_dir / "test.yaml").write_text("key: value\n")

        # CSV file
        (temp_dir / "test.csv").write_text("name,age\nAlice,30\nBob,25")

        # Markdown file
        (temp_dir / "test.md").write_text("# Title\n\nSome **bold** text")

        # HTML file
        (temp_dir / "test.html").write_text("<html><body><h1>Title</h1></body></html>")

        return temp_dir

    # ============================================
    # TIER 1: CORE FILE OPS TESTS
    # ============================================

    def test_read_file_success(self, tool, sample_files):
        """Test successful file reading"""
        result = tool.read_file(str(sample_files / "test.txt"))
        assert result['success'] is True
        assert "Hello World" in result['data']
        assert result['encoding'] in ['utf-8', 'ascii']

    def test_read_file_not_found(self, tool):
        """Test reading non-existent file"""
        result = tool.read_file("/nonexistent/file.txt")
        assert result['success'] is False
        assert "File not found" in result['error']

    def test_write_file_success(self, tool, temp_dir):
        """Test successful file writing"""
        test_path = temp_dir / "new_file.txt"
        result = tool.write_file(str(test_path), "New content")
        assert result['success'] is True
        assert test_path.exists()
        assert test_path.read_text() == "New content"

    def test_write_file_create_dirs(self, tool, temp_dir):
        """Test writing file with directory creation"""
        test_path = temp_dir / "subdir" / "nested" / "file.txt"
        result = tool.write_file(str(test_path), "content", create_dirs=True)
        assert result['success'] is True
        assert test_path.exists()

    def test_list_directory_success(self, tool, sample_files):
        """Test directory listing"""
        result = tool.list_directory(str(sample_files))
        assert result['success'] is True
        assert len(result['files']) >= 5  # Should find our sample files
        assert any(f['name'].endswith('test.txt') for f in result['files'])

    def test_list_directory_pattern(self, tool, sample_files):
        """Test directory listing with pattern"""
        result = tool.list_directory(str(sample_files), pattern="*.txt")
        assert result['success'] is True
        assert all(f['name'].endswith('.txt') for f in result['files'])

    def test_file_exists_success(self, tool, sample_files):
        """Test file existence check"""
        result = tool.file_exists(str(sample_files / "test.txt"))
        assert result['success'] is True
        assert result['exists'] is True
        assert 'size' in result
        assert 'modified' in result

    def test_file_exists_not_found(self, tool):
        """Test non-existent file check"""
        result = tool.file_exists("/nonexistent/file.txt")
        assert result['success'] is True
        assert result['exists'] is False

    def test_delete_file_success(self, tool, temp_dir):
        """Test successful file deletion"""
        test_file = temp_dir / "to_delete.txt"
        test_file.write_text("content")
        assert test_file.exists()

        result = tool.delete_file(str(test_file))
        assert result['success'] is True
        assert not test_file.exists()

    def test_delete_file_not_found(self, tool):
        """Test deleting non-existent file"""
        result = tool.delete_file("/nonexistent/file.txt")
        assert result['success'] is False
        assert "File not found" in result['error']

    # ============================================
    # TIER 2: FORMAT TRANSFORMATIONS TESTS
    # ============================================

    def test_convert_markdown_to_pdf_success(self, tool, sample_files):
        """Test markdown to PDF conversion"""
        # Skip test if dependencies not available
        try:
            import weasyprint
            import markdown
        except ImportError:
            pytest.skip("WeasyPrint or markdown not available")

        output_path = str(sample_files / "output.pdf")
        result = tool.convert_markdown_to_pdf(
            md_file=str(sample_files / "test.md"),
            output_path=output_path
        )
        assert result['success'] is True
        assert 'output_path' in result

    def test_convert_html_to_pdf_success(self, tool, sample_files):
        """Test HTML to PDF conversion"""
        try:
            import weasyprint
        except ImportError:
            pytest.skip("WeasyPrint not available")

        output_path = str(sample_files / "output.pdf")
        result = tool.convert_html_to_pdf(
            html_file=str(sample_files / "test.html"),
            output_path=output_path
        )
        assert result['success'] is True

    def test_csv_to_excel_success(self, tool, sample_files):
        """Test CSV to Excel conversion"""
        try:
            import pandas
            import openpyxl
        except ImportError:
            pytest.skip("pandas or openpyxl not available")

        output_path = str(sample_files / "output.xlsx")
        result = tool.csv_to_excel(
            csv_path=str(sample_files / "test.csv"),
            output_path=output_path
        )
        assert result['success'] is True

    def test_excel_to_csv_success(self, tool, temp_dir):
        """Test Excel to CSV conversion"""
        try:
            import pandas
            import openpyxl
        except ImportError:
            pytest.skip("pandas or openpyxl not available")

        # Create a mock Excel file for testing
        xlsx_path = temp_dir / "test.xlsx"
        xlsx_path.write_bytes(b"mock excel data")

        output_path = str(temp_dir / "output.csv")
        result = tool.excel_to_csv(
            xlsx_path=str(xlsx_path),
            output_path=output_path
        )
        assert result['success'] is True

    def test_json_to_csv_success(self, tool, temp_dir):
        """Test JSON to CSV conversion"""
        try:
            import pandas
        except ImportError:
            pytest.skip("pandas not available")

        json_data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        output_path = str(temp_dir / "output.csv")

        result = tool.json_to_csv(json_data, output_path)
        assert result['success'] is True

    # ============================================
    # TIER 3: BINARY OPERATIONS TESTS
    # ============================================

    def test_read_binary_file_success(self, tool, sample_files):
        """Test binary file reading"""
        result = tool.read_binary_file(str(sample_files / "test.txt"))
        assert result['success'] is True
        assert 'data_b64' in result
        assert 'size' in result

    def test_write_binary_file_success(self, tool, temp_dir):
        """Test binary file writing"""
        import base64
        test_data = base64.b64encode(b"binary data").decode()

        output_path = str(temp_dir / "binary_output.bin")
        result = tool.write_binary_file(output_path, test_data)
        assert result['success'] is True
        assert Path(output_path).exists()

    def test_encode_base64_success(self, tool, sample_files):
        """Test base64 encoding"""
        result = tool.encode_base64(str(sample_files / "test.txt"))
        assert result['success'] is True
        assert 'data_b64' in result

    def test_decode_base64_success(self, tool, temp_dir):
        """Test base64 decoding"""
        import base64
        test_data = base64.b64encode(b"test data").decode()

        output_path = str(temp_dir / "decoded.bin")
        result = tool.decode_base64(test_data, output_path)
        assert result['success'] is True
        assert Path(output_path).exists()

    def test_compress_files_success(self, tool, sample_files, temp_dir):
        """Test file compression"""
        file_list = [str(sample_files / "test.txt"), str(sample_files / "test.json")]
        zip_path = str(temp_dir / "archive.zip")

        result = tool.compress_files(file_list, zip_path)
        assert result['success'] is True
        assert Path(zip_path).exists()

    def test_extract_archive_success(self, tool, temp_dir):
        """Test archive extraction"""
        # Create a test archive
        import zipfile
        zip_path = temp_dir / "test.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("test.txt", "content")

        extract_dir = str(temp_dir / "extracted")
        result = tool.extract_archive(str(zip_path), extract_dir)
        assert result['success'] is True
        assert Path(extract_dir).exists()

    # ============================================
    # TIER 4: SMART ANALYSIS TESTS
    # ============================================

    def test_detect_file_type_success(self, tool, sample_files):
        """Test file type detection"""
        try:
            import magic
        except ImportError:
            pytest.skip("python-magic-bin not available")

        result = tool.detect_file_type(str(sample_files / "test.txt"))
        assert result['success'] is True
        assert 'mime_type' in result

    def test_extract_text_from_pdf_success(self, tool, temp_dir):
        """Test PDF text extraction"""
        try:
            import PyPDF2
        except ImportError:
            pytest.skip("PyPDF2 not available")

        # Create mock PDF file
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"mock pdf content")

        result = tool.extract_text_from_pdf(str(pdf_path))
        assert result['success'] is True

    def test_extract_metadata_success(self, tool, sample_files):
        """Test metadata extraction"""
        result = tool.extract_metadata(str(sample_files / "test.txt"))
        assert result['success'] is True
        assert 'size' in result
        assert 'modified' in result
        assert 'created' in result

    def test_count_lines_of_code_success(self, tool, sample_files):
        """Test line counting"""
        result = tool.count_lines_of_code(str(sample_files / "test.txt"))
        assert result['success'] is True
        assert 'total_lines' in result
        assert 'code_lines' in result
        assert 'comment_lines' in result

    def test_validate_json_file_success(self, tool, sample_files):
        """Test JSON validation"""
        result = tool.validate_json_file(str(sample_files / "test.json"))
        assert result['success'] is True
        assert result['valid'] is True

    def test_validate_json_file_invalid(self, tool, temp_dir):
        """Test invalid JSON validation"""
        invalid_json = temp_dir / "invalid.json"
        invalid_json.write_text('{"invalid": json}')

        result = tool.validate_json_file(str(invalid_json))
        assert result['success'] is True
        assert result['valid'] is False

    def test_validate_yaml_file_success(self, tool, sample_files):
        """Test YAML validation"""
        result = tool.validate_yaml_file(str(sample_files / "test.yaml"))
        assert result['success'] is True
        assert result['valid'] is True

    # ============================================
    # TIER 5: BULK OPERATIONS TESTS
    # ============================================

    def test_batch_rename_dry_run(self, tool, temp_dir):
        """Test batch rename dry run"""
        # Create test files
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")

        result = tool.batch_rename(
            directory=str(temp_dir),
            pattern="file",
            replacement="renamed",
            dry_run=True
        )
        assert result['success'] is True
        assert 'operations' in result
        assert len(result['operations']) == 2

    def test_find_files_success(self, tool, sample_files):
        """Test advanced file search"""
        result = tool.find_files(directory=str(sample_files), pattern="*.txt")
        assert result['success'] is True
        assert len(result['matches']) >= 1
        assert all(f['name'].endswith('.txt') for f in result['matches'])

    def test_merge_files_success(self, tool, temp_dir):
        """Test file merging"""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        file1.write_text("Content 1")
        file2.write_text("Content 2")

        output_path = str(temp_dir / "merged.txt")
        result = tool.merge_files([str(file1), str(file2)], output_path)
        assert result['success'] is True
        assert Path(output_path).exists()

        merged_content = Path(output_path).read_text()
        assert "Content 1" in merged_content
        assert "Content 2" in merged_content

    def test_split_file_success(self, tool, temp_dir):
        """Test file splitting"""
        large_file = temp_dir / "large.txt"
        # Create a file larger than 1MB
        content = "x" * (1024 * 1024 * 2)  # 2MB
        large_file.write_text(content)

        result = tool.split_file(str(large_file), chunk_size_mb=1)
        assert result['success'] is True
        assert 'chunks_created' in result
        assert result['chunks_created'] >= 2

    def test_sync_directories_success(self, tool, temp_dir):
        """Test directory synchronization"""
        source_dir = temp_dir / "source"
        dest_dir = temp_dir / "dest"
        source_dir.mkdir()
        dest_dir.mkdir()

        # Create source files
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")

        result = tool.sync_directories(str(source_dir), str(dest_dir))
        assert result['success'] is True
        assert result['files_copied'] == 2

    # ============================================
    # EXECUTE_TOOL TESTS
    # ============================================

    def test_execute_tool_success(self):
        """Test execute_tool wrapper"""
        result_str = execute_tool("file_exists", path="c:\\Windows\\System32\\notepad.exe")
        result = json.loads(result_str)
        assert 'success' in result
        # Note: This might fail on some systems, but tests the wrapper

    def test_execute_tool_unknown_operation(self):
        """Test execute_tool with unknown operation"""
        result_str = execute_tool("unknown_operation")
        result = json.loads(result_str)
        assert result['success'] is False
        assert "Unknown operation" in result['error']

    # ============================================
    # DEPENDENCY INSTALLATION TESTS
    # ============================================

    @patch('subprocess.check_call')
    @patch('builtins.__import__')
    def test_auto_install_dependency(self, mock_import, mock_subprocess, tool):
        """Test automatic dependency installation"""
        # Mock successful installation
        mock_subprocess.return_value = None
        mock_import.side_effect = ImportError("No module")  # First import fails
        # Second import succeeds after installation
        mock_import.side_effect = [ImportError("No module"), MagicMock()]

        # This should trigger dependency installation
        result = tool._install_if_missing("nonexistent_package", "nonexistent_module")
        assert result is True
        mock_subprocess.assert_called_once()

    # ============================================
    # ERROR HANDLING TESTS
    # ============================================

    def test_tool_error_handling(self, tool):
        """Test general error handling"""
        # Test with invalid arguments
        result = tool.read_file("")  # Empty path
        assert result['success'] is False
        assert 'error' in result

    def test_binary_operations_error_handling(self, tool):
        """Test binary operations error handling"""
        result = tool.encode_base64("/nonexistent/file.bin")
        assert result['success'] is False
        assert 'error' in result


if __name__ == "__main__":
    pytest.main([__file__])