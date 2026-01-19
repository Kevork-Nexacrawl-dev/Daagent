"""
File Operations Toolset - Daagent Native Tools
Comprehensive file operations with auto-dependency installation and smart defaults.
Inspired by Perplexity's PDF generation agent pattern.
"""

import json
import os
import sys
import subprocess
import base64
import tempfile
import shutil
import glob
import zipfile
import tarfile
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class FileOperationsTool:
    """
    Comprehensive file operations tool with auto-dependency installation.

    Provides 5 tiers of file capabilities:
    - Tier 1: Core File Ops (basic I/O)
    - Tier 2: Format Transformations (MD→PDF, CSV→Excel, etc.)
    - Tier 3: Binary Operations (read/write bytes, base64 encoding)
    - Tier 4: Smart Analysis (file type detection, PDF text extraction)
    - Tier 5: Bulk Operations (batch rename, find files, merge)
    """

    def __init__(self):
        """Initialize tool with auto-dependency installation."""
        self.installed_packages = set()
        self._ensure_base_deps()

    def _ensure_base_deps(self) -> None:
        """Install base dependencies required for core functionality."""
        base_deps = [
            ('chardet', 'chardet'),  # Encoding detection
            ('python-magic-bin', 'magic'),  # File type detection
        ]

        for package, import_name in base_deps:
            self._install_if_missing(package, import_name)

    def _install_if_missing(self, package: str, import_name: str = None) -> bool:
        """
        Install package if not available. Returns True if available after check.

        Args:
            package: Package name to install
            import_name: Name to import (defaults to package name)

        Returns:
            True if package is available after installation attempt
        """
        if import_name is None:
            import_name = package

        if import_name in self.installed_packages:
            return True

        try:
            __import__(import_name)
            self.installed_packages.add(import_name)
            return True
        except ImportError:
            pass

        try:
            logger.info(f"Installing missing dependency: {package}")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-q", package
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            __import__(import_name)
            self.installed_packages.add(import_name)
            logger.info(f"✓ Successfully installed {package}")
            return True

        except (subprocess.CalledProcessError, ImportError) as e:
            logger.error(f"⚠️ Failed to install {package}: {e}")
            return False

    # ============================================
    # TIER 1: CORE FILE OPS
    # ============================================

    def read_file(self, path: str, encoding: str = 'auto') -> Dict[str, Any]:
        """
        Read text file with auto-encoding detection.

        Args:
            path: File path to read
            encoding: Text encoding ('auto' for detection, or specific encoding)

        Returns:
            Dict with success status and file content
        """
        try:
            file_path = Path(path)
            if not file_path.exists():
                return {'success': False, 'error': f'File not found: {path}'}

            if encoding == 'auto':
                if not self._install_if_missing('chardet'):
                    return {'success': False, 'error': 'Failed to install chardet for encoding detection'}

                import chardet
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                    detected = chardet.detect(raw_data)
                    encoding = detected.get('encoding', 'utf-8')

            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()

            return {
                'success': True,
                'data': content,
                'path': str(file_path.absolute()),
                'size': len(content),
                'encoding': encoding,
                'message': f'✓ Read {len(content)} characters from {file_path.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def write_file(self, path: str, content: str, encoding: str = 'utf-8', create_dirs: bool = True) -> Dict[str, Any]:
        """
        Write text content to file.

        Args:
            path: File path to write
            content: Text content to write
            encoding: Text encoding
            create_dirs: Create parent directories if they don't exist

        Returns:
            Dict with success status and file info
        """
        try:
            file_path = Path(path)

            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)

            return {
                'success': True,
                'path': str(file_path.absolute()),
                'size': len(content),
                'encoding': encoding,
                'message': f'✓ Wrote {len(content)} characters to {file_path.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def list_directory(self, path: str, pattern: str = '*', recursive: bool = False) -> Dict[str, Any]:
        """
        List directory contents with pattern matching.

        Args:
            path: Directory path to list
            pattern: Glob pattern to match files
            recursive: Include subdirectories recursively

        Returns:
            Dict with directory listing
        """
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return {'success': False, 'error': f'Directory not found: {path}'}

            if not dir_path.is_dir():
                return {'success': False, 'error': f'Path is not a directory: {path}'}

            if recursive:
                files = list(dir_path.rglob(pattern))
            else:
                files = list(dir_path.glob(pattern))

            # Separate files and directories
            file_list = []
            dir_list = []

            for item in files:
                if item.is_file():
                    file_list.append({
                        'name': item.name,
                        'path': str(item.absolute()),
                        'size': item.stat().st_size,
                        'modified': item.stat().st_mtime
                    })
                elif item.is_dir():
                    dir_list.append({
                        'name': item.name,
                        'path': str(item.absolute()),
                        'modified': item.stat().st_mtime
                    })

            return {
                'success': True,
                'path': str(dir_path.absolute()),
                'files': file_list,
                'directories': dir_list,
                'total_files': len(file_list),
                'total_dirs': len(dir_list),
                'message': f'✓ Listed {len(file_list)} files, {len(dir_list)} directories'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def file_exists(self, path: str) -> Dict[str, Any]:
        """
        Check if file exists and return metadata.

        Args:
            path: File path to check

        Returns:
            Dict with existence status and file info
        """
        try:
            file_path = Path(path)
            exists = file_path.exists()

            if exists:
                stat = file_path.stat()
                return {
                    'success': True,
                    'exists': True,
                    'path': str(file_path.absolute()),
                    'size': stat.st_size,
                    'is_file': file_path.is_file(),
                    'is_dir': file_path.is_dir(),
                    'modified': stat.st_mtime,
                    'message': f'✓ File exists: {file_path.name}'
                }
            else:
                return {
                    'success': True,
                    'exists': False,
                    'path': path,
                    'message': f'⚠️ File not found: {path}'
                }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def delete_file(self, path: str) -> Dict[str, Any]:
        """
        Safely delete a file.

        Args:
            path: File path to delete

        Returns:
            Dict with deletion status
        """
        try:
            file_path = Path(path)
            if not file_path.exists():
                return {'success': False, 'error': f'File not found: {path}'}

            if file_path.is_dir():
                return {'success': False, 'error': 'Cannot delete directory with delete_file. Use delete_directory.'}

            # Store info before deletion
            size = file_path.stat().st_size
            file_path.unlink()

            return {
                'success': True,
                'path': str(file_path.absolute()),
                'size_deleted': size,
                'message': f'✓ Deleted file: {file_path.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    # ============================================
    # TIER 2: FORMAT TRANSFORMATIONS
    # ============================================

    def convert_markdown_to_pdf(self, md_content: str = None, md_file: str = None,
                               output_path: str = None, style: str = 'professional') -> Dict[str, Any]:
        """
        Convert Markdown to PDF with professional styling.

        Args:
            md_content: Markdown content as string
            md_file: Path to markdown file
            output_path: Output PDF path (auto-generated if None)
            style: Style preset ('professional', 'minimal', 'resume')

        Returns:
            Dict with conversion result
        """
        try:
            if not self._install_if_missing('weasyprint'):
                return {'success': False, 'error': 'Failed to install weasyprint'}
            if not self._install_if_missing('markdown', 'markdown'):
                return {'success': False, 'error': 'Failed to install markdown'}

            import weasyprint
            import markdown

            # Get markdown content
            if md_file and not md_content:
                read_result = self.read_file(md_file)
                if not read_result['success']:
                    return read_result
                md_content = read_result['data']
            elif not md_content:
                return {'success': False, 'error': 'Either md_content or md_file must be provided'}

            # Auto-generate output path
            if not output_path:
                if md_file:
                    output_path = str(Path(md_file).with_suffix('.pdf'))
                else:
                    output_path = 'output.pdf'

            # Convert markdown to HTML
            html_content = markdown.markdown(md_content, extensions=['extra', 'codehilite'])

            # Apply styling based on preset
            css_styles = self._get_pdf_style_css(style)
            full_html = self._create_full_html_document(html_content, css_styles)

            # Generate PDF
            pdf_bytes = BytesIO()
            weasyprint.HTML(string=full_html).write_pdf(pdf_bytes)
            pdf_bytes.seek(0)
            pdf_data = pdf_bytes.read()

            # Write to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(pdf_data)

            return {
                'success': True,
                'output_path': str(output_file.absolute()),
                'size_kb': round(len(pdf_data) / 1024, 2),
                'style': style,
                'message': f'✓ Converted markdown to PDF: {output_file.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def _get_pdf_style_css(self, style: str) -> str:
        """Get CSS styles for PDF generation."""
        base_css = """
        @page { size: A4; margin: 2cm; }
        body { font-family: 'Helvetica', sans-serif; line-height: 1.6; color: #333; }
        h1, h2, h3, h4, h5, h6 { color: #2c3e50; margin-top: 1.5em; margin-bottom: 0.5em; }
        h1 { font-size: 2em; border-bottom: 2px solid #3498db; padding-bottom: 0.3em; }
        h2 { font-size: 1.5em; border-bottom: 1px solid #bdc3c7; padding-bottom: 0.2em; }
        p { margin: 0.8em 0; }
        code { background: #f8f8f8; padding: 0.2em 0.4em; border-radius: 3px; font-family: 'Monaco', monospace; }
        pre { background: #f8f8f8; padding: 1em; border-radius: 5px; overflow-x: auto; }
        blockquote { border-left: 4px solid #3498db; padding-left: 1em; margin: 1em 0; font-style: italic; }
        table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        th, td { border: 1px solid #bdc3c7; padding: 0.5em; text-align: left; }
        th { background: #ecf0f1; }
        ul, ol { margin: 1em 0; padding-left: 2em; }
        li { margin: 0.3em 0; }
        """

        if style == 'minimal':
            return base_css + """
            body { font-size: 11pt; color: #000; }
            @page { margin: 1.5cm; }
            """
        elif style == 'resume':
            return base_css + """
            body { font-size: 10pt; max-width: none; }
            @page { margin: 1cm; }
            h1 { color: #000; font-size: 1.8em; }
            .contact { font-size: 9pt; color: #666; margin-bottom: 1em; }
            """
        else:  # professional
            return base_css + """
            body { font-size: 11pt; }
            .header { background: #2c3e50; color: white; padding: 1em; margin: -2cm -2cm 1em -2cm; }
            .header h1 { color: white; border: none; margin: 0; }
            """

    def _create_full_html_document(self, body_content: str, css_styles: str) -> str:
        """Create complete HTML document with embedded CSS."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
    <style>
    {css_styles}
    </style>
</head>
<body>
    {body_content}
</body>
</html>"""

    def convert_html_to_pdf(self, html_content: str = None, html_file: str = None,
                           output_path: str = None, css_override: str = None) -> Dict[str, Any]:
        """
        Convert HTML to PDF.

        Args:
            html_content: HTML content as string
            html_file: Path to HTML file
            output_path: Output PDF path
            css_override: Additional CSS to inject

        Returns:
            Dict with conversion result
        """
        try:
            if not self._install_if_missing('weasyprint'):
                return {'success': False, 'error': 'Failed to install weasyprint'}

            import weasyprint

            # Get HTML content
            if html_file and not html_content:
                read_result = self.read_file(html_file)
                if not read_result['success']:
                    return read_result
                html_content = read_result['data']
            elif not html_content:
                return {'success': False, 'error': 'Either html_content or html_file must be provided'}

            # Auto-generate output path
            if not output_path:
                if html_file:
                    output_path = str(Path(html_file).with_suffix('.pdf'))
                else:
                    output_path = 'output.pdf'

            # Apply CSS override if provided
            if css_override:
                # Inject CSS into head if present, otherwise add style block
                if '<head>' in html_content:
                    html_content = html_content.replace('<head>', f'<head><style>{css_override}</style>')
                else:
                    html_content = f'<style>{css_override}</style>{html_content}'

            # Generate PDF
            pdf_bytes = BytesIO()
            weasyprint.HTML(string=html_content).write_pdf(pdf_bytes)
            pdf_bytes.seek(0)
            pdf_data = pdf_bytes.read()

            # Write to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(pdf_data)

            return {
                'success': True,
                'output_path': str(output_file.absolute()),
                'size_kb': round(len(pdf_data) / 1024, 2),
                'message': f'✓ Converted HTML to PDF: {output_file.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def csv_to_excel(self, csv_path: str, output_path: str = None, sheet_name: str = 'Sheet1') -> Dict[str, Any]:
        """
        Convert CSV to Excel spreadsheet.

        Args:
            csv_path: Path to CSV file
            output_path: Output Excel path (auto-generated if None)
            sheet_name: Excel sheet name

        Returns:
            Dict with conversion result
        """
        try:
            if not self._install_if_missing('pandas'):
                return {'success': False, 'error': 'Failed to install pandas'}
            if not self._install_if_missing('openpyxl'):
                return {'success': False, 'error': 'Failed to install openpyxl'}

            import pandas as pd

            # Auto-generate output path
            if not output_path:
                output_path = str(Path(csv_path).with_suffix('.xlsx'))

            # Read CSV and write Excel
            df = pd.read_csv(csv_path)
            df.to_excel(output_path, sheet_name=sheet_name, index=False)

            output_file = Path(output_path)
            return {
                'success': True,
                'output_path': str(output_file.absolute()),
                'rows': len(df),
                'columns': len(df.columns),
                'sheet_name': sheet_name,
                'message': f'✓ Converted CSV to Excel: {output_file.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def excel_to_csv(self, xlsx_path: str, output_path: str = None, sheet_name: Union[str, int] = 0) -> Dict[str, Any]:
        """
        Convert Excel to CSV.

        Args:
            xlsx_path: Path to Excel file
            output_path: Output CSV path (auto-generated if None)
            sheet_name: Sheet name or index to convert

        Returns:
            Dict with conversion result
        """
        try:
            if not self._install_if_missing('pandas'):
                return {'success': False, 'error': 'Failed to install pandas'}
            if not self._install_if_missing('openpyxl'):
                return {'success': False, 'error': 'Failed to install openpyxl'}

            import pandas as pd

            # Auto-generate output path
            if not output_path:
                output_path = str(Path(xlsx_path).with_suffix('.csv'))

            # Read Excel and write CSV
            df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
            df.to_csv(output_path, index=False)

            output_file = Path(output_path)
            return {
                'success': True,
                'output_path': str(output_file.absolute()),
                'rows': len(df),
                'columns': len(df.columns),
                'message': f'✓ Converted Excel to CSV: {output_file.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def json_to_csv(self, json_data: Union[str, Dict, List], output_path: str) -> Dict[str, Any]:
        """
        Convert JSON data to CSV.

        Args:
            json_data: JSON data (string, dict, or list)
            output_path: Output CSV path

        Returns:
            Dict with conversion result
        """
        try:
            if not self._install_if_missing('pandas'):
                return {'success': False, 'error': 'Failed to install pandas'}

            import pandas as pd
            import json as json_module

            # Parse JSON if it's a string
            if isinstance(json_data, str):
                data = json_module.loads(json_data)
            else:
                data = json_data

            # Convert to DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # Assume it's a dict of arrays or single record
                if all(isinstance(v, list) for v in data.values()):
                    # Dict of lists
                    df = pd.DataFrame(data)
                else:
                    # Single record
                    df = pd.DataFrame([data])
            else:
                return {'success': False, 'error': 'JSON data must be a dict or list'}

            # Write CSV
            df.to_csv(output_path, index=False)

            output_file = Path(output_path)
            return {
                'success': True,
                'output_path': str(output_file.absolute()),
                'rows': len(df),
                'columns': len(df.columns),
                'message': f'✓ Converted JSON to CSV: {output_file.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    # ============================================
    # TIER 3: BINARY OPERATIONS
    # ============================================

    def read_binary_file(self, path: str) -> Dict[str, Any]:
        """
        Read binary file and return bytes with metadata.

        Args:
            path: File path to read

        Returns:
            Dict with binary data and metadata
        """
        try:
            file_path = Path(path)
            if not file_path.exists():
                return {'success': False, 'error': f'File not found: {path}'}

            with open(file_path, 'rb') as f:
                data = f.read()

            return {
                'success': True,
                'data_b64': base64.b64encode(data).decode('ascii'),
                'size': len(data),
                'path': str(file_path.absolute()),
                'message': f'✓ Read {len(data)} bytes from {file_path.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def write_binary_file(self, path: str, data_b64: str, create_dirs: bool = True) -> Dict[str, Any]:
        """
        Write binary data to file.

        Args:
            path: File path to write
            data_b64: Base64 encoded binary data
            create_dirs: Create parent directories if they don't exist

        Returns:
            Dict with write result
        """
        try:
            file_path = Path(path)

            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # Decode base64 data
            data = base64.b64decode(data_b64)

            with open(file_path, 'wb') as f:
                f.write(data)

            return {
                'success': True,
                'path': str(file_path.absolute()),
                'size': len(data),
                'message': f'✓ Wrote {len(data)} bytes to {file_path.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def encode_base64(self, file_path: str) -> Dict[str, Any]:
        """
        Encode file to base64 string.

        Args:
            file_path: Path to file to encode

        Returns:
            Dict with base64 encoded data
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            with open(file_path_obj, 'rb') as f:
                data = f.read()

            encoded = base64.b64encode(data).decode('ascii')

            return {
                'success': True,
                'data_b64': encoded,
                'original_size': len(data),
                'encoded_size': len(encoded),
                'path': str(file_path_obj.absolute()),
                'message': f'✓ Encoded {len(data)} bytes to base64'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def decode_base64(self, base64_string: str, output_path: str, create_dirs: bool = True) -> Dict[str, Any]:
        """
        Decode base64 string to file.

        Args:
            base64_string: Base64 encoded data
            output_path: Output file path
            create_dirs: Create parent directories if they don't exist

        Returns:
            Dict with decode result
        """
        try:
            output_file = Path(output_path)

            if create_dirs:
                output_file.parent.mkdir(parents=True, exist_ok=True)

            # Decode base64 data
            data = base64.b64decode(base64_string)

            with open(output_file, 'wb') as f:
                f.write(data)

            return {
                'success': True,
                'path': str(output_file.absolute()),
                'size': len(data),
                'message': f'✓ Decoded base64 to {output_file.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def compress_files(self, file_list: List[str], zip_name: str) -> Dict[str, Any]:
        """
        Create ZIP archive from list of files.

        Args:
            file_list: List of file paths to compress
            zip_name: Output ZIP file name

        Returns:
            Dict with compression result
        """
        try:
            zip_path = Path(zip_name)
            zip_path.parent.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_list:
                    file_obj = Path(file_path)
                    if file_obj.exists():
                        zipf.write(file_obj, file_obj.name)

            final_size = zip_path.stat().st_size
            return {
                'success': True,
                'archive_path': str(zip_path.absolute()),
                'files_compressed': len(file_list),
                'size_kb': round(final_size / 1024, 2),
                'message': f'✓ Created ZIP archive with {len(file_list)} files'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def extract_archive(self, archive_path: str, dest_dir: str, create_dirs: bool = True) -> Dict[str, Any]:
        """
        Extract ZIP or TAR archive.

        Args:
            archive_path: Path to archive file
            dest_dir: Destination directory
            create_dirs: Create destination directory if it doesn't exist

        Returns:
            Dict with extraction result
        """
        try:
            archive_file = Path(archive_path)
            dest_path = Path(dest_dir)

            if not archive_file.exists():
                return {'success': False, 'error': f'Archive not found: {archive_path}'}

            if create_dirs:
                dest_path.mkdir(parents=True, exist_ok=True)

            extracted_files = []

            if archive_file.suffix.lower() in ['.zip']:
                with zipfile.ZipFile(archive_file, 'r') as zipf:
                    zipf.extractall(dest_path)
                    extracted_files = zipf.namelist()
            elif archive_file.suffix.lower() in ['.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2']:
                with tarfile.open(archive_file, 'r:*') as tarf:
                    tarf.extractall(dest_path)
                    extracted_files = [member.name for member in tarf.getmembers()]
            else:
                return {'success': False, 'error': f'Unsupported archive format: {archive_file.suffix}'}

            return {
                'success': True,
                'archive_path': str(archive_file.absolute()),
                'dest_dir': str(dest_path.absolute()),
                'files_extracted': len(extracted_files),
                'message': f'✓ Extracted {len(extracted_files)} files from archive'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    # ============================================
    # TIER 4: SMART ANALYSIS
    # ============================================

    def detect_file_type(self, path: str) -> Dict[str, Any]:
        """
        Detect file type using magic numbers and metadata.

        Args:
            path: File path to analyze

        Returns:
            Dict with file type information
        """
        try:
            if not self._install_if_missing('python-magic-bin', 'magic'):
                return {'success': False, 'error': 'Failed to install python-magic-bin'}

            import magic
            import chardet

            file_path = Path(path)
            if not file_path.exists():
                return {'success': False, 'error': f'File not found: {path}'}

            # Get MIME type
            mime_type = magic.from_file(str(file_path), mime=True)

            # Get file description
            file_description = magic.from_file(str(file_path))

            # Detect encoding for text files
            encoding = None
            if mime_type.startswith('text/'):
                with open(file_path, 'rb') as f:
                    raw_data = f.read(1024)  # First 1KB for detection
                    detected = chardet.detect(raw_data)
                    encoding = detected.get('encoding')

            # Get file extension
            extension = file_path.suffix.lower()

            return {
                'success': True,
                'path': str(file_path.absolute()),
                'mime_type': mime_type,
                'description': file_description,
                'extension': extension,
                'encoding': encoding,
                'size': file_path.stat().st_size,
                'message': f'✓ Detected file type: {mime_type}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text content from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict with extracted text
        """
        try:
            if not self._install_if_missing('PyPDF2'):
                return {'success': False, 'error': 'Failed to install PyPDF2'}

            import PyPDF2

            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                return {'success': False, 'error': f'PDF file not found: {pdf_path}'}

            with open(pdf_file, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)

                text_content = []
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_content.append(page.extract_text())

                full_text = '\n\n'.join(text_content)

            return {
                'success': True,
                'path': str(pdf_file.absolute()),
                'pages': len(pdf_reader.pages),
                'text_length': len(full_text),
                'text': full_text,
                'message': f'✓ Extracted text from {len(pdf_reader.pages)} pages'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract file metadata (size, dates, permissions).

        Args:
            file_path: Path to file

        Returns:
            Dict with file metadata
        """
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            stat = path_obj.stat()

            import datetime
            metadata = {
                'success': True,
                'path': str(path_obj.absolute()),
                'name': path_obj.name,
                'size': stat.st_size,
                'size_kb': round(stat.st_size / 1024, 2),
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created': datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.datetime.fromtimestamp(stat.st_atime).isoformat(),
                'is_file': path_obj.is_file(),
                'is_dir': path_obj.is_dir(),
                'extension': path_obj.suffix.lower() if path_obj.is_file() else None,
                'parent_dir': str(path_obj.parent),
                'message': f'✓ Extracted metadata for {path_obj.name}'
            }

            return metadata

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def count_lines_of_code(self, file_path: str) -> Dict[str, Any]:
        """
        Count lines of code in source files.

        Args:
            file_path: Path to source file

        Returns:
            Dict with line counts
        """
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            with open(path_obj, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Count different types of lines
            total_lines = len(lines)
            code_lines = 0
            comment_lines = 0
            blank_lines = 0

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    blank_lines += 1
                elif stripped.startswith('#') or stripped.startswith('//'):
                    comment_lines += 1
                else:
                    code_lines += 1

            return {
                'success': True,
                'path': str(path_obj.absolute()),
                'total_lines': total_lines,
                'code_lines': code_lines,
                'comment_lines': comment_lines,
                'blank_lines': blank_lines,
                'language': path_obj.suffix.lower(),
                'message': f'✓ Analyzed {total_lines} lines in {path_obj.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def validate_json_file(self, path: str) -> Dict[str, Any]:
        """
        Validate JSON file syntax.

        Args:
            path: Path to JSON file

        Returns:
            Dict with validation result
        """
        try:
            read_result = self.read_file(path)
            if not read_result['success']:
                return read_result

            content = read_result['data']
            parsed = json.loads(content)

            return {
                'success': True,
                'path': path,
                'valid': True,
                'size': len(content),
                'parsed_type': type(parsed).__name__,
                'message': f'✓ Valid JSON file: {Path(path).name}'
            }

        except json.JSONDecodeError as e:
            return {
                'success': True,
                'path': path,
                'valid': False,
                'error': f'JSON syntax error: {str(e)}',
                'message': f'⚠️ Invalid JSON file: {Path(path).name}'
            }
        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def validate_yaml_file(self, path: str) -> Dict[str, Any]:
        """
        Validate YAML file syntax.

        Args:
            path: Path to YAML file

        Returns:
            Dict with validation result
        """
        try:
            if not self._install_if_missing('PyYAML', 'yaml'):
                return {'success': False, 'error': 'Failed to install PyYAML'}

            import yaml

            read_result = self.read_file(path)
            if not read_result['success']:
                return read_result

            content = read_result['data']
            parsed = yaml.safe_load(content)

            return {
                'success': True,
                'path': path,
                'valid': True,
                'size': len(content),
                'parsed_type': type(parsed).__name__,
                'message': f'✓ Valid YAML file: {Path(path).name}'
            }

        except yaml.YAMLError as e:
            return {
                'success': True,
                'path': path,
                'valid': False,
                'error': f'YAML syntax error: {str(e)}',
                'message': f'⚠️ Invalid YAML file: {Path(path).name}'
            }
        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    # ============================================
    # TIER 5: BULK OPERATIONS
    # ============================================

    def batch_rename(self, directory: str, pattern: str, replacement: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Batch rename files in directory.

        Args:
            directory: Directory containing files to rename
            pattern: Pattern to replace in filenames
            replacement: Replacement string
            dry_run: Preview changes without executing

        Returns:
            Dict with rename operations
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return {'success': False, 'error': f'Directory not found: {directory}'}

            operations = []
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    old_name = file_path.name
                    new_name = old_name.replace(pattern, replacement)

                    if old_name != new_name:
                        operations.append({
                            'old_path': str(file_path),
                            'new_path': str(file_path.parent / new_name),
                            'old_name': old_name,
                            'new_name': new_name
                        })

            if not dry_run:
                for op in operations:
                    Path(op['old_path']).rename(op['new_path'])

            return {
                'success': True,
                'directory': str(dir_path.absolute()),
                'operations': operations,
                'count': len(operations),
                'dry_run': dry_run,
                'executed': not dry_run,
                'message': f'✓ {"Previewed" if dry_run else "Executed"} {len(operations)} renames'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def find_files(self, directory: str, pattern: str = '*', recursive: bool = True,
                  file_type: str = None) -> Dict[str, Any]:
        """
        Advanced file search with filtering.

        Args:
            directory: Directory to search in
            pattern: Glob pattern to match
            recursive: Search subdirectories
            file_type: Filter by file type ('file', 'dir', or None for both)

        Returns:
            Dict with found files
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return {'success': False, 'error': f'Directory not found: {directory}'}

            if recursive:
                matches = list(dir_path.rglob(pattern))
            else:
                matches = list(dir_path.glob(pattern))

            # Filter by type
            if file_type == 'file':
                matches = [m for m in matches if m.is_file()]
            elif file_type == 'dir':
                matches = [m for m in matches if m.is_dir()]

            results = []
            for match in matches:
                stat = match.stat()
                results.append({
                    'path': str(match.absolute()),
                    'name': match.name,
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'is_file': match.is_file(),
                    'is_dir': match.is_dir()
                })

            return {
                'success': True,
                'directory': str(dir_path.absolute()),
                'pattern': pattern,
                'recursive': recursive,
                'file_type': file_type,
                'results': results,
                'count': len(results),
                'message': f'✓ Found {len(results)} files matching pattern'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def merge_files(self, file_list: List[str], output_path: str, delimiter: str = '\n\n') -> Dict[str, Any]:
        """
        Merge multiple files into one.

        Args:
            file_list: List of file paths to merge
            output_path: Output file path
            delimiter: String to insert between files

        Returns:
            Dict with merge result
        """
        try:
            merged_content = []
            total_size = 0

            for file_path in file_list:
                read_result = self.read_file(file_path)
                if read_result['success']:
                    merged_content.append(read_result['data'])
                    total_size += read_result['size']
                else:
                    return {'success': False, 'error': f'Failed to read {file_path}: {read_result["error"]}'}

            final_content = delimiter.join(merged_content)

            write_result = self.write_file(output_path, final_content)
            if not write_result['success']:
                return write_result

            return {
                'success': True,
                'output_path': output_path,
                'files_merged': len(file_list),
                'total_input_size': total_size,
                'output_size': len(final_content),
                'message': f'✓ Merged {len(file_list)} files into {Path(output_path).name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def split_file(self, large_file: str, chunk_size_mb: int) -> Dict[str, Any]:
        """
        Split large file into chunks.

        Args:
            large_file: Path to file to split
            chunk_size_mb: Size of each chunk in MB

        Returns:
            Dict with split result
        """
        try:
            file_path = Path(large_file)
            if not file_path.exists():
                return {'success': False, 'error': f'File not found: {large_file}'}

            chunk_size_bytes = chunk_size_mb * 1024 * 1024
            file_size = file_path.stat().st_size

            if file_size <= chunk_size_bytes:
                return {'success': False, 'error': f'File size ({file_size} bytes) is smaller than chunk size'}

            chunks_created = []
            with open(file_path, 'rb') as f:
                chunk_num = 0
                while True:
                    chunk = f.read(chunk_size_bytes)
                    if not chunk:
                        break

                    chunk_name = f"{file_path.stem}_part{chunk_num:03d}{file_path.suffix}"
                    chunk_path = file_path.parent / chunk_name

                    with open(chunk_path, 'wb') as chunk_file:
                        chunk_file.write(chunk)

                    chunks_created.append({
                        'path': str(chunk_path.absolute()),
                        'size': len(chunk)
                    })
                    chunk_num += 1

            return {
                'success': True,
                'original_file': str(file_path.absolute()),
                'original_size': file_size,
                'chunk_size_mb': chunk_size_mb,
                'chunks_created': len(chunks_created),
                'chunks': chunks_created,
                'message': f'✓ Split file into {len(chunks_created)} chunks'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def sync_directories(self, source: str, dest: str, mode: str = 'mirror') -> Dict[str, Any]:
        """
        Synchronize directories.

        Args:
            source: Source directory
            dest: Destination directory
            mode: Sync mode ('mirror', 'update', 'backup')

        Returns:
            Dict with sync result
        """
        try:
            source_path = Path(source)
            dest_path = Path(dest)

            if not source_path.exists():
                return {'success': False, 'error': f'Source directory not found: {source}'}

            dest_path.mkdir(parents=True, exist_ok=True)

            operations = []
            total_copied = 0
            total_size = 0

            # Walk source directory
            for src_file in source_path.rglob('*'):
                if src_file.is_file():
                    # Calculate relative path
                    rel_path = src_file.relative_to(source_path)
                    dest_file = dest_path / rel_path

                    # Check if copy is needed
                    needs_copy = False
                    if not dest_file.exists():
                        needs_copy = True
                    elif mode == 'mirror':
                        needs_copy = True  # Always copy in mirror mode
                    elif mode == 'update':
                        needs_copy = src_file.stat().st_mtime > dest_file.stat().st_mtime

                    if needs_copy:
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dest_file)

                        operations.append({
                            'operation': 'copy',
                            'source': str(src_file),
                            'dest': str(dest_file),
                            'size': src_file.stat().st_size
                        })

                        total_copied += 1
                        total_size += src_file.stat().st_size

            return {
                'success': True,
                'source': str(source_path.absolute()),
                'dest': str(dest_path.absolute()),
                'mode': mode,
                'operations': operations,
                'files_copied': total_copied,
                'total_size': total_size,
                'message': f'✓ Synced {total_copied} files ({round(total_size/1024/1024, 2)} MB)'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def batch_rename(self, directory: str, pattern: str, replacement: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Batch rename files in directory.

        Args:
            directory: Directory containing files to rename
            pattern: Pattern to replace in filenames
            replacement: Replacement string
            dry_run: Preview changes without executing

        Returns:
            Dict with rename operations
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return {'success': False, 'error': f'Directory not found: {directory}'}

            operations = []
            count = 0

            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    old_name = file_path.name
                    new_name = old_name.replace(pattern, replacement)

                    if new_name != old_name:
                        old_path = file_path
                        new_path = file_path.parent / new_name

                        operations.append({
                            'old_path': str(old_path),
                            'new_path': str(new_path),
                            'old_name': old_name,
                            'new_name': new_name
                        })

                        if not dry_run:
                            file_path.rename(new_path)

                        count += 1

            return {
                'success': True,
                'directory': str(dir_path.absolute()),
                'pattern': pattern,
                'replacement': replacement,
                'dry_run': dry_run,
                'executed': not dry_run,
                'count': count,
                'operations': operations,
                'message': f'✓ {"Previewed" if dry_run else "Executed"} {count} renames'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def find_files(self, directory: str, pattern: str = '*', recursive: bool = True, file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Advanced file search with filtering.

        Args:
            directory: Directory to search in
            pattern: Glob pattern to match
            recursive: Search subdirectories
            file_type: Filter by type ('file', 'dir', or None)

        Returns:
            Dict with search results
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return {'success': False, 'error': f'Directory not found: {directory}'}

            if recursive:
                matches = list(dir_path.rglob(pattern))
            else:
                matches = list(dir_path.glob(pattern))

            # Filter by type
            if file_type == 'file':
                matches = [m for m in matches if m.is_file()]
            elif file_type == 'dir':
                matches = [m for m in matches if m.is_dir()]

            # Build result list
            results = []
            for match in matches:
                result = {
                    'name': match.name,
                    'path': str(match.absolute()),
                    'relative_path': str(match.relative_to(dir_path)),
                    'is_file': match.is_file(),
                    'is_dir': match.is_dir()
                }

                if match.is_file():
                    stat = match.stat()
                    result.update({
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })

                results.append(result)

            return {
                'success': True,
                'directory': str(dir_path.absolute()),
                'pattern': pattern,
                'recursive': recursive,
                'file_type': file_type,
                'matches': results,
                'count': len(results),
                'message': f'✓ Found {len(results)} matches'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def merge_files(self, file_list: List[str], output_path: str, delimiter: str = '\n\n') -> Dict[str, Any]:
        """
        Merge multiple files into one.

        Args:
            file_list: List of file paths to merge
            output_path: Output file path
            delimiter: String to insert between files

        Returns:
            Dict with merge result
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            merged_content = []
            total_size = 0

            for file_path in file_list:
                file_obj = Path(file_path)
                if not file_obj.exists():
                    return {'success': False, 'error': f'File not found: {file_path}'}

                content = file_obj.read_text(encoding='utf-8')
                merged_content.append(content)
                total_size += len(content)

            # Write merged content
            final_content = delimiter.join(merged_content)
            output_file.write_text(final_content, encoding='utf-8')

            return {
                'success': True,
                'output_path': str(output_file.absolute()),
                'files_merged': len(file_list),
                'total_size': len(final_content),
                'delimiter': delimiter,
                'message': f'✓ Merged {len(file_list)} files into {output_file.name}'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def split_file(self, large_file: str, chunk_size_mb: int) -> Dict[str, Any]:
        """
        Split large file into chunks.

        Args:
            large_file: Path to file to split
            chunk_size_mb: Size of each chunk in MB

        Returns:
            Dict with split result
        """
        try:
            file_path = Path(large_file)
            if not file_path.exists():
                return {'success': False, 'error': f'File not found: {large_file}'}

            chunk_size_bytes = chunk_size_mb * 1024 * 1024
            file_size = file_path.stat().st_size

            if file_size <= chunk_size_bytes:
                return {'success': False, 'error': f'File is already smaller than chunk size: {file_size} bytes'}

            chunks_created = 0
            chunk_paths = []

            with open(file_path, 'rb') as f:
                chunk_num = 0
                while True:
                    chunk = f.read(chunk_size_bytes)
                    if not chunk:
                        break

                    chunk_path = file_path.parent / f"{file_path.stem}_part{chunk_num:03d}{file_path.suffix}"
                    with open(chunk_path, 'wb') as chunk_file:
                        chunk_file.write(chunk)

                    chunk_paths.append(str(chunk_path))
                    chunks_created += 1
                    chunk_num += 1

            return {
                'success': True,
                'original_file': str(file_path.absolute()),
                'original_size': file_size,
                'chunk_size_mb': chunk_size_mb,
                'chunks_created': chunks_created,
                'chunk_paths': chunk_paths,
                'message': f'✓ Split file into {chunks_created} chunks'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def search_file_contents(self, file_path: str, pattern: str, case_sensitive: bool = False,
                           max_results: int = 50, context_lines: int = 2) -> Dict[str, Any]:
        """
        Search file contents using regex patterns with context.

        Args:
            file_path: Path to file to search
            pattern: Regex pattern to search for
            case_sensitive: Whether search is case sensitive
            max_results: Maximum number of matches to return
            context_lines: Number of context lines around each match

        Returns:
            Dict with search results
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            if not path.is_file():
                return {'success': False, 'error': f'Path is not a file: {file_path}'}

            # Read file content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                return {'success': False, 'error': f'File encoding not supported: {file_path}'}

            # Compile regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return {'success': False, 'error': f'Invalid regex pattern: {e}'}

            matches = []
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    # Get context lines
                    start_ctx = max(1, line_num - context_lines)
                    end_ctx = min(len(lines), line_num + context_lines)

                    context = []
                    for ctx_line_num in range(start_ctx, end_ctx + 1):
                        marker = '>>>' if ctx_line_num == line_num else '   '
                        context.append(f'{marker} {ctx_line_num:4d}: {lines[ctx_line_num-1].rstrip()}')

                    matches.append({
                        'line_number': line_num,
                        'matched_line': line.rstrip(),
                        'context': context
                    })

                    if len(matches) >= max_results:
                        break

            return {
                'success': True,
                'file_path': str(path.absolute()),
                'pattern': pattern,
                'case_sensitive': case_sensitive,
                'total_matches': len(matches),
                'max_results': max_results,
                'matches': matches,
                'message': f'Found {len(matches)} matches'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}

    def search_and_replace(self, file_path: str, old_string: str, new_string: str,
                          dry_run: bool = True, backup: bool = True) -> Dict[str, Any]:
        """
        Search and replace content in file with diff preview.

        Args:
            file_path: Path to file to modify
            old_string: Exact string to replace
            new_string: Replacement string
            dry_run: If True, only show diff without modifying file
            backup: If True, create backup before modification

        Returns:
            Dict with operation results and diff
        """
        try:
            import difflib

            path = Path(file_path)
            if not path.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            if not path.is_file():
                return {'success': False, 'error': f'Path is not a file: {file_path}'}

            # Read original content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            except UnicodeDecodeError:
                return {'success': False, 'error': f'File encoding not supported: {file_path}'}

            # Check if old_string exists
            if old_string not in original_content:
                return {'success': False, 'error': f'Old string not found in file: {file_path}'}

            # Count occurrences
            occurrences = original_content.count(old_string)

            # Generate new content
            new_content = original_content.replace(old_string, new_string, 1)  # Replace only first occurrence

            # Generate diff
            diff = list(difflib.unified_diff(
                original_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f'a/{path.name}',
                tofile=f'b/{path.name}',
                lineterm=''
            ))

            if dry_run:
                return {
                    'success': True,
                    'dry_run': True,
                    'file_path': str(path.absolute()),
                    'occurrences_found': occurrences,
                    'will_replace_first': True,
                    'diff': diff,
                    'message': f'Dry run: Would replace 1 occurrence of old string'
                }

            # Create backup if requested
            backup_path = None
            if backup:
                backup_path = path.with_suffix(path.suffix + '.backup')
                try:
                    import shutil
                    shutil.copy2(path, backup_path)
                except Exception as e:
                    return {'success': False, 'error': f'Failed to create backup: {e}'}

            # Write new content
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            except Exception as e:
                # Restore backup if write failed
                if backup_path and backup_path.exists():
                    import shutil
                    shutil.copy2(backup_path, path)
                return {'success': False, 'error': f'Failed to write file: {e}'}

            return {
                'success': True,
                'dry_run': False,
                'file_path': str(path.absolute()),
                'backup_created': str(backup_path) if backup_path else None,
                'occurrences_replaced': 1,
                'total_occurrences': occurrences,
                'diff': diff,
                'message': f'Successfully replaced 1 occurrence'
            }

        except Exception as e:
            return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}


# ============================================
# TOOL REGISTRATION (for agent/core.py to discover)
# ============================================

TOOL_SCHEMAS = [
    # Tier 1: Core File Ops
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read text file with auto-encoding detection",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "encoding": {"type": "string", "default": "auto", "description": "Text encoding"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Text content to write"},
                    "encoding": {"type": "string", "default": "utf-8", "description": "Text encoding"},
                    "create_dirs": {"type": "boolean", "default": True, "description": "Create parent directories"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List directory contents with pattern matching",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list"},
                    "pattern": {"type": "string", "default": "*", "description": "Glob pattern to match"},
                    "recursive": {"type": "boolean", "default": False, "description": "Include subdirectories"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_exists",
            "description": "Check if file exists and return metadata",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to check"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Safely delete a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to delete"}
                },
                "required": ["path"]
            }
        }
    },

    # Tier 2: Format Transformations
    {
        "type": "function",
        "function": {
            "name": "convert_markdown_to_pdf",
            "description": "Convert Markdown to PDF with professional styling",
            "parameters": {
                "type": "object",
                "properties": {
                    "md_content": {"type": "string", "description": "Markdown content as string"},
                    "md_file": {"type": "string", "description": "Path to markdown file"},
                    "output_path": {"type": "string", "description": "Output PDF path"},
                    "style": {"type": "string", "default": "professional", "enum": ["professional", "minimal", "resume"]}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_html_to_pdf",
            "description": "Convert HTML to PDF",
            "parameters": {
                "type": "object",
                "properties": {
                    "html_content": {"type": "string", "description": "HTML content as string"},
                    "html_file": {"type": "string", "description": "Path to HTML file"},
                    "output_path": {"type": "string", "description": "Output PDF path"},
                    "css_override": {"type": "string", "description": "Additional CSS to inject"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "csv_to_excel",
            "description": "Convert CSV to Excel spreadsheet",
            "parameters": {
                "type": "object",
                "properties": {
                    "csv_path": {"type": "string", "description": "Path to CSV file"},
                    "output_path": {"type": "string", "description": "Output Excel path"},
                    "sheet_name": {"type": "string", "default": "Sheet1", "description": "Excel sheet name"}
                },
                "required": ["csv_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "excel_to_csv",
            "description": "Convert Excel to CSV",
            "parameters": {
                "type": "object",
                "properties": {
                    "xlsx_path": {"type": "string", "description": "Path to Excel file"},
                    "output_path": {"type": "string", "description": "Output CSV path"},
                    "sheet_name": {"type": "string", "default": "0", "description": "Sheet name or index"}
                },
                "required": ["xlsx_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "json_to_csv",
            "description": "Convert JSON data to CSV",
            "parameters": {
                "type": "object",
                "properties": {
                    "json_data": {"description": "JSON data (string, dict, or list)"},
                    "output_path": {"type": "string", "description": "Output CSV path"}
                },
                "required": ["json_data", "output_path"]
            }
        }
    },

    # Tier 3: Binary Operations
    {
        "type": "function",
        "function": {
            "name": "read_binary_file",
            "description": "Read binary file and return base64 encoded data",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_binary_file",
            "description": "Write binary data from base64 string to file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "data_b64": {"type": "string", "description": "Base64 encoded binary data"},
                    "create_dirs": {"type": "boolean", "default": True, "description": "Create parent directories"}
                },
                "required": ["path", "data_b64"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "encode_base64",
            "description": "Encode file to base64 string",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file to encode"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "decode_base64",
            "description": "Decode base64 string to file",
            "parameters": {
                "type": "object",
                "properties": {
                    "base64_string": {"type": "string", "description": "Base64 encoded data"},
                    "output_path": {"type": "string", "description": "Output file path"},
                    "create_dirs": {"type": "boolean", "default": True, "description": "Create parent directories"}
                },
                "required": ["base64_string", "output_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compress_files",
            "description": "Create ZIP archive from list of files",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_list": {"type": "array", "items": {"type": "string"}, "description": "List of file paths to compress"},
                    "zip_name": {"type": "string", "description": "Output ZIP file name"}
                },
                "required": ["file_list", "zip_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_archive",
            "description": "Extract ZIP or TAR archive",
            "parameters": {
                "type": "object",
                "properties": {
                    "archive_path": {"type": "string", "description": "Path to archive file"},
                    "dest_dir": {"type": "string", "description": "Destination directory"},
                    "create_dirs": {"type": "boolean", "default": True, "description": "Create destination directory"}
                },
                "required": ["archive_path", "dest_dir"]
            }
        }
    },

    # Tier 4: Smart Analysis
    {
        "type": "function",
        "function": {
            "name": "detect_file_type",
            "description": "Detect file type using magic numbers and metadata",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to analyze"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_text_from_pdf",
            "description": "Extract text content from PDF file",
            "parameters": {
                "type": "object",
                "properties": {
                    "pdf_path": {"type": "string", "description": "Path to PDF file"}
                },
                "required": ["pdf_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_metadata",
            "description": "Extract file metadata (size, dates, permissions)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "count_lines_of_code",
            "description": "Count lines of code in source files",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to source file"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_json_file",
            "description": "Validate JSON file syntax",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to JSON file"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_yaml_file",
            "description": "Validate YAML file syntax",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to YAML file"}
                },
                "required": ["path"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "search_file_contents",
            "description": "Search file contents using regex patterns with context",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file to search"},
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "case_sensitive": {"type": "boolean", "default": False, "description": "Whether search is case sensitive"},
                    "max_results": {"type": "integer", "default": 50, "description": "Maximum number of matches to return"},
                    "context_lines": {"type": "integer", "default": 2, "description": "Number of context lines around each match"}
                },
                "required": ["file_path", "pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_and_replace",
            "description": "Search and replace content in file with diff preview",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file to modify"},
                    "old_string": {"type": "string", "description": "Exact string to replace"},
                    "new_string": {"type": "string", "description": "Replacement string"},
                    "dry_run": {"type": "boolean", "default": True, "description": "If true, only show diff without modifying file"},
                    "backup": {"type": "boolean", "default": True, "description": "If true, create backup before modification"}
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        }
    },

    # Tier 5: Bulk Operations
    {
        "type": "function",
        "function": {
            "name": "batch_rename",
            "description": "Batch rename files in directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory containing files to rename"},
                    "pattern": {"type": "string", "description": "Pattern to replace in filenames"},
                    "replacement": {"type": "string", "description": "Replacement string"},
                    "dry_run": {"type": "boolean", "default": True, "description": "Preview changes without executing"}
                },
                "required": ["directory", "pattern", "replacement"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Advanced file search with filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory to search in"},
                    "pattern": {"type": "string", "default": "*", "description": "Glob pattern to match"},
                    "recursive": {"type": "boolean", "default": True, "description": "Search subdirectories"},
                    "file_type": {"type": "string", "enum": ["file", "dir", None], "description": "Filter by file type"}
                },
                "required": ["directory"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "merge_files",
            "description": "Merge multiple files into one",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_list": {"type": "array", "items": {"type": "string"}, "description": "List of file paths to merge"},
                    "output_path": {"type": "string", "description": "Output file path"},
                    "delimiter": {"type": "string", "default": "\n\n", "description": "String to insert between files"}
                },
                "required": ["file_list", "output_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "split_file",
            "description": "Split large file into chunks",
            "parameters": {
                "type": "object",
                "properties": {
                    "large_file": {"type": "string", "description": "Path to file to split"},
                    "chunk_size_mb": {"type": "integer", "description": "Size of each chunk in MB"}
                },
                "required": ["large_file", "chunk_size_mb"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sync_directories",
            "description": "Synchronize directories",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source directory"},
                    "dest": {"type": "string", "description": "Destination directory"},
                    "mode": {"type": "string", "default": "mirror", "enum": ["mirror", "update", "backup"]}
                },
                "required": ["source", "dest"]
            }
        }
    }
]

def execute_tool(operation: str, **kwargs) -> str:
    """
    Execute file operations tool.

    Args:
        operation: Tool operation name
        **kwargs: Tool arguments

    Returns:
        JSON string result
    """
    tool = FileOperationsTool()

    # Map operation names to methods
    operation_map = {
        # Tier 1: Core File Ops
        "read_file": tool.read_file,
        "write_file": tool.write_file,
        "list_directory": tool.list_directory,
        "file_exists": tool.file_exists,
        "delete_file": tool.delete_file,

        # Tier 2: Format Transformations
        "convert_markdown_to_pdf": tool.convert_markdown_to_pdf,
        "convert_html_to_pdf": tool.convert_html_to_pdf,
        "csv_to_excel": tool.csv_to_excel,
        "excel_to_csv": tool.excel_to_csv,
        "json_to_csv": tool.json_to_csv,

        # Tier 3: Binary Operations
        "read_binary_file": tool.read_binary_file,
        "write_binary_file": tool.write_binary_file,
        "encode_base64": tool.encode_base64,
        "decode_base64": tool.decode_base64,
        "compress_files": tool.compress_files,
        "extract_archive": tool.extract_archive,

        # Tier 4: Smart Analysis
        "detect_file_type": tool.detect_file_type,
        "extract_text_from_pdf": tool.extract_text_from_pdf,
        "extract_metadata": tool.extract_metadata,
        "count_lines_of_code": tool.count_lines_of_code,
        "validate_json_file": tool.validate_json_file,
        "validate_yaml_file": tool.validate_yaml_file,
        "search_file_contents": tool.search_file_contents,
        "search_and_replace": tool.search_and_replace,

        # Tier 5: Bulk Operations
        "batch_rename": tool.batch_rename,
        "find_files": tool.find_files,
        "merge_files": tool.merge_files,
        "split_file": tool.split_file,
        "sync_directories": tool.sync_directories,
    }

    if operation not in operation_map:
        return json.dumps({"success": False, "error": f"Unknown operation: {operation}"})

    try:
        result = operation_map[operation](**kwargs)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": f"{type(e).__name__}: {str(e)}"})