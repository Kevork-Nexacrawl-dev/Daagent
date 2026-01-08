"""
Partial result handler for graceful degradation.
Formats partial success responses with actionable next steps.
"""

from typing import Dict, List, Any
from agent.checkpoint import TaskCheckpoint

class PartialResultHandler:
    """Formats partial success responses for user consumption"""
    
    @staticmethod
    def format_response(checkpoint: TaskCheckpoint, final_error: str) -> str:
        """
        Format partial success response.
        
        Args:
            checkpoint: TaskCheckpoint with completed steps
            final_error: Error that stopped the task
            
        Returns:
            Formatted response string
        """
        summary = checkpoint.get_summary()
        results = checkpoint.get_results()
        
        # Build response sections
        response_parts = []
        
        # Header
        success_rate = int(summary['success_rate'] * 100)
        response_parts.append(f"⚠️ **Task Partially Completed** ({success_rate}% success)")
        response_parts.append("")
        
        # Completed steps
        if summary['completed_steps']:
            response_parts.append("## ✅ What Worked:")
            for i, step in enumerate(summary['completed_steps'], 1):
                response_parts.append(f"{i}. **{step}**")
                
                # Include result preview if available
                if step in results:
                    result_preview = PartialResultHandler._format_result_preview(results[step])
                    if result_preview:
                        response_parts.append(f"   {result_preview}")
            response_parts.append("")
        
        # Failed steps
        if summary['failed_steps']:
            response_parts.append("## ❌ What Failed:")
            for i, failure in enumerate(summary['failed_steps'], 1):
                response_parts.append(f"{i}. **{failure['step']}**")
                response_parts.append(f"   Error: {failure['error']}")
            response_parts.append("")
        
        # Final error context
        response_parts.append("## 🔍 Why It Stopped:")
        response_parts.append(final_error)
        response_parts.append("")
        
        # Next steps
        next_steps = PartialResultHandler._generate_next_steps(summary, final_error)
        if next_steps:
            response_parts.append("## 💡 Suggested Next Steps:")
            for i, step in enumerate(next_steps, 1):
                response_parts.append(f"{i}. {step}")
        
        return "\n".join(response_parts)
    
    @staticmethod
    def _format_result_preview(result: Any, max_length: int = 100) -> str:
        """
        Create a short preview of result data.
        
        Args:
            result: Result data to preview
            max_length: Maximum preview length
            
        Returns:
            Preview string
        """
        if isinstance(result, dict):
            if 'path' in result:
                return f"→ Saved to: `{result['path']}`"
            elif 'data' in result:
                preview = str(result['data'])[:max_length]
                return f"→ Data: {preview}..." if len(str(result['data'])) > max_length else f"→ Data: {preview}"
            elif 'success' in result and result['success']:
                return f"→ {result.get('message', 'Success')}"
        
        elif isinstance(result, str):
            preview = result[:max_length]
            return f"→ {preview}..." if len(result) > max_length else f"→ {preview}"
        
        return ""
    
    @staticmethod
    def _generate_next_steps(summary: Dict, final_error: str) -> List[str]:
        """
        Generate actionable next steps based on failure context.
        
        Args:
            summary: Checkpoint summary
            final_error: Error message
            
        Returns:
            List of suggested next steps
        """
        suggestions = []
        
        error_lower = final_error.lower()
        
        # File-related errors
        if "file not found" in error_lower or "no such file" in error_lower:
            suggestions.append("Check if the file path exists and is accessible")
            suggestions.append("Try using absolute paths instead of relative paths")
        
        # Network/API errors
        elif "timeout" in error_lower or "connection" in error_lower:
            suggestions.append("Retry the operation (network issue may be temporary)")
            suggestions.append("Check your internet connection")
        
        # Permission errors
        elif "permission denied" in error_lower or "unauthorized" in error_lower:
            suggestions.append("Verify you have necessary permissions/API keys")
            suggestions.append("Check if authentication tokens are valid")
        
        # Browser automation errors
        elif "browser" in error_lower or "captcha" in error_lower:
            suggestions.append("Some web forms require manual completion (CAPTCHA, verification)")
            suggestions.append("Use the data gathered so far to complete manually")
        
        # Generic fallback
        else:
            suggestions.append("Review the completed steps above - some data may be usable")
            suggestions.append("Try breaking the task into smaller steps")
        
        # Always suggest checkpoint resume if steps completed
        if summary['completed_steps']:
            suggestions.append(f"Resume from checkpoint (Task ID: {summary['task_id']})")
        
        return suggestions