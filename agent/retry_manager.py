"""
Retry logic with exponential backoff for tool execution.
"""

import time
import logging
from typing import Callable, Any
from agent.errors import RetryableError, FatalError

logger = logging.getLogger(__name__)

class RetryManager:
    """Handles retry logic with exponential backoff"""

    def __init__(self, max_retries=3, base_delay=1.0, max_delay=30.0):
        """
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay cap in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            FatalError: For non-retryable errors
            RetryableError: After all retries exhausted
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_retries}")
                result = func(*args, **kwargs)

                if attempt > 0:
                    logger.info(f"✓ Success after {attempt + 1} attempts")

                return result

            except FatalError:
                # Don't retry fatal errors
                logger.error(f"Fatal error, not retrying")
                raise

            except RetryableError as e:
                last_error = e

                if attempt < self.max_retries - 1:
                    delay = min(
                        self.base_delay * (2 ** attempt),  # Exponential backoff
                        self.max_delay
                    )

                    # Use retry_after if provided by error
                    if hasattr(e, 'retry_after') and e.retry_after:
                        delay = e.retry_after

                    logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ All {self.max_retries} attempts failed")
                    raise

            except Exception as e:
                # Classify unknown errors
                from agent.errors import classify_error
                classified = classify_error(e)

                if isinstance(classified, FatalError):
                    raise classified

                last_error = classified

                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise classified

        # Should never reach here, but just in case
        raise last_error if last_error else Exception("Unknown error")