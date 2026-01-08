#!/usr/bin/env python3
"""
Daagent CLI - Interactive AI Agent Interface
"""
import sys
import argparse
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich import print as rprint
import yaml

# Handle readline import (not available on Windows by default)
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    try:
        import pyreadline3 as readline
        READLINE_AVAILABLE = True
    except ImportError:
        READLINE_AVAILABLE = False
        readline = None  # Dummy

from agent.core import UnifiedAgent
from agent.config import Config

console = Console()

# CLI Configuration
HISTORY_FILE = Path.home() / ".daagent_history"
CONFIG_FILE = Path("config/cli_config.yaml")

# Shortcuts for quick commands
SHORTCUTS = {
    "py:": "Execute Python persistent:",
    "js:": "Execute JavaScript persistent:",
    "bash:": "Execute Bash:",
    "file:": "Read file:",
    "save:": "Write file:"
}


def load_config() -> dict:
    """
    Load CLI configuration from file.
    
    Returns:
        Configuration dictionary
    """
    default_config = {
        "cli": {
            "color_scheme": "default",
            "show_reasoning": True,
            "auto_save_history": True,
            "max_history_lines": 1000,
            "default_session_id": "default",
            "streaming_enabled": False
        },
        "models": {
            "free_model": "deepseek/deepseek-chat",
            "paid_model": "grok-fast",
            "switch_threshold": "complex"
        }
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_config = yaml.safe_load(f)
                # Merge with defaults
                if user_config:
                    default_config.update(user_config)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config file: {e}[/yellow]")
    
    return default_config


def check_dependencies() -> None:
    """
    Check if all required dependencies are installed.
    Exits with error if any are missing.
    """
    required = {
        "openai": "OpenAI Python SDK",
        "rich": "Terminal UI library",
        "yaml": "YAML configuration support",
        "jupyter_client": "Jupyter kernel support",
        "psutil": "Process management"
    }
    
    missing = []
    for package, description in required.items():
        try:
            __import__(package)
        except ImportError:
            missing.append(f"  - {package} ({description})")
    
    if missing:
        console.print("[red]Missing dependencies:[/red]")
        for pkg in missing:
            console.print(pkg)
        console.print("\n[yellow]Install with: pip install -r requirements.txt[/yellow]")
        sys.exit(1)


def load_history() -> None:
    """Load command history from file."""
    if not READLINE_AVAILABLE:
        return
    if HISTORY_FILE.exists():
        try:
            readline.read_history_file(str(HISTORY_FILE))
        except Exception:
            pass  # Ignore history loading errors


def save_history() -> None:
    """Save command history to file."""
    if not READLINE_AVAILABLE:
        return
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        readline.write_history_file(str(HISTORY_FILE))
    except Exception:
        pass  # Ignore history saving errors


def expand_shortcuts(user_input: str) -> str:
    """
    Expand shortcuts to full commands.
    
    Examples:
    - "py: print(42)" → "Execute Python persistent: print(42)"
    - "file: data.csv" → "Read file: data.csv"
    """
    for shortcut, expansion in SHORTCUTS.items():
        if user_input.startswith(shortcut):
            return user_input.replace(shortcut, expansion, 1)
    return user_input


def safe_agent_run(agent: UnifiedAgent, query: str) -> Optional[str]:
    """
    Execute agent query with comprehensive error handling.
    
    Args:
        agent: The agent instance
        query: The query to execute
        
    Returns:
        Response string or None if error
    """
    try:
        return agent.run(query)
    
    except TimeoutError:
        console.print("[red]⏱️  Query timed out. Try a simpler operation.[/red]")
        return None
    
    except ImportError as e:
        console.print(f"[red]📦 Missing dependency: {e}[/red]")
        console.print("[yellow]💡 Try: pip install -r requirements.txt[/yellow]")
        return None
    
    except ConnectionError:
        console.print("[red]🌐 Network error. Check your internet connection.[/red]")
        return None
    
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {str(e)}[/red]")
        console.print("[dim]Stack trace saved to error.log[/dim]")
        
        # Log full error
        import traceback
        try:
            with open("error.log", "a") as f:
                f.write(f"\n\n=== Error at {datetime.now()} ===\n")
                f.write(f"Query: {query}\n")
                f.write(traceback.format_exc())
        except Exception:
            pass  # Ignore logging errors
        
        return None

# CLI Configuration
HISTORY_FILE = Path.home() / ".daagent_history"
CONFIG_FILE = Path("config/cli_config.yaml")

# Shortcuts for quick commands
SHORTCUTS = {
    "py:": "Execute Python persistent:",
    "js:": "Execute JavaScript persistent:",
    "bash:": "Execute Bash:",
    "file:": "Read file:",
    "save:": "Write file:"
}


def main():
    # Load configuration
    config = load_config()
    
    # Check dependencies
    check_dependencies()
    
    parser = argparse.ArgumentParser(
        description="Daagent - General-purpose AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Start interactive mode
  python main.py "search for AI news"     # Single query
  python main.py --dev-mode               # Force dev mode
  python main.py --model grok-4-fast      # Use specific model
  python main.py --provider huggingface   # Use HuggingFace provider
        """
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Single query to execute (starts interactive mode if not provided)"
    )
    parser.add_argument(
        "--dev-mode",
        action="store_true",
        help="Force development mode (free models)"
    )
    parser.add_argument(
        "--prod-mode",
        action="store_true",
        help="Force production mode (paid models)"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Force specific model (bypasses task detection)"
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openrouter", "huggingface", "together"],
        help="Override API provider (default: from .env PROVIDER setting)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        help="Override maximum iterations (default: 25)"
    )
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Disable MCP warehouse integration"
    )
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Disable all latency optimizations"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear response cache and exit"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Hide tool call details"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug information on errors"
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools and exit"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information and exit"
    )

    args = parser.parse_args()

    # Handle version
    if args.version:
        console.print("[bold cyan]Daagent CLI v2.0[/bold cyan]")
        console.print("Built on general-purpose AI agent framework")
        sys.exit(0)

    # Apply overrides from CLI args
    if args.dev_mode:
        Config.DEV_MODE = True
    if args.prod_mode:
        Config.DEV_MODE = False
    if args.model:
        Config.OVERRIDE_MODEL = args.model
    if args.provider:
        Config.OVERRIDE_PROVIDER = args.provider
    if args.max_iterations:
        Config.MAX_ITERATIONS = args.max_iterations
    if args.no_mcp:
        Config.ENABLE_MCP = False
    if args.no_optimize:
        Config.ENABLE_QUERY_CLASSIFICATION = False
        Config.ENABLE_RESPONSE_CACHE = False
        Config.ENABLE_LAZY_TOOLS = False

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        sys.exit(1)

    # Handle cache clearing
    if args.clear_cache:
        from agent.response_cache import ResponseCache
        cache = ResponseCache()
        cache.clear()
        console.print("[green]Response cache cleared[/green]")
        sys.exit(0)

    # Initialize agent
    console.print("[blue]Initializing Daagent...[/blue]")
    agent = UnifiedAgent()
    
    # Handle list tools
    if args.list_tools:
        list_tools(agent.tool_registry, console)
        sys.exit(0)

    # Check if single query or interactive mode
    if args.query:
        # Single query mode
        response = safe_agent_run(agent, args.query)
        if response:
            console.print(Markdown(response))
        sys.exit(0)

    # Interactive mode
    interactive_mode(agent, args, config)


def interactive_mode(agent: UnifiedAgent, args: argparse.Namespace, config: dict) -> None:
    """
    Run interactive chat session.

    Args:
        agent: The initialized agent
        args: Parsed command line arguments
        config: CLI configuration
    """
    # Load command history
    load_history()
    
    # Check if input is from a pipe (non-interactive)
    is_piped_input = not sys.stdin.isatty()
    
    # Show welcome banner (only for interactive sessions)
    if not is_piped_input:
        console.print(Panel.fit(
            "[bold green]Daagent - AI Agent[/bold green]\n"
            f"Mode: {'DEV' if Config.DEV_MODE else 'PROD'}\n"
            f"Tools: {len(agent.available_tools)} available\n"
            "Commands: /help, /reset, /exit, /list-tools, /sessions",
            border_style="green"
        ))

    try:
        while True:
            try:
                # Get user input (handle multi-line)
                user_input = get_multiline_input()
                
                # If piped input and we got EOF, exit
                if is_piped_input and user_input == "":
                    break
                
                # Expand shortcuts
                user_input = expand_shortcuts(user_input)

                # Handle commands
                if user_input.startswith('/'):
                    if not handle_command(user_input, agent, config):
                        break  # Exit requested
                    continue

                # Execute query with visual feedback
                with console.status("[bold yellow]Agent thinking..."):
                    response = safe_agent_run(agent, user_input)

                if response:
                    # Display response
                    console.print(Panel(
                        Markdown(response),
                        title="[bold green]Agent",
                        border_style="green"
                    ))
                else:
                    # Error already displayed by safe_agent_run
                    pass
                
                # If piped input, exit after first response
                if is_piped_input:
                    break

            except KeyboardInterrupt:
                if not is_piped_input:
                    console.print("\n[yellow]Use /exit to quit properly[/yellow]")
                break
            except Exception as e:
                if args.debug:
                    raise
                console.print(f"[red]Error:[/red] {e}")
                if is_piped_input:
                    break
    finally:
        # Save command history on exit (only for interactive sessions)
        if not is_piped_input and config["cli"]["auto_save_history"]:
            save_history()


def get_multiline_input() -> str:
    """
    Get user input with multi-line support.
    Press Enter twice to submit (or immediately for commands).
    
    Returns:
        The complete user input, or empty string on EOF for piped input
    """
    # Check if input is from a pipe
    is_piped = not sys.stdin.isatty()
    
    if is_piped:
        # For piped input, read all available input at once
        try:
            lines = sys.stdin.readlines()
            if not lines:
                return ""
            # Remove trailing newlines and join
            return "".join(line.rstrip('\r\n') + '\n' for line in lines).rstrip('\n')
        except:
            return ""
    
    # Interactive mode - show prompt and handle multi-line
    console.print("[bold cyan]You:[/bold cyan] ", end="")
    lines = []
    consecutive_empty = 0
    
    while True:
        try:
            line = input()
            
            # Commands are single-line - submit immediately
            if line.startswith('/'):
                return line
            
            # Track consecutive empty lines
            if line.strip() == "":
                consecutive_empty += 1
                if consecutive_empty >= 2 and lines:
                    # Two consecutive empty lines after content = submit
                    break
            else:
                consecutive_empty = 0
            
            lines.append(line)
            
        except EOFError:
            # Ctrl+D - submit current input
            break
    
    return "\n".join(lines)


def handle_command(command: str, agent: UnifiedAgent, config: dict) -> bool:
    """
    Handle special commands.

    Args:
        command: The command string
        agent: The agent instance
        config: CLI configuration

    Returns:
        False if should exit, True otherwise
    """
    command = command.strip().lower()
    
    if command in ['/exit', '/quit', '/q']:
        console.print("[yellow]Goodbye![/yellow]")
        return False
        
    elif command == '/reset':
        agent.reset_conversation()
        console.print("[yellow]Conversation history cleared[/yellow]")
        
    elif command in ['/help', '/h', '/?']:
        show_help(console)
        
    elif command in ['/list-tools', '/tools']:
        list_tools(agent.tool_registry, console)
        
    elif command.startswith('/session'):
        handle_session_command(command, agent)
        
    elif command == '/clear':
        console.clear()
        
    elif command == '/config':
        show_config(config)
        
    elif command == '/history':
        show_command_history()
        
    else:
        console.print(f"[red]Unknown command:[/red] {command}")
        console.print("[dim]Type /help for available commands[/dim]")

    return True


def handle_session_command(command: str, agent: UnifiedAgent) -> None:
    """
    Handle session management commands.
    
    Commands:
    - /session list          : List all active sessions
    - /session info <id>     : Show detailed session info
    - /session kill <id>     : Terminate a session
    - /session cleanup       : Clean up idle sessions
    """
    parts = command.split()
    
    if len(parts) < 2:
        console.print("[red]Usage: /session [list|info|kill|cleanup] [session_id][/red]")
        return
    
    action = parts[1].lower()
    
    try:
        if action == "list":
            # Call list_sessions tool
            response = safe_agent_run(agent, "List all active sessions")
            if response:
                console.print(Markdown(response))
    
        elif action == "info" and len(parts) >= 3:
            session_id = parts[2]
            response = safe_agent_run(agent, f"Get session info for: {session_id}")
            if response:
                console.print(Markdown(response))
    
        elif action == "kill" and len(parts) >= 3:
            session_id = parts[2]
            response = safe_agent_run(agent, f"Kill session: {session_id}")
            if response:
                console.print(Markdown(response))
    
        elif action == "cleanup":
            response = safe_agent_run(agent, "Cleanup idle sessions")
            if response:
                console.print(Markdown(response))
    
        else:
            console.print("[red]Unknown session command. Use: list, info, kill, cleanup[/red]")
            
    except Exception as e:
        console.print(f"[red]Session command failed: {e}[/red]")


def show_help(console: Console) -> None:
    """Display help information."""
    help_text = """
**Available Commands:**

- `/help` or `/h` - Show this help message
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

**Shortcuts:**

- `py: <code>` → Execute Python persistent
- `js: <code>` → Execute JavaScript persistent
- `bash: <cmd>` → Execute Bash command
- `file: <path>` → Read file
- `save: <path>` → Write file

**Multi-line Input:**

Press Enter twice to submit multi-line queries.

**Examples:**

- `py: x = 42; print(x)`
- `file: data.csv`
- `/session list`
- Long queries spanning multiple lines
"""
    console.print(Markdown(help_text))


def list_tools(registry, console: Console) -> None:
    """List all discovered tools."""
    try:
        tools = registry.list_tools()
        
        console.print(f"\n[bold cyan]Available Tools ({len(tools)}):[/bold cyan]\n")
        
        # Group tools by category
        categories = {
            "Code Execution": [],
            "File Operations": [],
            "Session Management": [],
            "Other": []
        }
        
        for tool in sorted(tools):
            tool_lower = tool.lower()
            if any(keyword in tool_lower for keyword in ["execute", "python", "javascript", "bash", "powershell", "sql", "docker"]):
                categories["Code Execution"].append(tool)
            elif any(keyword in tool_lower for keyword in ["file", "read", "write", "directory"]):
                categories["File Operations"].append(tool)
            elif "session" in tool_lower:
                categories["Session Management"].append(tool)
            else:
                categories["Other"].append(tool)
        
        for category, tool_list in categories.items():
            if tool_list:
                console.print(f"[yellow]{category}:[/yellow]")
                for tool in tool_list:
                    console.print(f"  - {tool}")
                console.print()
    except Exception as e:
        console.print(f"[red]Error listing tools: {e}[/red]")


def show_config(config: dict) -> None:
    """Show current CLI configuration."""
    console.print("\n[bold cyan]CLI Configuration:[/bold cyan]")
    for section, settings in config.items():
        console.print(f"\n[yellow]{section.upper()}:[/yellow]")
        if isinstance(settings, dict):
            for key, value in settings.items():
                console.print(f"  {key}: {value}")
        else:
            console.print(f"  {settings}")


def show_command_history() -> None:
    """Show recent command history."""
    if not READLINE_AVAILABLE:
        console.print("[dim]Command history not available (readline not installed)[/dim]")
        return
        
    try:
        # Get history from readline
        history_length = readline.get_current_history_length()
        if history_length == 0:
            console.print("[dim]No command history available[/dim]")
            return
            
        console.print(f"\n[bold cyan]Recent Commands ({min(10, history_length)}):[/bold cyan]")
        start = max(1, history_length - 10)
        for i in range(start, history_length + 1):
            cmd = readline.get_history_item(i)
            if cmd:
                console.print(f"{i:3d}: {cmd}")
    except Exception as e:
        console.print(f"[red]Error showing history: {e}[/red]")


if __name__ == "__main__":
    main()
