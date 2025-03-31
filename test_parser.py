import os
from server.code_understanding.language_adapters import JavaScriptParserAdapter

def print_node(node, level=0):
    """Print a tree-sitter node and its children."""
    indent = '  ' * level
    print(f"{indent}{node.type}: {node.text.decode('utf-8')}")
    for child in node.children:
        print_node(child, level + 1)

def test_parser():
    # Read the test file
    with open('test.js', 'r') as f:
        code = f.read()
    
    # Create parser instance
    parser = JavaScriptParserAdapter()
    
    # Parse the code and get the raw tree
    tree = parser.parser.parse(bytes(code, 'utf-8'))
    print("\nTree structure:")
    print_node(tree.root_node)
    
    # Parse the code
    result = parser.parse(code)
    
    # Print results
    print("\nImports:")
    for imp in result.features['imports']:
        print(f"- {imp}")
    
    print("\nFunctions:")
    for func in result.features['functions']:
        print(f"- {func}")
    
    print("\nClasses:")
    for cls in result.features['classes']:
        print(f"- {cls}")
    
    print("\nVariables:")
    for var in result.features['variables']:
        print(f"- {var}")
    
    print("\nExports:")
    for exp in result.features['exports']:
        print(f"- {exp}")
    
    if result.features['has_errors']:
        print("\nErrors:")
        for error in result.features['error_details']:
            print(f"- {error}")

if __name__ == '__main__':
    test_parser() 