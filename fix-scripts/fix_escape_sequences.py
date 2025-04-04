#!/usr/bin/env python3
"""
Fix invalid escape sequences in Python files.

This script replaces invalid escape sequences like '\\.' and '\\(' with their
proper escaped versions '\\\\.' and '\\\\(' in Swift code snippets within test files.
"""

import re
import sys
import argparse
from pathlib import Path


def fix_escape_sequences(content):
    """
    Fix the escape sequences in the content.
    
    Args:
        content: The content to fix
        
    Returns:
        The fixed content
    """
    # First, normalize any triple backslashes to a single backslash
    content = re.sub(r'\\\\\\(?=[.(])', r'\\', content)
    
    # Replace environment escape sequences (e.g., "\.colorScheme")
    content = re.sub(r'@Environment\(\\\.([a-zA-Z]+)\)', r'@Environment(\\\\.\1)', content)
    
    # Replace string interpolation escape sequences with more specific patterns
    patterns = [
        r'print\([^)]*\\(?=\([^)]*\))',
        r'Text\([^)]*\\(?=\([^)]*\))',
        r'to \\(?=\([^)]*\))',
        r'from \\(?=\([^)]*\))',
        r'time: \\(?=\([^)]*\))',
        r'Item \\(?=\([^)]*\))',
        r'Width: \\(?=\([^)]*\))',
        r'Height: \\(?=\([^)]*\))',
        r'Value: \\(?=\([^)]*\))',
        r'Current \\(?=\([^)]*\))',
    ]
    
    # Apply each pattern
    for pattern in patterns:
        content = re.sub(pattern, lambda m: m.group(0).replace('\\', '\\\\'), content)
    
    # Also catch any remaining cases of \( that aren't already escaped
    content = re.sub(r'([^\\])\\(?=\([^)]*\))', r'\1\\\\', content)
    
    # Fix ForEach with id: \.self syntax
    content = re.sub(r'ForEach\(([^,]+),\s*id:\s*\\\.self', r'ForEach(\1, id: \\\\.self', content)
    content = re.sub(r'Chart\(([^,]+),\s*id:\s*\\\.self', r'Chart(\1, id: \\\\.self', content)
    
    return content


def process_file(file_path):
    """
    Process a single file to fix escape sequences.
    
    Args:
        file_path: Path to the file to process
    """
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File '{file_path}' does not exist.")
        return False
    
    try:
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Skip fixing escape sequences in test_error_handling function
        if 'test_error_handling' in content:
            # Extract the test_error_handling function
            error_test_pattern = r'def test_error_handling.*?def'
            error_test_match = re.search(error_test_pattern, content, re.DOTALL)
            if error_test_match:
                error_test = error_test_match.group(0)
                # Remove the error test from content before fixing
                content = content.replace(error_test, '')
                # Fix escape sequences in the rest of the content
                content = fix_escape_sequences(content)
                # Restore the error test
                content = content.replace('def test_complex_swiftui_view', error_test + 'def test_complex_swiftui_view')
        else:
            content = fix_escape_sequences(content)
        
        # If the content was changed, write it back to the file
        if content != content:
            with open(path, 'w', encoding='utf-8') as file:
                file.write(content)
            print(f"Fixed escape sequences in '{file_path}'.")
            return True
        else:
            print(f"No escape sequences to fix in '{file_path}'.")
            return False
    
    except Exception as e:
        print(f"Error processing file '{file_path}': {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Fix invalid escape sequences in Python files.")
    parser.add_argument('files', nargs='+', help="Files to process")
    args = parser.parse_args()
    
    success_count = 0
    for file_path in args.files:
        if process_file(file_path):
            success_count += 1
    
    print(f"Fixed escape sequences in {success_count} out of {len(args.files)} files.")
    return 0


if __name__ == '__main__':
    sys.exit(main()) 