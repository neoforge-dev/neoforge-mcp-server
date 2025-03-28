import os
import subprocess

def build_language():
    """Build the tree-sitter language bindings for Python."""
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create the build directory if it doesn't exist
    build_dir = os.path.join(current_dir, 'build')
    os.makedirs(build_dir, exist_ok=True)
    
    # Change to the tree-sitter-python directory
    python_grammar_dir = os.path.join(current_dir, 'vendor', 'tree-sitter-python')
    os.chdir(python_grammar_dir)
    
    # Run tree-sitter generate
    subprocess.run(['tree-sitter', 'generate'], check=True)
    
    # Run tree-sitter test
    subprocess.run(['tree-sitter', 'test'], check=True)
    
    # Build the shared library
    subprocess.run(['cc', '-fPIC', '-c', 'src/parser.c', '-I', 'src'], check=True)
    subprocess.run(['cc', '-fPIC', '-c', 'src/scanner.c', '-I', 'src'], check=True)
    subprocess.run(['cc', '-shared', '-o', os.path.join(current_dir, 'server', 'code_understanding', 'python.so'), 'parser.o', 'scanner.o'], check=True)
    
    print("Successfully built tree-sitter Python language bindings")

if __name__ == '__main__':
    build_language() 