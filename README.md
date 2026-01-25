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

# Context Window Management
MAX_CONTEXT_TOKENS=32000          # Total context window size in tokens
CONTEXT_RESERVE_TOKENS=4000       # Tokens reserved for AI response generation
ENABLE_CONTEXT_SUMMARIZATION=true # Enable automatic context summarization
CONTEXT_SUMMARY_TRIGGER_RATIO=0.8 # Ratio of context used before triggering summarization (0.0-1.0)
```

#### Context Window Management

Daagent includes advanced context window management to optimize performance and prevent token limit errors:

- **`MAX_CONTEXT_TOKENS`**: Sets the total context window size in tokens. This should match your model's maximum context length (e.g., 32000 for most models, 128000 for larger ones).
- **`CONTEXT_RESERVE_TOKENS`**: Reserves tokens for the AI's response generation. Prevents the context from filling up completely, leaving room for meaningful replies.
- **`ENABLE_CONTEXT_SUMMARIZATION`**: When enabled, automatically summarizes older conversation history when approaching context limits to maintain continuity.
- **`CONTEXT_SUMMARY_TRIGGER_RATIO`**: Defines when summarization kicks in as a ratio of total context used (0.8 = 80%). Lower values trigger earlier summarization for better performance.

**Recommended Settings:**
- For 32K models: `MAX_CONTEXT_TOKENS=32000`, `CONTEXT_RESERVE_TOKENS=4000`
- For 128K models: `MAX_CONTEXT_TOKENS=128000`, `CONTEXT_RESERVE_TOKENS=8000`
- For memory-intensive tasks: Lower `CONTEXT_SUMMARY_TRIGGER_RATIO` to 0.7

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

## 🏠 Using Ollama as Local Provider

### Prerequisites

To use Ollama as a local LLM provider, you need to:

1. **Install Ollama**: Download and install Ollama from [ollama.ai](https://ollama.ai). Follow the installation instructions for your operating system.

2. **Pull a Model**: After installation, pull a model you want to use, e.g., Llama 2 or Mistral:
   ```bash
   ollama pull llama2
   ```

3. **Start the Ollama Server**: Run the Ollama server in the background:
   ```bash
   ollama serve
   ```

### Configuration

Set the following environment variables in your `.env` file:

```bash
# Set provider to ollama
PROVIDER=ollama

# Specify the model name (must match what you pulled)
OLLAMA_MODEL=llama2

# Optional: Set the Ollama API base URL (default is http://localhost:11434)
OLLAMA_BASE_URL=http://localhost:11434
```

### Usage Examples

Once configured, use Daagent with Ollama just like other providers:

```bash
# Interactive mode with Ollama
python main.py

# Single query
python main.py "Summarize this text: [your text]"

# Force Ollama provider
python main.py --provider ollama "Generate a Python function for data analysis"
```

### Benefits of Local LLMs

- **Privacy**: All data stays on your local machine
- **Cost**: No API costs or rate limits
- **Offline**: Works without internet connection
- **Customization**: Fine-tune models for specific tasks
- **Speed**: Lower latency for local inference

### Troubleshooting

**"Connection refused" error**
- Ensure Ollama server is running: `ollama serve`
- Check if the model is pulled: `ollama list`
- Verify OLLAMA_BASE_URL in .env

**"Model not found" error**
- Pull the model first: `ollama pull <model_name>`
- Confirm the model name in OLLAMA_MODEL matches

**Slow performance**
- Use smaller models for faster inference
- Ensure sufficient RAM (models need 4-16GB+)
- Close other resource-intensive applications

**Permission issues on Windows/Linux**
- Run Ollama with appropriate permissions
- Check firewall settings for local connections

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
