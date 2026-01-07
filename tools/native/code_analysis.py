"""
Code Analysis - Daagent Native Tools
Ported from autogen-shop with adaptations for OpenAI function calling.
"""

import json
import ast
import re
from typing import Dict, Any

# ============================================
# TOOL SCHEMAS (OpenAI Function Calling Format)
# ============================================

VALIDATE_SYNTAX_SCHEMA = {
    "type": "function",
    "function": {
        "name": "validate_syntax",
        "description": "Check if Python code has valid syntax using AST parsing",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python source code to validate"
                }
            },
            "required": ["code"]
        }
    }
}

ANALYZE_IMPORTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "analyze_imports",
        "description": "Extract and analyze all import statements from Python code",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python source code to analyze"
                }
            },
            "required": ["code"]
        }
    }
}

DETECT_DEPENDENCIES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "detect_dependencies",
        "description": "Identify required packages and dependencies from Python code",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python source code to analyze"
                }
            },
            "required": ["code"]
        }
    }
}

# ============================================
# TOOL IMPLEMENTATIONS
# ============================================

def execute_validate_syntax(args: Dict[str, Any]) -> str:
    """
    Execute validate_syntax tool.

    Args:
        args: Dict with 'code' key containing Python source code

    Returns:
        JSON string with validation result
    """
    try:
        code = args.get("code", "")
        if not code.strip():
            return json.dumps({"status": "error", "error": "No code provided"})

        ast.parse(code)
        return json.dumps({
            "status": "success",
            "valid": True,
            "message": "Syntax is valid"
        })
    except SyntaxError as e:
        return json.dumps({
            "status": "success",
            "valid": False,
            "error": str(e),
            "line": e.lineno,
            "offset": e.offset
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"Validation failed: {str(e)}"
        })


def execute_analyze_imports(args: Dict[str, Any]) -> str:
    """
    Execute analyze_imports tool.

    Args:
        args: Dict with 'code' key containing Python source code

    Returns:
        JSON string with import analysis
    """
    try:
        code = args.get("code", "")
        if not code.strip():
            return json.dumps({"status": "error", "error": "No code provided"})

        tree = ast.parse(code)

        imports = []
        from_imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "alias": alias.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    from_imports.append({
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname
                    })

        all_modules = set([imp["module"] for imp in imports] +
                         [imp["module"] for imp in from_imports])

        return json.dumps({
            "status": "success",
            "import_count": len(imports),
            "from_import_count": len(from_imports),
            "unique_modules": len(all_modules),
            "imports": imports,
            "from_imports": from_imports,
            "modules": sorted(list(all_modules))
        })
    except SyntaxError as e:
        return json.dumps({"status": "error", "error": f"Syntax error: {e}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def execute_detect_dependencies(args: Dict[str, Any]) -> str:
    """
    Execute detect_dependencies tool.

    Args:
        args: Dict with 'code' key containing Python source code

    Returns:
        JSON string with dependency analysis
    """
    try:
        code = args.get("code", "")
        if not code.strip():
            return json.dumps({"status": "error", "error": "No code provided"})

        # Get imports first
        import_result = json.loads(execute_analyze_imports(args))
        if import_result["status"] != "success":
            return json.dumps(import_result)

        modules = import_result.get("modules", [])

        # Known standard library modules (don't need installation)
        stdlib_modules = {
            'os', 'sys', 're', 'json', 'datetime', 'time', 'math', 'random',
            'collections', 'itertools', 'functools', 'operator', 'pathlib',
            'typing', 'dataclasses', 'enum', 'abc', 'contextlib', 'io', 'ast'
        }

        # Detect potential third-party packages
        third_party = []
        for module in modules:
            if module and module not in stdlib_modules:
                # Check for common package name patterns
                if '.' in module:
                    package = module.split('.')[0]
                else:
                    package = module

                # Skip if it's a local module pattern
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', package):
                    continue

                third_party.append(package)

        # Remove duplicates and sort
        third_party = sorted(list(set(third_party)))

        return json.dumps({
            "status": "success",
            "total_modules": len(modules),
            "stdlib_modules": len([m for m in modules if m in stdlib_modules]),
            "third_party_packages": len(third_party),
            "packages": third_party,
            "analysis": {
                "stdlib_found": [m for m in modules if m in stdlib_modules],
                "third_party_found": third_party
            }
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ============================================
# REGISTRY (for agent/core.py to discover)
# ============================================

TOOL_SCHEMAS = [VALIDATE_SYNTAX_SCHEMA, ANALYZE_IMPORTS_SCHEMA, DETECT_DEPENDENCIES_SCHEMA]

def execute_tool(operation: str, **kwargs) -> str:
    """
    Execute code analysis tool.

    Args:
        operation: Tool operation name
        **kwargs: Tool arguments

    Returns:
        JSON string result
    """
    if operation == "validate_syntax":
        return execute_validate_syntax(kwargs)
    elif operation == "analyze_imports":
        return execute_analyze_imports(kwargs)
    elif operation == "detect_dependencies":
        return execute_detect_dependencies(kwargs)
    else:
        return json.dumps({"status": "error", "error": f"Unknown operation: {operation}"})