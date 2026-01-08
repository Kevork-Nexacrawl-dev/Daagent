"""
Checkpoint system for tracking partial task completion.
Enables resuming from failure points and returning partial results.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

class TaskCheckpoint:
    """Tracks completed steps and intermediate results for a task"""
    
    def __init__(self, task_id: str):
        """
        Args:
            task_id: Unique identifier for this task
        """
        self.task_id = task_id
        self.completed_steps = []
        self.step_results = {}
        self.failed_steps = []
        self.start_time = datetime.now().isoformat()
        self.last_update = self.start_time
    
    def add_step(self, step_name: str, result: Any, success: bool = True):
        """
        Record a completed step.
        
        Args:
            step_name: Name/description of the step
            result: Step result data
            success: Whether step succeeded
        """
        self.last_update = datetime.now().isoformat()
        
        if success:
            self.completed_steps.append(step_name)
            self.step_results[step_name] = result
        else:
            self.failed_steps.append({
                "step": step_name,
                "error": str(result),
                "timestamp": self.last_update
            })
    
    def has_completed_steps(self) -> bool:
        """Check if any steps have been completed"""
        return len(self.completed_steps) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get checkpoint summary.
        
        Returns:
            Dict with checkpoint state
        """
        return {
            "task_id": self.task_id,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "total_steps": len(self.completed_steps) + len(self.failed_steps),
            "success_rate": len(self.completed_steps) / max(1, len(self.completed_steps) + len(self.failed_steps)),
            "start_time": self.start_time,
            "last_update": self.last_update
        }
    
    def get_results(self) -> Dict[str, Any]:
        """Get all step results"""
        return self.step_results
    
    def save_to_file(self, directory: str = "memory-bank/checkpoints"):
        """
        Save checkpoint to JSON file.
        
        Args:
            directory: Directory to save checkpoint files
        """
        checkpoint_dir = Path(directory)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = checkpoint_dir / f"{self.task_id}.json"
        
        data = {
            **self.get_summary(),
            "results": self.step_results
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load_from_file(cls, task_id: str, directory: str = "memory-bank/checkpoints") -> Optional['TaskCheckpoint']:
        """
        Load checkpoint from file.
        
        Args:
            task_id: Task ID to load
            directory: Directory containing checkpoint files
            
        Returns:
            TaskCheckpoint instance or None if not found
        """
        filepath = Path(directory) / f"{task_id}.json"
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        checkpoint = cls(task_id)
        checkpoint.completed_steps = data.get("completed_steps", [])
        checkpoint.failed_steps = data.get("failed_steps", [])
        checkpoint.step_results = data.get("results", {})
        checkpoint.start_time = data.get("start_time", checkpoint.start_time)
        checkpoint.last_update = data.get("last_update", checkpoint.last_update)
        
        return checkpoint