"""
Data Operations - Daagent Native Tools
Ported from autogen-shop with adaptations for OpenAI function calling.
"""

import json
import re
import statistics
from typing import Dict, Any, List

# ============================================
# TOOL SCHEMAS (OpenAI Function Calling Format)
# ============================================

PARSE_SALARY_RANGES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "parse_salary_ranges",
        "description": "Extract and parse salary ranges from text (e.g., job descriptions)",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text containing salary information"
                }
            },
            "required": ["text"]
        }
    }
}

TRANSFORM_CSV_SCHEMA = {
    "type": "function",
    "function": {
        "name": "transform_csv",
        "description": "Transform CSV data with filtering, sorting, and column operations",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of CSV row objects"
                },
                "operations": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of transformation operations"
                }
            },
            "required": ["data"]
        }
    }
}

NORMALIZE_DATA_SCHEMA = {
    "type": "function",
    "function": {
        "name": "normalize_data",
        "description": "Normalize numerical data to a specified range",
        "parameters": {
            "type": "object",
            "properties": {
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "List of numerical values to normalize"
                },
                "min_val": {
                    "type": "number",
                    "description": "Minimum output value",
                    "default": 0
                },
                "max_val": {
                    "type": "number",
                    "description": "Maximum output value",
                    "default": 100
                }
            },
            "required": ["values"]
        }
    }
}

# ============================================
# TOOL IMPLEMENTATIONS
# ============================================

def execute_parse_salary_ranges(args: Dict[str, Any]) -> str:
    """
    Execute parse_salary_ranges tool.

    Args:
        args: Dict with 'text' key containing text with salary info

    Returns:
        JSON string with parsed salary ranges
    """
    try:
        text = args.get("text", "")
        if not text.strip():
            return json.dumps({"status": "error", "error": "No text provided"})

        ranges = []

        # Pattern: $50,000 - $75,000 or $50k-$75k
        range_pattern = r"\$(\d+(?:,\d{3})*(?:k)?)\s*(?:-|to)\s*\$(\d+(?:,\d{3})*(?:k)?)"
        matches = re.findall(range_pattern, text, re.IGNORECASE)

        for match in matches:
            min_val = match[0].replace(',', '')
            max_val = match[1].replace(',', '')

            # Convert 'k' notation
            if 'k' in min_val.lower():
                min_val = str(int(min_val.lower().replace('k', '')) * 1000)
            if 'k' in max_val.lower():
                max_val = str(int(max_val.lower().replace('k', '')) * 1000)

            ranges.append({
                "min": int(min_val),
                "max": int(max_val),
                "range": int(max_val) - int(min_val),
                "midpoint": (int(min_val) + int(max_val)) // 2
            })

        # If no ranges found, look for single salaries
        if not ranges:
            single_pattern = r"\$(\d+(?:,\d{3})*(?:k)?)"
            singles = re.findall(single_pattern, text)
            for sal in singles[:5]:
                val = sal.replace(',', '')
                if 'k' in val.lower():
                    val = str(int(val.lower().replace('k', '')) * 1000)
                val = int(val)
                ranges.append({
                    "min": val,
                    "max": val,
                    "range": 0,
                    "midpoint": val
                })

        return json.dumps({
            "status": "success",
            "ranges_found": len(ranges),
            "ranges": ranges,
            "overall_min": min([r["min"] for r in ranges]) if ranges else None,
            "overall_max": max([r["max"] for r in ranges]) if ranges else None
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def execute_transform_csv(args: Dict[str, Any]) -> str:
    """
    Execute transform_csv tool.

    Args:
        args: Dict with 'data' and optional 'operations'

    Returns:
        JSON string with transformed data
    """
    try:
        data = args.get("data", [])
        operations = args.get("operations", [])

        if not data:
            return json.dumps({"status": "error", "error": "No data provided"})

        transformed_data = data.copy()

        # Apply operations
        for op in operations:
            op_type = op.get("type", "")
            if op_type == "filter":
                column = op.get("column")
                condition = op.get("condition", "")
                value = op.get("value")

                if column and condition:
                    if condition == "equals":
                        transformed_data = [row for row in transformed_data if row.get(column) == value]
                    elif condition == "contains":
                        transformed_data = [row for row in transformed_data if value in str(row.get(column, ""))]
                    elif condition == "greater_than":
                        transformed_data = [row for row in transformed_data if float(row.get(column, 0)) > float(value)]
                    elif condition == "less_than":
                        transformed_data = [row for row in transformed_data if float(row.get(column, 0)) < float(value)]

            elif op_type == "sort":
                column = op.get("column")
                ascending = op.get("ascending", True)
                if column:
                    transformed_data.sort(key=lambda x: x.get(column, ""), reverse=not ascending)

            elif op_type == "add_column":
                column = op.get("column")
                expression = op.get("expression", "")
                if column and expression:
                    for row in transformed_data:
                        # Simple expression evaluation (basic math)
                        try:
                            # Replace column references with values
                            expr = expression
                            for col, val in row.items():
                                if isinstance(val, (int, float)):
                                    expr = expr.replace(f"{{{col}}}", str(val))
                            result = eval(expr, {"__builtins__": {}})
                            row[column] = result
                        except:
                            row[column] = None

        return json.dumps({
            "status": "success",
            "original_rows": len(data),
            "transformed_rows": len(transformed_data),
            "operations_applied": len(operations),
            "data": transformed_data
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def execute_normalize_data(args: Dict[str, Any]) -> str:
    """
    Execute normalize_data tool.

    Args:
        args: Dict with 'values' and optional min_val/max_val

    Returns:
        JSON string with normalized data
    """
    try:
        values = args.get("values", [])
        min_val = args.get("min_val", 0)
        max_val = args.get("max_val", 100)

        if not values:
            return json.dumps({"status": "error", "error": "No values provided"})

        values = [float(v) for v in values]

        data_min = min(values)
        data_max = max(values)
        data_range = data_max - data_min

        if data_range == 0:
            normalized = [max_val] * len(values)
        else:
            normalized = [
                ((score - data_min) / data_range) * (max_val - min_val) + min_val
                for score in values
            ]

        return json.dumps({
            "status": "success",
            "original_range": {"min": data_min, "max": data_max},
            "normalized_range": {"min": min_val, "max": max_val},
            "normalized_values": [round(s, 2) for s in normalized],
            "original_values": values
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ============================================
# REGISTRY (for agent/core.py to discover)
# ============================================

TOOL_SCHEMAS = [PARSE_SALARY_RANGES_SCHEMA, TRANSFORM_CSV_SCHEMA, NORMALIZE_DATA_SCHEMA]

def execute_tool(operation: str, **kwargs) -> str:
    """
    Execute data operations tool.

    Args:
        operation: Tool operation name
        **kwargs: Tool arguments

    Returns:
        JSON string result
    """
    if operation == "parse_salary_ranges":
        return execute_parse_salary_ranges(kwargs)
    elif operation == "transform_csv":
        return execute_transform_csv(kwargs)
    elif operation == "normalize_data":
        return execute_normalize_data(kwargs)
    else:
        return json.dumps({"status": "error", "error": f"Unknown operation: {operation}"})