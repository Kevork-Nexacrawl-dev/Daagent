# Daagent - General-Purpose AI Agent

Daagent is a powerful, extensible AI agent system built for productivity and automation. It features dynamic model selection, prompt layering, and a comprehensive tool ecosystem.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd daagent

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Basic Usage

```bash
# Start interactive CLI
python main.py

# Single query mode
python main.py "Execute Python: print('Hello World')"

# List available tools
python main.py --list-tools
```

## 📋 Features

### Core Capabilities
- **Dynamic Model Selection**: Automatically chooses the best AI model for each task
- **Tool Calling**: 90+ tools for code execution, file operations, web search, and more
- **Prompt Layering**: Customizable behavior through layered prompt system
- **Session Management**: Persistent execution environments for complex workflows
- **Multi-language Support**: Python, JavaScript, Bash, PowerShell, SQL, Docker

### CLI Interface
- **Interactive Mode**: REPL-style interface with command history
- **Multi-line Input**: Press Enter twice to submit multi-line queries
- **Shortcuts**: Quick commands like `py:`, `js:`, `file:`
- **Session Commands**: Manage persistent execution sessions
- **Rich Output**: Colored, formatted responses with Markdown support

## 🛠️ CLI Usage

### Interactive Mode

```bash
python main.py

Daagent CLI v2.0
Type your query, 'help' for commands, 'exit' to quit

You: Execute Python persistent: x = 42; print(x)
Agent: 42

You: py: print(x * 2)
Agent: 84
```

### Commands

- `/help` - Show help message
- `/reset` - Clear conversation history
- `/exit` - Exit the CLI
- `/list-tools` - List all available tools
- `/session list` - List active sessions
- `/session info <id>` - Show session details
- `/session kill <id>` - Terminate session
- `/clear` - Clear the screen
- `/config` - Show current configuration
- `/history` - Show recent command history

### Shortcuts

- `py: <code>` → Execute Python persistent
- `js: <code>` → Execute JavaScript persistent
- `bash: <cmd>` → Execute Bash command
- `file: <path>` → Read file
- `save: <path>` → Write file

### Multi-line Input

```bash
You: Execute Python persistent:
import pandas as pd
df = pd.read_csv('data.csv')
print(df.head())

[Enter]
[Enter]  # Submit
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Required
OPENROUTER_API_KEY=your_key_here

# Optional
DEV_MODE=true
PROVIDER=openrouter
LOG_LEVEL=INFO
```

### CLI Configuration (config/cli_config.yaml)

```yaml
cli:
  color_scheme: "default"
  show_reasoning: true
  auto_save_history: true
  max_history_lines: 1000
  default_session_id: "default"
  streaming_enabled: false

models:
  free_model: "nex-agi/deepseek-v3.1-nex-n1:free"
  paid_model: "x-ai/grok-4-fast"
  switch_threshold: "complex"
```

## 🏗️ Architecture

### Core Components

- **`agent/core.py`**: UnifiedAgent with ReAct loop and tool calling
- **`agent/config.py`**: Dynamic model selection and configuration
- **`agent/tool_registry.py`**: Auto-discovery of tools from `tools/native/`
- **`tools/native/`**: 37+ native tools for various operations
- **`tools/mcp/`**: MCP (Model Context Protocol) bridge for external tools

### Tool Categories

- **Code Execution**: Python, JavaScript, Bash, PowerShell, SQL, Docker
- **File Operations**: Read/write files, directory management, file conversion
- **Session Management**: Persistent execution environments
- **Web Operations**: Search, scraping, API calls
- **Data Processing**: CSV/Excel/JSON manipulation
- **System Tools**: Git, filesystem, compression

## 📚 Examples

### Data Analysis Workflow

```bash
# Load and analyze data
You: py: import pandas as pd; df = pd.read_csv('sales.csv')
You: py: print(df.describe())
You: py: df.groupby('region').sum()
```

### Multi-language Development

```bash
You: py: data = {'name': 'Alice', 'age': 30}
You: js: const jsonData = JSON.stringify(data); console.log(jsonData)
You: bash: echo "Data processed successfully"
```

### File Operations

```bash
You: file: config.yaml
You: save: output.txt with content 'Analysis complete'
```

### Session Management

```bash
You: /session list
You: /session info analysis_session
You: /session cleanup
```

## 🔍 Advanced Usage

### Model Selection

```bash
# Force specific model
python main.py --model x-ai/grok-4-fast "complex query"

# Use development mode (free models)
python main.py --dev-mode

# Use production mode (paid models)
python main.py --prod-mode
```

### Performance Optimization

```bash
# Disable optimizations for debugging
python main.py --no-optimize

# Clear response cache
python main.py --clear-cache
```

### Provider Selection

```bash
# Use different API providers
python main.py --provider openrouter
python main.py --provider huggingface
```

## 🐛 Troubleshooting

### Common Issues

**"Missing dependencies"**
```bash
pip install -r requirements.txt
```

**"Configuration Error"**
- Check `.env` file has required API keys
- Verify `config/cli_config.yaml` syntax

**"Network error"**
- Check internet connection
- Verify API keys are valid

**Command history not working**
- On Windows: `pip install pyreadline3`
- On Unix: Built-in readline support

### Debug Mode

```bash
# Show full error details
python main.py --debug "your query"
```

## 📖 Documentation

- **[CLI Usage Guide](docs/CLI_USAGE.md)**: Comprehensive CLI documentation
- **[API Reference](docs/API.md)**: Agent and tool APIs
- **[Tool Development](docs/TOOL_DEVELOPMENT.md)**: Creating custom tools
- **[Configuration](docs/CONFIGURATION.md)**: Advanced configuration options

## 🤝 Contributing

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_basic.py -v
```

### Adding Tools

1. Create `tools/native/your_tool.py`
2. Implement required functions and schemas
3. Add tests in `tests/test_your_tool.py`
4. Update documentation

### Code Standards

- Type hints on all functions
- Google-style docstrings
- Comprehensive error handling
- Unit tests for all functionality

## 📄 License

[License information]

## 🙏 Acknowledgments

- Built on the [AGENTS.md](AGENTS.md) philosophy
- Powered by OpenRouter, Anthropic, and other AI providers
- Tool ecosystem inspired by various open-source projects

---

**Ready to build something amazing?** 🚀

```bash
python main.py
```

For more information, see the [full documentation](docs/) or join our community.
