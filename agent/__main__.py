#!/usr/bin/env python3
"""
Agent module entry point for web API.
"""
import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import main

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('query', nargs='?', help='User query')
    parser.add_argument('--model', default='auto', help='Model selection')
    
    args = parser.parse_args()
    
    # Pass model to main (will update main.py to accept this)
    if args.query:
        sys.argv = ['agent', args.query, '--model', args.model]
    
    main()