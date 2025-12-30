#!/usr/bin/env python3
"""
Daagent CLI - Interactive AI Agent Interface
"""
import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich import print as rprint

from agent.core import UnifiedAgent
from agent.config import Config

console = Console()


def main():
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
        "--quiet",
        action="store_true",
        help="Hide tool call details"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug information on errors"
    )

    args = parser.parse_args()

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

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        sys.exit(1)

    # Initialize agent
    agent = UnifiedAgent()

    # Check if single query or interactive mode
    if args.query:
        # Single query mode
        response = agent.run(args.query)
        console.print(Markdown(response))
        sys.exit(0)

    # Interactive mode
    interactive_mode(agent, args)


def interactive_mode(agent: UnifiedAgent, args: argparse.Namespace) -> None:
    """
    Run interactive chat session.

    Args:
        agent: The initialized agent
        args: Parsed command line arguments
    """
    # Show welcome banner
    console.print(Panel.fit(
        "[bold green]Daagent - AI Agent[/bold green]\n"
        f"Mode: {'DEV' if Config.DEV_MODE else 'PROD'}\n"
        "Commands: /reset, /exit, /help",
        border_style="green"
    ))

    while True:
        try:
            # Get user input (handle multi-line)
            user_input = get_multiline_input()

            # Handle commands
            if user_input.startswith('/'):
                if not handle_command(user_input, agent):
                    break  # Exit requested
                continue

            # Execute query with visual feedback
            with console.status("[bold yellow]Agent thinking..."):
                response = agent.run(user_input)

            # Display response
            console.print(Panel(
                Markdown(response),
                title="[bold green]Agent",
                border_style="green"
            ))

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /exit to quit properly[/yellow]")
        except Exception as e:
            if args.debug:
                raise
            console.print(f"[red]Error:[/red] {e}")


def get_multiline_input() -> str:
    """
    Get user input with multi-line support.

    Returns:
        The complete user input
    """
    console.print("[bold cyan]You:[/bold cyan] ", end="")
    lines = []
    while True:
        try:
            line = input()

            # Commands are single-line - submit immediately
            if line.startswith('/'):
                return line

            # Empty line after content = submit
            if line == "" and lines:
                break

            lines.append(line)
        except EOFError:
            break

    return "\n".join(lines)


def handle_command(command: str, agent: UnifiedAgent) -> bool:
    """
    Handle special commands.

    Args:
        command: The command string
        agent: The agent instance

    Returns:
        False if should exit, True otherwise
    """
    command = command.strip().lower()
    if command in ['/exit', '/quit']:
        console.print("[yellow]Goodbye![/yellow]")
        return False
    elif command == '/reset':
        agent.reset_conversation()
        console.print("[yellow]Conversation history cleared[/yellow]")
    elif command == '/help':
        console.print("""
[bold]Commands:[/bold]
/reset - Clear conversation history
/exit  - Quit the program
/help  - Show this message
""")
    else:
        console.print(f"[red]Unknown command:[/red] {command}")

    return True


if __name__ == "__main__":
    main()
