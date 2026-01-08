"""
Error classification system for Daagent.
Categorizes errors into retryable, fatal, and partial success types.
"""

class ToolError(Exception):
    """Base exception for all tool errors"""
    pass

class RetryableError(ToolError):
    """Error that can be retried (network issues, rate limits, transient failures)"""
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after

class FatalError(ToolError):
    """Error that cannot be retried (file not found, invalid arguments, permissions)"""
    pass

class PartialSuccess(ToolError):
    """Task partially completed with some results available"""
    def __init__(self, message, completed_data=None, failed_steps=None):
        super().__init__(message)
        self.completed_data = completed_data or {}
        self.failed_steps = failed_steps or []

class AllFallbacksFailed(ToolError):
    """All primary and fallback strategies failed"""
    def __init__(self, errors):
        self.errors = errors
        super().__init__(f"All strategies failed: {len(errors)} errors")

def classify_error(exception: Exception) -> ToolError:
    """
    Classify generic exceptions into error types.

    Args:
        exception: The exception to classify

    Returns:
        Appropriate ToolError subclass
    """
    error_msg = str(exception).lower()

    # Retryable errors
    retryable_keywords = [
        "rate limit", "429", "quota exceeded",
        "timeout", "connection", "network",
        "temporarily unavailable", "try again"
    ]

    if any(kw in error_msg for kw in retryable_keywords):
        return RetryableError(str(exception))

    # Fatal errors
    fatal_keywords = [
        "file not found", "404", "permission denied",
        "invalid argument", "unauthorized", "403",
        "does not exist", "no such file"
    ]

    if any(kw in error_msg for kw in fatal_keywords):
        return FatalError(str(exception))

    # Default to retryable (safer to retry than fail immediately)
    return RetryableError(str(exception))