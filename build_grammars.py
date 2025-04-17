#!/usr/bin/env python3

import os
import subprocess
import sys
import platform
import shutil # Added for potentially removing incomplete clones
from pathlib import Path

# --- Grammar Configuration ---
GRAMMARS = {
    "javascript": {
        "repo": "https://github.com/tree-sitter/tree-sitter-javascript.git",
        "dir": "vendor/tree-sitter-javascript",
        "src_files": ["src/parser.c", "src/scanner.c"], # Explicit list for JS
        "has_grammar_js": True, # JS needs generation
    },
    "swift": {
        "repo": "https://codeberg.org/woolsweater/tree-sitter-swifter.git",
        "dir": "vendor/tree-sitter-swifter",
        # Let the script find parser.c (after generation) and scanner.c
        "src_files": ["src/parser.c", "src/scanner.c"], # Keep scanner.c explicit if needed
        "has_grammar_js": True, # Swift grammar also needs generation
    },
    # Add other languages here
}

BUILD_DIR = Path('server/code_understanding/build')
VENDOR_DIR = Path('vendor')

# Determine output library name based on OS
if platform.system() == "Windows":
    OUTPUT_LIB_NAME = "my-languages.dll"
    COMPILER = "gcc" # Or clang, or cl.exe if MSVC
elif platform.system() == "Darwin": # macOS
    OUTPUT_LIB_NAME = "my-languages.dylib"
    COMPILER = "clang" # Or gcc
else: # Linux/other Unix
    OUTPUT_LIB_NAME = "my-languages.so"
    COMPILER = "gcc" # Or clang

OUTPUT_LIB_PATH = BUILD_DIR / OUTPUT_LIB_NAME

def find_tree_sitter_cli() -> str:
    """Finds the tree-sitter CLI executable."""
    # Check common locations or PATH
    candidates = [shutil.which("tree-sitter")]
    # Add other potential paths if needed, e.g., node_modules/.bin
    if platform.system() == "Darwin" or platform.system() == "Linux":
         home = Path.home()
         candidates.append(shutil.which("tree-sitter", path=f"{home}/.local/bin:{home}/.npm-global/bin"))
         candidates.append(shutil.which("tree-sitter", path="/usr/local/bin"))
         # Add node global path if relevant
         try:
             npm_prefix = subprocess.run(["npm", "prefix", "-g"], capture_output=True, text=True, check=False).stdout.strip()
             if npm_prefix:
                 candidates.append(shutil.which("tree-sitter", path=os.path.join(npm_prefix, "bin")))
         except FileNotFoundError:
             pass # npm not installed

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
             # Optional: Check if it's executable?
            print(f"Found tree-sitter CLI at: {candidate}")
            return candidate

    print("ERROR: tree-sitter CLI not found. Please install it (e.g., 'npm install -g tree-sitter-cli') and ensure it's in your PATH.", file=sys.stderr)
    sys.exit(1)

def clone_grammar(name: str, config: dict) -> bool:
    """Clones a grammar repository if it doesn't exist."""
    grammar_dir = Path(config["dir"])
    if not grammar_dir.exists():
        print(f"Cloning {name} grammar from {config['repo']}...")
        VENDOR_DIR.mkdir(exist_ok=True)
        try:
            # Use --depth 1 for faster clones if history isn't needed
            subprocess.run([
                'git', 'clone', '--depth', '1',
                config["repo"],
                str(grammar_dir)
            ], check=True, capture_output=True, text=True)
            print(f"Successfully cloned {name}.")
        except subprocess.CalledProcessError as e:
             print(f"ERROR: Failed to clone {name}: {e.stderr}", file=sys.stderr)
             # Consider removing the potentially incomplete dir?
             # if grammar_dir.exists(): shutil.rmtree(grammar_dir)
             return False
        except Exception as e:
             print(f"ERROR: An unexpected error occurred during clone: {e}", file=sys.stderr)
             return False
    else:
        print(f"{name} grammar already exists at {grammar_dir}.")
    return True

def generate_parser(name: str, config: dict, tree_sitter_cli: str) -> bool:
    """Generates parser.c using tree-sitter generate if grammar.js exists."""
    grammar_dir = Path(config["dir"])
    grammar_js_path = grammar_dir / "grammar.js"
    src_dir = grammar_dir / "src"
    parser_c_path = src_dir / "parser.c"

    if config.get("has_grammar_js", False) and grammar_js_path.exists():
        print(f"Generating parser for {name} from grammar.js...")
        # Ensure src directory exists
        src_dir.mkdir(exist_ok=True)
        try:
            # Run tree-sitter generate grammar.js (implicitly outputs to src/parser.c)
            # We run it from within the grammar directory for context
            result = subprocess.run(
                [tree_sitter_cli, 'generate'],
                cwd=str(grammar_dir), # Run from the grammar's root
                check=True,
                capture_output=True,
                text=True
            )
            print(f"Successfully generated parser for {name}.")
            if result.stdout:
                 print(f"  Output:\n{result.stdout}")
            if not parser_c_path.exists():
                print(f"WARNING: tree-sitter generate completed but {parser_c_path} was not created.", file=sys.stderr)
                return False
            return True
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to generate parser for {name}:", file=sys.stderr)
            print(f"  Command: {' '.join(e.cmd)} in {grammar_dir}", file=sys.stderr)
            print(f"  Return Code: {e.returncode}", file=sys.stderr)
            print(f"  Stderr:\n{e.stderr}", file=sys.stderr)
            print(f"  Stdout:\n{e.stdout}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during parser generation for {name}: {e}", file=sys.stderr)
            return False
    elif config.get("has_grammar_js", False):
        print(f"WARNING: {name} configured with has_grammar_js=True, but {grammar_js_path} not found.", file=sys.stderr)
        return False # Generation required but couldn't happen
    else:
        print(f"Skipping parser generation for {name} (not configured or no grammar.js). Parser.c should exist pre-generated.")
        # If generation wasn't needed, parser.c *must* exist if listed in src_files
        if "src/parser.c" in config["src_files"] and not parser_c_path.exists():
            print(f"ERROR: Pre-generated parser.c expected but not found at {parser_c_path}", file=sys.stderr)
            return False
        return True # No generation needed/attempted

def build_grammars():
    """Clones, generates, and builds tree-sitter grammars defined in GRAMMARS."""
    tree_sitter_cli = find_tree_sitter_cli()

    print(f"Ensuring build directory exists: {BUILD_DIR}")
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ensuring vendor directory exists: {VENDOR_DIR}")
    VENDOR_DIR.mkdir(exist_ok=True)

    all_src_files_to_compile = []
    include_dirs = set()
    successful_setup = True

    for name, config in GRAMMARS.items():
        print(f"--- Processing Grammar: {name} ---")
        if not clone_grammar(name, config):
            successful_setup = False
            print(f"--- Skipping {name} due to clone failure ---")
            continue

        if not generate_parser(name, config, tree_sitter_cli):
             # If generation was required OR if a pre-gen parser.c was expected but missing
            if config.get("has_grammar_js", False) or "src/parser.c" in config["src_files"]:
                 successful_setup = False
                 print(f"--- Skipping {name} due to parser generation/availability issue ---")
                 continue
            else:
                # Generation wasn't required and parser.c wasn't expected, maybe only scanner.c
                pass

        grammar_path = Path(config["dir"])
        src_dir = grammar_path / "src"
        include_dirs.add(str(src_dir)) # Add src dir for includes

        # Add specified source files if they exist after potential generation
        for src_file_rel in config["src_files"]:
            src_file_abs = grammar_path / src_file_rel
            if src_file_abs.exists():
                print(f"  Adding source file: {src_file_abs}")
                all_src_files_to_compile.append(str(src_file_abs))
            else:
                # This warning might be okay if generation wasn't expected/needed for this file
                print(f"  WARNING: Source file listed but not found after processing: {src_file_abs}", file=sys.stderr)
        print(f"--- Finished Processing {name} ---")

    if not successful_setup:
         print("\nERROR: One or more grammars failed during setup (clone/generate). Aborting build.", file=sys.stderr)
         sys.exit(1)

    if not all_src_files_to_compile:
        print("\nERROR: No source files found to compile after processing all grammars.", file=sys.stderr)
        sys.exit(1)

    # Build shared library
    print(f"\nBuilding shared library {OUTPUT_LIB_NAME} from collected source files...")
    compile_cmd = [
        COMPILER,
        '-shared',
        '-o',
        str(OUTPUT_LIB_PATH),
    ]
    # Add include directories
    for inc_dir in include_dirs:
        compile_cmd.extend(['-I', inc_dir])

    # Add source files
    compile_cmd.extend(all_src_files_to_compile)

    # Add necessary flags (adjust as needed)
    compile_cmd.extend([
        '-lstdc++', # Link C++ standard library if scanners use C++
        '-fPIC', # Position Independent Code, usually required for shared libs
        '-O2' # Optional optimization
    ])

    print(f"Executing compile command: {' '.join(compile_cmd)}")
    try:
        result = subprocess.run(compile_cmd, check=True, capture_output=True, text=True)
        print("Compile successful.")
        if result.stdout:
            print("Compiler Output:")
            print(result.stdout)
        if result.stderr:
            # Treat stderr as warnings if compilation succeeded (returncode 0)
            print("Compiler Warnings:")
            print(result.stderr)
        print(f"\nGrammar build complete! Library created at: {OUTPUT_LIB_PATH}")
    except subprocess.CalledProcessError as e:
        print("\nERROR: Compilation failed!", file=sys.stderr)
        print(f"Command: {' '.join(e.cmd)}", file=sys.stderr)
        print(f"Return Code: {e.returncode}", file=sys.stderr)
        print("----- Compiler Output (stdout) -----:", file=sys.stderr)
        print(e.stdout or "(No stdout)", file=sys.stderr)
        print("----- Compiler Output (stderr) -----:", file=sys.stderr)
        print(e.stderr or "(No stderr)", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
         print(f"ERROR: Compiler '{COMPILER}' not found. Make sure it's installed and in your PATH.", file=sys.stderr)
         sys.exit(1)
    except Exception as e:
         print(f"\nERROR: An unexpected error occurred during compilation: {e}", file=sys.stderr)
         sys.exit(1)

if __name__ == '__main__':
    build_grammars() 