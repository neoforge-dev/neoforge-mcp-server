#!/usr/bin/env python3
"""Check for missing functions in server.py that are referenced in tests."""

import os
import sys
import inspect
import importlib
import glob
import importlib.util
from types import ModuleType

# Add parent dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def get_functions_from_file(file_path: str) -> set:
    """Extract all function names from a Python file without executing it."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Simple approach: look for function definitions
    functions = set()
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('def ') and '(' in line:
            # Extract function name
            func_name = line[4:line.find('(')].strip()
            if not func_name.startswith('_'):
                functions.add(func_name)
        
        # Also look for @mcp.tool() decorator functions
        if '@mcp.tool()' in line:
            # The next line should be a function definition
            next_line_idx = lines.index(line) + 1
            if next_line_idx < len(lines):
                next_line = lines[next_line_idx].strip()
                if next_line.startswith('def ') and '(' in next_line:
                    func_name = next_line[4:next_line.find('(')].strip()
                    if not func_name.startswith('_'):
                        functions.add(func_name)
    
    return functions

def get_referenced_functions_from_file(file_path: str) -> set:
    """Extract function references to server module from a test file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Simple approach: look for "server.function_name" patterns
    # This is not perfect but should work for our test files
    references = set()
    lines = content.split('\n')
    for line in lines:
        if 'server.' in line:
            parts = line.split('server.')
            for part in parts[1:]:
                # Extract the function name (up to the first non-identifier character)
                func_name = ''
                for char in part:
                    if char.isalnum() or char == '_':
                        func_name += char
                    else:
                        break
                if func_name:
                    references.add(func_name)
    
    return references

def main():
    """Main function to check missing functions."""
    # Get all functions defined in server.py
    server_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server.py'))
    defined_functions = get_functions_from_file(server_file)
    
    # Get all functions referenced in test files
    test_files = glob.glob(os.path.join(os.path.dirname(__file__), 'test_*.py'))
    referenced_functions = set()
    
    for test_file in test_files:
        referenced_functions.update(get_referenced_functions_from_file(test_file))
    
    # Find missing functions
    missing_functions = referenced_functions - defined_functions
    
    if missing_functions:
        print("Missing functions in server.py that are referenced in tests:")
        for func in sorted(missing_functions):
            print(f"- {func}")
    else:
        print("No missing functions found. All referenced functions are defined in server.py")
    
    # Also show what files reference each missing function
    if missing_functions:
        print("\nFiles referencing missing functions:")
        for func in sorted(missing_functions):
            print(f"\n{func}:")
            for test_file in test_files:
                if func in get_referenced_functions_from_file(test_file):
                    print(f"  - {os.path.basename(test_file)}")

if __name__ == "__main__":
    main() 