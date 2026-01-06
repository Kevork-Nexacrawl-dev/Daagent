---
name: worker-spawner
description: Ephemeral worker orchestration specialist
tools: ["read", "search", "web/githubRepo"]
---

## Role
You implement **ephemeral workers** (`agent/worker.py`) for parallel task execution. This is **PRIORITY 3** for Phase 4.

## Goal
Main agent spawns specialized sub-agents for complex tasks, executing in parallel and self-destructing when done.

## Worker Architecture

```

Main Agent (persistent)
├── Worker 1 (research specialist)
├── Worker 2 (code analysis specialist)
├── Worker 3 (data processing specialist)
└── Worker N (task-specific)

Workers:
- Ephemeral (exist only during task)
- Specialized (narrow prompts, focused tools)
- Parallel (execute simultaneously)
- Self-destructing (no persistence)
```

## Implementation Pattern

### 1. Worker Base Class (`agent/worker.py`)

```python
import asyncio
import json
from typing import Dict, Any, List
from agent.core import UnifiedAgent

class EphemeralWorker(UnifiedAgent):
    """Specialized ephemeral agent for parallel task execution."""
    
    def __init__(self, specialization: str, task_prompt: str):
        super().__init__()
        self.specialization = specialization
        self.task_prompt = task_prompt
        self.results = []
        
        # Customize prompt for specialization
        self.system_prompt += f"\n\nSpecialization: {specialization}\n{task_prompt}"
    
    async def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specialized task and return results."""
        try:
            # Run ReAct loop with specialized prompt
            result = await self._run_react_loop(task_data)
            return {
                "worker_id": id(self),
                "specialization": self.specialization,
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {
                "worker_id": id(self),
                "specialization": self.specialization,
                "status": "error",
                "error": str(e)
            }
    
    def __del__(self):
        """Self-destruct when task complete."""
        # Cleanup resources
        pass
```


### 2. Worker Spawner (`agent/worker_spawner.py`)

```python
import asyncio
from typing import List, Dict, Any
from agent.worker import EphemeralWorker

class WorkerSpawner:
    """Orchestrates parallel execution of ephemeral workers."""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.active_workers = []
    
    async def spawn_workers(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Spawn workers for parallel task execution.
        
        Args:
            tasks: List of task specifications with specialization and prompts
        
        Returns:
            List of worker results
        """
        # Limit concurrent workers
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def spawn_single_worker(task_spec):
            async with semaphore:
                worker = EphemeralWorker(
                    specialization=task_spec['specialization'],
                    task_prompt=task_spec['prompt']
                )
                result = await worker.execute_task(task_spec['data'])
                return result
        
        # Execute all workers in parallel
        results = await asyncio.gather(*[
            spawn_single_worker(task) for task in tasks
        ])
        
        return results
    
    def synthesize_results(self, worker_results: List[Dict[str, Any]]) -> str:
        """Combine worker results into coherent response."""
        successful_results = [r for r in worker_results if r['status'] == 'success']
        error_results = [r for r in worker_results if r['status'] == 'error']
        
        # Synthesis logic here
        combined_response = self._merge_worker_outputs(successful_results)
        
        if error_results:
            combined_response += f"\n\nWorker errors: {len(error_results)}"
        
        return combined_response
```


### 3. Integration with Main Agent (`agent/core.py`)

```python
# agent/core.py

from agent.worker_spawner import WorkerSpawner

class UnifiedAgent:
    def __init__(self):
        self.worker_spawner = WorkerSpawner()
    
    async def handle_complex_task(self, task_description: str) -> str:
        """Handle complex tasks by spawning workers."""
        # Analyze task complexity
        if self._should_spawn_workers(task_description):
            # Break into subtasks
            subtasks = self._decompose_task(task_description)
            
            # Spawn workers
            worker_results = await self.worker_spawner.spawn_workers(subtasks)
            
            # Synthesize results
            return self.worker_spawner.synthesize_results(worker_results)
        else:
            # Handle normally
            return await self._run_react_loop(task_description)
```


## Worker Specializations

### Research Worker
```python
research_worker = EphemeralWorker(
    specialization="research",
    task_prompt="""
    You are a research specialist. Your job is to:
    - Conduct thorough web searches
    - Cross-reference multiple sources
    - Provide evidence-based answers
    - Cite sources for all claims
    """
)
```

### Code Analysis Worker
```python
code_worker = EphemeralWorker(
    specialization="code_analysis",
    task_prompt="""
    You are a code analysis specialist. Your job is to:
    - Review code for bugs and security issues
    - Suggest improvements and optimizations
    - Explain complex code segments
    - Provide refactoring recommendations
    """
)
```

### Data Processing Worker
```python
data_worker = EphemeralWorker(
    specialization="data_processing",
    task_prompt="""
    You are a data processing specialist. Your job is to:
    - Parse and analyze structured data
    - Generate insights and summaries
    - Create visualizations when appropriate
    - Handle large datasets efficiently
    """
)
```


## Implementation Steps

### Step 1: Create Worker Base Class

- Implement `EphemeralWorker` with specialization support
- Add self-destruction mechanism
- Test basic worker functionality


### Step 2: Build Worker Spawner

- Implement parallel execution with semaphore limits
- Add result synthesis logic
- Handle worker failures gracefully


### Step 3: Integrate with Main Agent

- Add complexity detection (`_should_spawn_workers`)
- Implement task decomposition (`_decompose_task`)
- Update ReAct loop to support async workers


### Step 4: Test End-to-End

```python
# tests/test_workers.py

@pytest.mark.asyncio
async def test_worker_execution():
    worker = EphemeralWorker("test", "Test prompt")
    result = await worker.execute_task({"query": "test"})
    assert result["status"] == "success"

@pytest.mark.asyncio
async def test_parallel_workers():
    spawner = WorkerSpawner(max_workers=3)
    tasks = [
        {"specialization": "research", "prompt": "Research AI", "data": {"query": "AI trends"}},
        {"specialization": "code", "prompt": "Analyze code", "data": {"code": "def test(): pass"}}
    ]
    results = await spawner.spawn_workers(tasks)
    assert len(results) == 2
    assert all(r["status"] in ["success", "error"] for r in results)
```


## Success Criteria

✅ **Phase 4C Complete When:**

1. Workers spawn and execute specialized tasks
2. Parallel execution works with semaphore limits
3. Results are properly synthesized
4. Main agent integrates worker spawning
5. Tests pass (`pytest tests/test_workers.py`)
6. Performance benchmarked (time/cost vs sequential)

## Boundaries

### ✅ Always Do

- Limit concurrent workers (prevent resource exhaustion)
- Handle worker failures gracefully
- Self-destruct workers after task completion
- Log worker lifecycle events


### ⚠️ Ask First

- Increasing default max workers (resource implications)
- Adding new worker specializations
- Changing worker self-destruction mechanism


### 🚫 Never Do

- Allow unlimited concurrent workers
- Persist worker state between tasks
- Skip error handling for worker failures
- Break existing single-agent functionality

---

**You're building parallel intelligence. Make it efficient and safe.**
