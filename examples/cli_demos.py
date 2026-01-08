#!/usr/bin/env python3
"""
Daagent CLI Demo Script

This script demonstrates various CLI features and capabilities.
Run with: python examples/cli_demos.py
"""

import subprocess
import sys
import time
from pathlib import Path

def run_demo(name: str, description: str, commands: list):
    """Run a demo section."""
    print(f"\n{'='*60}")
    print(f"DEMO: {name}")
    print(f"{'='*60}")
    print(f"Description: {description}")
    print()

    for cmd in commands:
        print(f"$ {cmd}")
        try:
            # Handle Windows vs Unix differences
            if "|" in cmd and "head" in cmd:
                # Replace head with PowerShell equivalent
                cmd = cmd.replace(" | head -20", " | Select-Object -First 20")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                # Truncate long output
                output = result.stdout.strip()
                if len(output) > 500:
                    output = output[:500] + "... (truncated)"
                print(output)
            else:
                error_output = result.stderr.strip()
                if len(error_output) > 200:
                    error_output = error_output[:200] + "... (truncated)"
                print(f"Error: {error_output}")
        except subprocess.TimeoutExpired:
            print("Command timed out")
        except UnicodeDecodeError:
            print("Output contained non-ASCII characters")
        except Exception as e:
            print(f"Failed to run: {e}")
        print()
        time.sleep(1)  # Brief pause between commands

def main():
    print("Daagent CLI Demo Script")
    print("This will run various CLI commands to demonstrate features.")
    print("Make sure Daagent is properly configured before running.")
    print()

    # Check if main.py exists
    if not Path("main.py").exists():
        print("Error: main.py not found. Run from daagent root directory.")
        sys.exit(1)

    demos = [
        ("Basic CLI Launch", "Test basic CLI startup and help", [
            'python main.py --version',
            'python main.py --help'
        ]),

        ("Single Query Mode", "Test single query execution", [
            'python main.py "Execute Python: print(42)"'
        ]),

        ("Tool Listing", "List all available tools", [
            'python main.py --list-tools'
        ]),

        ("Configuration", "Show CLI configuration (requires interactive mode)", [
            'echo "Config command only available in interactive mode: /config"'
        ]),

        ("Interactive Commands", "Test various interactive commands (manual testing required)", [
            'echo "To test interactive mode, run: python main.py"',
            'echo "Then try commands like: /help, /list-tools, /config, /exit"'
        ]),

        ("Shortcuts", "Test command shortcuts (manual testing required)", [
            'echo "In interactive mode, try shortcuts like:"',
            'echo "  py: x = 42; print(x)"',
            'echo "  js: console.log(\'Hello\')"',
            'echo "  file: main.py (first few lines)"'
        ]),

        ("Session Management", "Test session commands (manual testing required)", [
            'echo "In interactive mode, try session commands:"',
            'echo "  /session list"',
            'echo "  /session info default"',
            'echo "  /session cleanup"'
        ]),

        ("Multi-line Input", "Test multi-line queries (manual testing required)", [
            'echo "In interactive mode, try multi-line input:"',
            'echo "Execute Python persistent:"',
            'echo "x = 42"',
            'echo "print(x)"',
            'echo ""',
            'echo "(then press Enter twice to submit)"'
        ]),

        ("Error Handling", "Test error scenarios", [
            'python main.py "Execute Python: import nonexistent_module" || echo "Expected error caught"',
            'echo "Timeout testing requires manual testing with long-running queries"'
        ])
    ]

    for name, description, commands in demos:
        run_demo(name, description, commands)

    print(f"\n{'='*60}")
    print("DEMO COMPLETE")
    print(f"{'='*60}")
    print()
    print("For full interactive testing:")
    print("  python main.py")
    print()
    print("For more examples, see docs/CLI_USAGE.md")

if __name__ == "__main__":
    main()