"""
Integration with existing MCP Module Manager warehouse.
Uses mcpmanager.py API for module discovery and management.
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Any


class MCPWarehouse:
    """Interface to existing MCP Module Manager"""

    def __init__(self, warehouse_path: str):
        """
        Initialize warehouse connection.

        Args:
            warehouse_path: Path to mcp-module-manager directory
        """
        self.warehouse_path = Path(warehouse_path)

        if not self.warehouse_path.exists():
            raise ValueError(f"MCP warehouse not found: {warehouse_path}")

        # Add warehouse to Python path to import mcp_manager
        sys.path.insert(0, str(self.warehouse_path))

        try:
            # Import the existing manager
            import mcp_manager
            self.manager = mcp_manager.EnhancedMCPModuleManager()
            print(f"📦 Connected to MCP Warehouse: {self.warehouse_path}")
        except ImportError as e:
            print(f"⚠️  MCP Warehouse not available: {e}")
            print("   Continuing with native tools only")
            self.manager = None

    def list_available_modules(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available modules from warehouse.

        Returns:
            Dict of module_name -> module_info
        """
        if self.manager is None:
            return {}
        return self.manager.list_available_modules()

    def get_active_modules(self) -> List[str]:
        """
        Get currently loaded modules.

        Returns:
            List of active module names
        """
        if self.manager is None:
            return []
        return self.manager.get_active_modules()

    def load_module(self, module_name: str) -> Dict[str, Any]:
        """
        Load a module (activates its MCP server).

        Args:
            module_name: Name of module to load

        Returns:
            Result dict with status and details
        """
        if self.manager is None:
            return {"status": "error", "message": "MCP warehouse not available"}
        return self.manager.load_module(module_name)

    def unload_module(self, module_name: str) -> Dict[str, Any]:
        """
        Unload a module.

        Args:
            module_name: Name of module to unload

        Returns:
            Result dict
        """
        if self.manager is None:
            return {"status": "error", "message": "MCP warehouse not available"}
        return self.manager.unload_module(module_name)

    def get_module_info(self, module_name: str) -> Dict[str, Any]:
        """
        Get detailed info about a specific module.

        Args:
            module_name: Module name

        Returns:
            Module metadata including tools list
        """
        if self.manager is None:
            return {}
        
        # Try to get from manager first
        modules = self.list_available_modules()
        module_meta = modules.get(module_name, {})
        
        # Load full module info from JSON file
        if 'path' in module_meta:
            try:
                import json
                with open(module_meta['path'], 'r', encoding='utf-8') as f:
                    full_info = json.load(f)
                # Merge with metadata
                full_info.update(module_meta)
                return full_info
            except Exception as e:
                print(f"Warning: Could not load full info for {module_name}: {e}")
        
        return module_meta

    def analyze_task(self, task_description: str) -> Dict[str, Any]:
        """
        Use warehouse's AI to analyze task requirements.

        Args:
            task_description: User's task description

        Returns:
            Analysis with recommended modules
        """
        if self.manager is None:
            return {"status": "error", "message": "MCP warehouse not available"}
        return self.manager.analyze_task_requirements(task_description)

    def adaptive_load(self, task_description: str) -> Dict[str, Any]:
        """
        Adaptively load modules based on task.

        Args:
            task_description: User's task

        Returns:
            Load result with modules activated
        """
        if self.manager is None:
            return {"status": "error", "message": "MCP warehouse not available"}
        return self.manager.adaptive_load_for_task(task_description)


# MCPToolAdapter moved to tools/mcp/adapters/__init__.py