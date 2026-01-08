# Daagent CLI Usage Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run CLI
python main.py
```

## Basic Usage

### Interactive Mode
```bash
python main.py

Daagent CLI v2.0
Type your query, 'help' for commands, 'exit' to quit

You: Execute Python persistent: x = 42; print(x)
Agent: 42

You: Execute Python persistent: print(x * 2)
Agent: 84
```

### Single Query Mode
```bash
python main.py "Read file: data.csv"
```

### Command Line Options
```bash
python main.py --help                    # Show all options
python main.py --dev-mode               # Use free models
python main.py --prod-mode              # Use paid models
python main.py --model grok-4-fast      # Force specific model
python main.py --list-tools             # List available tools
python main.py --version                # Show version
python main.py --clear-cache            # Clear response cache
```

## Commands

- `/help` or `/h` - Show help message
- `/reset` - Clear conversation history
- `/exit` or `/q` - Exit the CLI
- `/list-tools` - List all available tools
- `/session list` - List active sessions
- `/session info <id>` - Show session details
- `/session kill <id>` - Terminate session
- `/session cleanup` - Clean up idle sessions
- `/clear` - Clear the screen
- `/config` - Show current configuration
- `/history` - Show recent command history

## Shortcuts

- `py: <code>` → Execute Python persistent
- `js: <code>` → Execute JavaScript persistent
- `bash: <cmd>` → Execute Bash command
- `file: <path>` → Read file
- `save: <path>` → Write file

## Multi-line Input

Press Enter twice to submit multi-line queries:

```bash
You: Execute Python persistent:
import pandas as pd
df = pd.read_csv('data.csv')
print(df.head())

[Enter]
[Enter]  # Submit
```

## Examples

### Python Persistent Execution
```bash
You: py: x = 42; print(x)
Agent: 42

You: py: print(x * 2)
Agent: 84
```

### File Operations
```bash
You: file: data.csv
Agent: [CSV content displayed]

You: save: output.txt with content 'Hello World'
Agent: ✓ File written successfully
```

### Session Management
```bash
You: /session list
Agent: Active sessions:
- default (Python kernel, uptime: 5m)
- analysis (Python kernel, uptime: 2m)

You: /session kill analysis
Agent: ✓ Killed session 'analysis'
```

### Multi-language Execution
```bash
You: py: x = 42
You: js: const y = 100; console.log(y)
You: bash: echo "Hello from bash"
```

## Configuration

The CLI can be configured via `config/cli_config.yaml`:

```yaml
cli:
  color_scheme: "default"  # or "dark", "light"
  show_reasoning: true     # Show agent's thinking process
  auto_save_history: true
  max_history_lines: 1000
  default_session_id: "default"
  streaming_enabled: false  # Enable when agent supports it

models:
  free_model: "nex-agi/deepseek-v3.1-nex-n1:free"
  paid_model: "x-ai/grok-4-fast"
  switch_threshold: "complex"  # or "simple", "medium"
```

## Command History

- Up/Down arrows navigate through command history
- History is automatically saved to `~/.daagent_history`
- Use `/history` to view recent commands

## Error Handling

The CLI includes comprehensive error handling:

- **Timeout errors**: Queries that take too long
- **Network errors**: Connection issues
- **Dependency errors**: Missing required packages
- **Unexpected errors**: Logged to `error.log`

## Advanced Features

### Model Selection
```bash
# Use free models (default in dev mode)
python main.py --dev-mode

# Use paid models
python main.py --prod-mode

# Force specific model
python main.py --model x-ai/grok-4-fast
```

### Provider Selection
```bash
# Use different API providers
python main.py --provider openrouter
python main.py --provider huggingface
```

### Performance Options
```bash
# Disable optimizations for debugging
python main.py --no-optimize

# Disable MCP integration
python main.py --no-mcp

# Clear response cache
python main.py --clear-cache
```

## Troubleshooting

### Common Issues

**"Missing dependencies"**
```bash
pip install -r requirements.txt
```

**"Configuration Error"**
- Check your `.env` file has required API keys
- Verify `config/cli_config.yaml` syntax

**"Network error"**
- Check internet connection
- Verify API keys are valid

**Command history not working**
- On Windows, ensure `pyreadline3` is installed
- History file: `~/.daagent_history`

### Debug Mode
```bash
# Show full error details
python main.py --debug "your query"
```

## Architecture

The CLI wraps the `UnifiedAgent` class with:

- **Command parsing**: argparse for CLI options
- **Interactive loop**: Rich console for colored output
- **History management**: readline for command history
- **Configuration**: YAML-based settings
- **Error handling**: Comprehensive exception catching
- **Tool discovery**: Auto-registration from `tools/native/`

## Future Enhancements

- Streaming output (when agent supports it)
- Web UI mode (`--web` flag)
- Batch processing (`--file queries.txt`)
- Export to JSON/CSV (`--export results.json`)
- Plugin system for custom commands