"""
Fallback strategy system for tool execution.
Tries primary tool, then fallbacks in sequence.
"""

import logging
from typing import List, Dict, Any
from agent.errors import AllFallbacksFailed, FatalError

logger = logging.getLogger(__name__)

class FallbackStrategy:
    """Represents a single fallback strategy"""

    def __init__(self, tool_name: str, args_transformer=None):
        """
        Args:
            tool_name: Name of the tool to use
            args_transformer: Optional function to transform args for this tool
        """
        self.tool_name = tool_name
        self.args_transformer = args_transformer or (lambda x: x)

class FallbackManager:
    """Manages fallback strategies for tool execution"""

    def __init__(self):
        """Initialize fallback manager with predefined strategies"""
        self.fallback_chains = self._define_fallback_chains()

    def _define_fallback_chains(self) -> Dict[str, List[FallbackStrategy]]:
        """
        Define fallback chains for common tool categories.

        Returns:
            Dict mapping primary tool to list of fallbacks
        """
        return {
            # Example fallback chains (expand based on your tools)
            "web_search": [
                FallbackStrategy("alternative_search_tool"),
            ],

            "read_file": [
                FallbackStrategy("read_binary_file",
                               lambda args: {**args, "encoding": "latin-1"}),
            ],
        }

    def execute_with_fallbacks(self, tool_registry, primary_tool: str,
                               args: Dict[str, Any]) -> Any:
        """
        Execute tool with fallback strategies.

        Args:
            tool_registry: ToolRegistry instance
            primary_tool: Primary tool name
            args: Tool arguments

        Returns:
            Tool execution result

        Raises:
            AllFallbacksFailed: If all strategies fail
        """
        strategies = [FallbackStrategy(primary_tool)]

        # Add predefined fallbacks if available
        if primary_tool in self.fallback_chains:
            strategies.extend(self.fallback_chains[primary_tool])

        errors = []

        for i, strategy in enumerate(strategies):
            try:
                tool_name = strategy.tool_name
                transformed_args = strategy.args_transformer(args)

                if i > 0:
                    logger.info(f"🔄 Trying fallback {i}: {tool_name}")

                result = tool_registry.execute_tool(tool_name, **transformed_args)

                if i > 0:
                    logger.info(f"✓ Fallback {i} succeeded")

                return result

            except FatalError as e:
                # Fatal errors stop fallback chain
                logger.error(f"Fatal error in {strategy.tool_name}, stopping fallbacks")
                raise

            except Exception as e:
                error_info = {
                    "tool": strategy.tool_name,
                    "error": str(e),
                    "attempt": i + 1
                }
                errors.append(error_info)
                logger.warning(f"⚠️ {strategy.tool_name} failed: {e}")

                if i < len(strategies) - 1:
                    continue
                else:
                    logger.error(f"❌ All {len(strategies)} strategies failed")
                    raise AllFallbacksFailed(errors)

        raise AllFallbacksFailed(errors)