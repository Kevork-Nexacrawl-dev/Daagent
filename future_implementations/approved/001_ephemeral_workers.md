## 6. future_implementations/001_ephemeral_workers.md

  

```markdown

# Ephemeral Worker Spawning System

  

**Status**: pending  

**Priority**: medium  

**Estimated Effort**: large (1-2 weeks)  

**Dependencies**: Native tools (web_search, file_ops), CLI interface  

**Phase**: 4 (after tools + CLI working)

  

---

  

## Inspiration Source

  

- Pattern observed in Dust.tt agent architecture

- User's autogen-shop experience with parallel agents

- ReAct pattern limitations with complex multi-step tasks

  

---

  

## Problem It Solves

  

### Current Limitation

Main agent executes tasks sequentially:



  

User: "Research top 5 AI frameworks"

Main Agent:

→ Search for framework 1 (wait...)

→ Search for framework 2 (wait...)

→ Search for framework 3 (wait...)

→ Synthesize results

→ Return answer

Total time: 5x search latency

  



  

### Desired Behavior

Main agent spawns parallel workers:



  

User: "Research top 5 AI frameworks"

Main Agent:

→ Spawn 5 workers in parallel

Worker 1: Research LangChain

Worker 2: Research CrewAI

Worker 3: Research AutoGen

Worker 4: Research LangGraph

Worker 5: Research Semantic Kernel

→ All execute simultaneously

→ Main agent synthesizes results

→ Workers self-destruct

Total time: 1x search latency + synthesis overhead

  



  

---

  

## Proposed Solution

  

### Architecture

  



  

class UnifiedAgent:

def run(self, user_message):

\# Detect if task benefits from parallelization

if self._needs_parallel_execution(user_message):

return self._execute_with_workers(user_message)

else:

return self._direct_execution(user_message)

  

    def _execute_with_workers(self, task):

        # 1. Decompose task into subtasks

        subtasks = self._decompose_task(task)

        # 2. Spawn workers

        workers = [

            self._spawn_worker(subtask, worker_id=i)

            for i, subtask in enumerate(subtasks)

        ]

        # 3. Execute in parallel

        results = asyncio.gather(*[w.execute() for w in workers])

        # 4. Workers self-destruct (automatic via context manager)

        # 5. Main agent synthesizes

        return self._synthesize_results(results)

    def _spawn_worker(self, subtask, worker_id):

        # Load specialist prompt if needed

        specialist_prompt = self._get_specialist_prompt(subtask)

        # Create ephemeral worker with limited scope

        return EphemeralWorker(

            task=subtask,

            worker_id=worker_id,

            base_prompt=self.base_prompt,

            specialist_prompt=specialist_prompt,

            tools=self._filter_tools(subtask),

            model=self._select_worker_model(subtask)

        )

    class EphemeralWorker:

"""

Short-lived worker agent for specific subtask.

"""

def __init__(self, task, worker_id, base_prompt, specialist_prompt, tools, model):

self.task = task

self.worker_id = worker_id

self.prompt = base_prompt + specialist_prompt

self.tools = tools

self.model = model

self.created_at = time.time()

  

    async def execute(self):

        """Execute assigned task and return result."""

        try:

            result = await self._run_task()

            logger.info(f"Worker {self.worker_id} completed in {time.time() - self.created_at:.2f}s")

            return result

        finally:

            self._

  

CONTIUATION - NEW THREAD

  

<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

  

# continue bro last thing u wrote is a half script that ended at self.

  

**Continuing from where I left off...**

  

***

  

   ```python

    async def execute(self):

        """Execute assigned task and return result."""

        try:

            result = await self._run_task()

            logger.info(f"Worker {self.worker_id} completed in {time.time() - self.created_at:.2f}s")

            return result

        finally:

            self._cleanup()  # Self-destruct

    async def _run_task(self):

        """Run ReAct loop for this specific task."""

        messages = [

            {"role": "system", "content": self.prompt},

            {"role": "user", "content": self.task}

        ]

        client = Config.get_openrouter_client()

        # Simplified ReAct loop (max 3 iterations for workers)

        for _ in range(3):

            response = await client.chat.completions.create(

                model=self.model,

                messages=messages,

                tools=self.tools

            )

            if response.choices[^0].message.tool_calls:

                # Execute tools, add results

                for tc in response.choices[^0].message.tool_calls:

                    result = self._execute_tool(tc)

                    messages.append({"role": "tool", "content": result})

                continue

            else:

                # Worker has answer

                return response.choices[^0].message.content

        return "Task incomplete (max iterations reached)"

    def _cleanup(self):

        """Self-destruct: Clear memory, close connections."""

        self.tools = None

        self.prompt = None

        logger.debug(f"Worker {self.worker_id} self-destructed")



***

  

## When to Use Workers

  

### Good Candidates for Parallel Execution:

  

**Research Tasks**:

  

- "Compare X, Y, and Z"

- "Find information about multiple topics"

- "Research top N items in category"

  

**Data Collection**:

  

- "Scrape multiple websites"

- "Fetch data from multiple APIs"

- "Process multiple files"

  

**Analysis Tasks**:

  

- "Analyze these 5 code files for bugs"

- "Review multiple documents for inconsistencies"

  
  

### NOT Good for Workers:

  

**Sequential Dependencies**:

  

- "Search X, then use results to search Y" (can't parallelize)

- "Read file, modify, write back" (order matters)

  

**Single-Step Tasks**:

  

- "Search for AI news" (no benefit from parallelization)

- "Write file" (worker overhead not worth it)

  

***

  

## Example Usage

  

```python

# User query

user: "Research LangChain, CrewAI, and AutoGen. Create comparison table."

  

# Main agent detects parallelization opportunity

main_agent._needs_parallel_execution(query) → True

main_agent._decompose_task(query) → [

    "Research LangChain architecture and features",

    "Research CrewAI architecture and features",

    "Research AutoGen architecture and features"

]

  

# Spawn 3 workers in parallel

Worker 1 (LangChain):

  → web_search("LangChain features")

  → web_search("LangChain architecture")

  → Returns: "LangChain is a framework for..."

  

Worker 2 (CrewAI):

  → web_search("CrewAI features")

  → web_search("CrewAI architecture")

  → Returns: "CrewAI focuses on..."

  

Worker 3 (AutoGen):

  → web_search("AutoGen features")

  → web_search("AutoGen architecture")

  → Returns: "AutoGen enables..."

  

# All workers complete in ~5 seconds (parallel)

# Main agent synthesizes results into comparison table

  

Output:

| Framework | Architecture | Key Features | Use Cases |

|-----------|-------------|--------------|-----------|

| LangChain | ... | ... | ... |

| CrewAI | ... | ... | ... |

| AutoGen | ... | ... | ... |



  
  

***

  

## Implementation Checklist

  

### Phase 4A: Core Worker System

  

- [ ] Create `agent/worker.py` with `EphemeralWorker` class

- [ ] Add async support to `UnifiedAgent`

- [ ] Implement task decomposition logic

- [ ] Add worker spawning mechanism

- [ ] Implement parallel execution with `asyncio.gather()`

  
  

### Phase 4B: Worker Management

  

- [ ] Add worker lifecycle tracking (created, running, completed)

- [ ] Implement worker timeout handling

- [ ] Add worker error recovery

- [ ] Implement result synthesis logic

  
  

### Phase 4C: Optimization

  

- [ ] Add worker pooling (reuse instead of spawn every time)

- [ ] Implement smart parallelization detection

- [ ] Add performance metrics (speedup vs sequential)

- [ ] Optimize worker prompts (minimal, focused)

  
  

### Phase 4D: Specialist Workers

  

- [ ] Create worker prompt templates in `prompts/workers/`

- [ ] Implement worker type selection (researcher, coder, analyst)

- [ ] Add tool filtering per worker type

- [ ] Test specialist workers vs generic workers

  

***

  

## Open Questions

  

- [ ] **Max workers**: Limit to N parallel workers to avoid rate limits?

- [ ] **Worker communication**: Should workers share data, or only main agent sees all results?

- [ ] **Cost optimization**: Use cheaper models for workers, expensive for main agent?

- [ ] **Failure handling**: If one worker fails, retry or proceed with partial results?

- [ ] **Async vs threading**: Use asyncio or multiprocessing?

  

***

  

## Success Criteria

  

1. **Performance**: 3+ subtasks complete faster than sequential

2. **Reliability**: Worker failures don't crash main agent

3. **Cost-effective**: Total token usage comparable to sequential (due to parallel efficiency)

4. **User-transparent**: User doesn't need to know workers exist

  

***

  

## Risks \& Mitigation

  

### Risk 1: API Rate Limits

  

**Mitigation**:

  

- Implement worker queue (max N concurrent)

- Add exponential backoff on rate limit errors

- Use cheaper models for workers

  
  

### Risk 2: Increased Complexity

  

**Mitigation**:

  

- Keep worker logic simple (3 iteration limit)

- Extensive testing before production

- Fallback to sequential if parallel fails

  
  

### Risk 3: Cost Explosion

  

**Mitigation**:

  

- Monitor token usage per worker

- Set budget limits per task

- Only parallelize when benefit > cost

  

***

  

## Decision Log

  

- **2025-12-25**: Feature proposed based on Dust.tt pattern

- **Status**: Pending approval, implement in Phase 4 after tools + CLI

- **Next**: User approval needed before design refinement

  

***

  

**END OF 001_ephemeral_workers.md**

  

This feature will be implemented after core tools and CLI are working.

  

```

  

---
