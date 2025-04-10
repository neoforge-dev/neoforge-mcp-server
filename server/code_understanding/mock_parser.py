"""Mock parser for testing purposes."""

from typing import Any, Optional, List, Dict, Tuple
import ast
import logging
import re

# Import common types
from .common_types import MockNode, MockTree

logger = logging.getLogger(__name__)

class MockQuery:
    """Mock query for testing."""
    def __init__(self, pattern: str):
        self.pattern = pattern

    def matches(self, node: MockNode) -> List[Dict[str, Any]]:
        """Return matches based on the query pattern."""
        matches = []
        if node.type == 'program':
            if 'import' in self.pattern:
                # Handle import statements
                for child in node.children:
                    if child.type == 'import_statement':
                        matches.append({
                            'captures': [(child, 'import')]
                        })
            elif 'require' in self.pattern:
                # Handle require statements
                for child in node.children:
                    if child.type == 'variable_declaration':
                        for var_decl in child.children:
                            if var_decl.type == 'variable_declarator':
                                init = var_decl.child_by_field_name('init')
                                if init and init.type == 'call_expression' and init.child_by_field_name('function').text.decode('utf-8') == 'require':
                                    matches.append({
                                        'captures': [(init, 'require_call')]
                                    })
            elif 'async' in self.pattern:
                # Handle async functions
                for child in node.children:
                    if child.type == 'function_declaration' and any(c.type == 'async' for c in child.children):
                        matches.append({
                            'captures': [(child, 'function')]
                        })
                    elif child.type == 'class_declaration':
                        for method in child.child_by_field_name('body').children:
                            if method.type == 'method_definition' and any(c.type == 'async' for c in method.children):
                                matches.append({
                                    'captures': [(method, 'method')]
                                })
            elif 'export' in self.pattern:
                # Handle export statements
                for child in node.children:
                    if child.type == 'export_statement':
                        matches.append({
                            'captures': [(child, 'export')]
                        })
            elif 'class' in self.pattern:
                # Handle class declarations
                for child in node.children:
                    if child.type == 'class_declaration':
                        matches.append({
                            'captures': [(child, 'class')]
                        })
            elif 'variable' in self.pattern:
                # Handle variable declarations
                for child in node.children:
                    if child.type == 'variable_declaration':
                        for var_decl in child.children:
                            if var_decl.type == 'variable_declarator':
                                matches.append({
                                    'captures': [(var_decl, 'variable')]
                                })
        return matches

class MockParser:
    """Mock parser for testing."""
    def __init__(self):
        self.language = 'javascript'

    def parse(self, code: bytes) -> MockNode:
        """Parse code and return a mock AST."""
        if not code:
            return MockNode('program', children=[])

        # Convert bytes to string
        code_str = code.decode('utf-8')

        # Create program node
        program = MockNode('program', children=[])

        # Parse imports
        import_pattern = r'import\s+(?:(?:\{[^}]+\}|\*\s+as\s+\w+|\w+)(?:\s*,\s*(?:\{[^}]+\}|\w+))?)\s+from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(import_pattern, code_str):
            source = match.group(1)
            import_node = MockNode('import_statement', fields={
                'source': MockNode('string', text=source),
                'import_clause': MockNode('import_clause', text=match.group(0))
            })
            program.children.append(import_node)

        # Parse requires
        require_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*require\([\'"]([^\'"]+)[\'"]\)'
        for match in re.finditer(require_pattern, code_str):
            var_name, module = match.groups()
            var_decl = MockNode('variable_declaration', children=[
                MockNode('variable_declarator', fields={
                    'name': MockNode('identifier', text=var_name),
                    'init': MockNode('call_expression', fields={
                        'function': MockNode('identifier', text='require'),
                        'arguments': MockNode('arguments', children=[
                            MockNode('string', text=module)
                        ])
                    })
                })
            ])
            program.children.append(var_decl)

        # Parse exports
        export_pattern = r'export\s+(?:default\s+)?(?:(?:const|let|var|function|class)\s+(\w+)|(?:\{[^}]+\}))'
        for match in re.finditer(export_pattern, code_str):
            export_node = MockNode('export_statement', fields={
                'declaration': MockNode('identifier', text=match.group(1)) if match.group(1) else None
            })
            program.children.append(export_node)

        # Parse async functions
        async_pattern = r'async\s+function\s+(\w+)'
        for match in re.finditer(async_pattern, code_str):
            func_node = MockNode('function_declaration', children=[
                MockNode('async'),
                MockNode('identifier', text=match.group(1))
            ])
            program.children.append(func_node)

        # Parse classes
        # Capture class name (group 1) and body (group 2)
        class_pattern = r'class\s+(\w+)\s*\{(.*?)\}\s*;?' # Added body capture and optional semicolon
        method_pattern = r'^\s*(\w+)\s*\([^)]*\)\s*\{' # Matches methods like 'methodName() {'

        for match in re.finditer(class_pattern, code_str, re.DOTALL | re.MULTILINE):
            class_name = match.group(1)
            class_body_text = match.group(2)
            
            # Create class body node and populate with methods
            class_body_node = MockNode('class_body', children=[])
            for method_match in re.finditer(method_pattern, class_body_text, re.MULTILINE):
                method_name = method_match.group(1)
                # Create a method_definition MockNode
                method_node = MockNode(
                    type='method_definition',
                    fields={
                        # Mimic tree-sitter structure where name is a property_identifier field
                        'name': MockNode('property_identifier', text=method_name) 
                    },
                    # Add dummy start/end points if needed later
                    # start_point=(0,0), end_point=(0,0) 
                )
                class_body_node.children.append(method_node)

            # Create the main class declaration node
            class_node = MockNode('class_declaration', fields={
                'name': MockNode('identifier', text=class_name),
                'body': class_body_node # Assign the populated body node
            })
            program.children.append(class_node)

        # Parse variables
        var_pattern = r'(?:const|let|var)\s+(\w+)'
        for match in re.finditer(var_pattern, code_str):
            var_decl = MockNode('variable_declaration', children=[
                MockNode('variable_declarator', fields={
                    'name': MockNode('identifier', text=match.group(1))
                })
            ])
            program.children.append(var_decl)

        return program

    def query(self, pattern: str) -> MockQuery:
        """Create a mock query."""
        return MockQuery(pattern)

    def parse(self, code: str) -> Optional[MockTree]:
        """Parse code and return a mock tree."""
        print(f"--- ENTERING MockParser.parse ---")
        try:
            if isinstance(code, bytes):
                code = code.decode('utf-8')
            tree = ast.parse(code)
            logger.info(f"MockParser: AST parsed. Body nodes: {[type(n).__name__ for n in tree.body]}")
            root = MockNode('module', children=[])
            
            def process_node(node: ast.AST) -> Optional[MockNode]:
                logger.info(f"MockParser: Entered process_node for type: {type(node).__name__}")
                mock_node = None
                if isinstance(node, ast.Import):
                    logger.info(f"MockParser: Processing ast.Import")
                    mock_node = self._convert_ast_node(node)
                elif isinstance(node, ast.ImportFrom):
                    logger.info(f"MockParser: Processing ast.ImportFrom")
                    mock_node = self._convert_ast_node(node)
                elif isinstance(node, ast.FunctionDef):
                    logger.info(f"MockParser: Processing ast.FunctionDef")
                    mock_node = self._convert_ast_node(node)
                elif isinstance(node, ast.ClassDef):
                    logger.info(f"MockParser: Processing ast.ClassDef")
                    mock_node = self._convert_ast_node(node)
                elif isinstance(node, ast.Call):
                    logger.info(f"MockParser: Processing ast.Call")
                    mock_node = self._convert_ast_node(node)
                elif isinstance(node, ast.Attribute):
                    logger.info(f"MockParser: Processing ast.Attribute")
                    mock_node = self._convert_ast_node(node)
                elif isinstance(node, ast.Name):
                    logger.info(f"MockParser: Processing ast.Name")
                    mock_node = self._convert_ast_node(node)
                elif isinstance(node, ast.Return):
                    logger.info(f"MockParser: Processing ast.Return")
                    mock_node = self._convert_ast_node(node)
                elif isinstance(node, ast.Assign):
                    logger.info(f"MockParser: Processing ast.Assign")
                    mock_node = self._convert_ast_node(node)
                elif isinstance(node, ast.Expr):
                    logger.info(f"MockParser: Processing ast.Expr, descending into value")
                    return process_node(node.value)
                else:
                    logger.warning(f"MockParser: Unhandled node type {type(node).__name__} in process_node, processing children.")
                    for child in ast.iter_child_nodes(node):
                        child_node = process_node(child)
                        if child_node:
                            logger.info(f"MockParser: Appending child {child_node.type} from unhandled parent {type(node).__name__} to root")
                            root.children.append(child_node)
                    mock_node = None

                if mock_node:
                    logger.info(f"MockParser: Exiting process_node, returning MockNode of type {mock_node.type}")
                else:
                    logger.info(f"MockParser: Exiting process_node, returning None")
                return mock_node

            logger.info(f"MockParser: Starting loop over tree.body")
            for i, node in enumerate(tree.body):
                logger.info(f"MockParser: Processing body node {i} of type {type(node).__name__}")
                node_result = process_node(node)
                if node_result:
                    logger.info(f"MockParser: Appending node {node_result.type} from body to root")
                    root.children.append(node_result)
                else:
                    logger.info(f"MockParser: process_node returned None for body node {i} ({type(node).__name__})")

            logger.info(f"MockParser: Final root node children types: {[child.type for child in root.children]}")
            print(f"--- EXITING MockParser.parse NORMALLY ---")
            return MockTree(root)
        except Exception as e:
            print(f"--- EXITING MockParser.parse WITH ERROR: {e} ---")
            logger.exception(f"MockParser: Failed to parse code")
            return None

    def extract_symbols(self, tree: MockTree) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """Extract symbols and references from the AST.

        Args:
            tree: The AST to extract symbols from

        Returns:
            A tuple of (symbols, references) where:
            - symbols is a dictionary mapping symbol types to lists of symbol information
            - references is a list of reference information dictionaries
        """
        symbols = {
            'imports': [],
            'functions': [],
            'classes': [],
            'variables': []
        }
        references = []
        current_scope = None

        def process_node(node: MockNode) -> None:
            nonlocal current_scope
            # --- Handle Imports (ast.Import) --- 
            if node.type == 'import':
                 # The MockNode text for ast.Import is like "import module1, module2"
                 # We need to extract the module names
                 logger.info(f"extract_symbols: Processing node type 'import': {node.text}")
                 match = re.match(r'import\s+(.*)', node.text)
                 if match:
                     modules = [m.strip() for m in match.group(1).split(',')]
                     for module_name in modules:
                         logger.info(f"extract_symbols: Appending simple import: {module_name}")
                         symbols['imports'].append({
                             'type': 'import',
                             'module': module_name,
                             'symbol': None, # No specific symbol for 'import module'
                             'start_line': node.start_point[0],
                             'end_line': node.end_point[0]
                         })
                 else:
                     logger.warning(f"extract_symbols: Regex failed for simple import: {node.text}")
            # --- Handle From Imports (ast.ImportFrom) --- 
            elif node.type == 'module': # This type comes from converting ast.ImportFrom
                 # The children of this 'module' node are individual 'import' nodes like "from x import y"
                 logger.info(f"extract_symbols: Processing node type 'module': {node.text if node.text else '[Root Module]'}")
                 for import_child in node.children:
                     # Add check if it's actually an import node expected here
                     if import_child.type == 'import': # Check the child type
                         logger.info(f"extract_symbols: Processing 'module' child of type 'import': {import_child.text}")
                         match = re.match(r'from\s+([.\w]+)\s+import\s+(\w+)', import_child.text)
                         if match:
                             module_name, symbol_name = match.groups()
                             logger.info(f"extract_symbols: Appending from_import: {module_name} -> {symbol_name}")
                             symbols['imports'].append({
                                 'type': 'from_import',
                                 'module': module_name,
                                 'symbol': symbol_name,
                                 'start_line': import_child.start_point[0],
                                 'end_line': import_child.end_point[0]
                             })
                         else:
                             logger.warning(f"extract_symbols: Regex failed for from_import in child: {import_child.text}")
                     # else: # Optional: Log if a child of 'module' is not 'import'
                     #    logger.debug(f"extract_symbols: Skipping child of type {import_child.type} within 'module' node processing.")

            # -- Existing Function/Class/Call/Attribute handling ---
            elif node.type == 'function_definition':
                name = next((child.text for child in node.children if child.type == 'name'), '')
                params = []
                for child in node.children:
                    if child.type == 'parameters':
                        for param in child.children:
                            if param.type == 'identifier':
                                params.append({
                                    'name': param.text,
                                    'start_line': param.start_point[0],
                                    'end_line': param.end_point[0]
                                })
                # Only append if at the top level (no current class scope)
                if current_scope is None: 
                    logger.info(f"extract_symbols: Appending top-level function: {name}")
                    symbols['functions'].append({
                        'type': 'function',
                        'name': name,
                        'parameters': params,
                        'start_line': node.start_point[0] + 1,
                        'end_line': node.end_point[0]
                    })
                # --- Scope handling for recursion --- 
                old_scope = current_scope
                current_scope = name
                for child in node.children:
                    if child.type == 'body':
                        for child_node in child.children:
                            process_node(child_node)
                current_scope = old_scope
            elif node.type == 'class_definition':
                # Extract name, bases, and methods directly
                class_name_node = next((child for child in node.children if child.type == 'identifier'), None)
                name = class_name_node.text if class_name_node else node.text # Fallback if structure differs
                methods = []
                bases = []
                body_children = [] # Collect body nodes for explicit method extraction
                for child in node.children:
                    if child.type == 'bases':
                        bases.extend([base.text for base in child.children if base.type == 'identifier'])
                    elif child.type == 'body':
                        # Find function definitions within the body
                        body_children = child.children
                        for method_node in child.children: 
                            if method_node.type == 'function_definition':
                                # Extract method name (assuming similar structure to top-level functions)
                                method_name_node = next((m_child for m_child in method_node.children if m_child.type == 'name'), None)
                                method_name = method_name_node.text if method_name_node else method_node.text # Fallback
                                methods.append({
                                    'name': method_name,
                                    'start_line': method_node.start_point[0] + 1,
                                    'end_line': method_node.end_point[0]
                                })
                logger.info(f"extract_symbols: Appending class: {name} with {len(methods)} methods")
                symbols['classes'].append({
                    'type': 'class',
                    'name': name,
                    'bases': bases,
                    'methods': methods,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0]
                })
                # --- Scope handling for recursion --- 
                old_scope = current_scope
                current_scope = name
                # --- REMOVED recursive call for body nodes --- 
                # No need to recursively call process_node on body children here, 
                # as methods are explicitly extracted above. 
                # This prevents methods from being added to the top-level functions list.
                # for child_node in body_children: # Use collected body children
                #    process_node(child_node)
                current_scope = old_scope
            elif node.type == 'call':
                references.append({
                    'type': 'call',
                    'name': node.text,
                    'scope': current_scope,
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0]
                })
            elif node.type == 'attribute':
                references.append({
                    'type': 'attribute',
                    'name': node.text.split('.')[-1],
                    'scope': node.text.split('.')[0],
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0]
                })

            # Recursive call - Log before recursion
            logger.debug(f"extract_symbols: Recursing into children of node type {node.type}")
            # *** Ensure recursion doesn't happen if inside class_definition block already handled ***
            if node.type != 'class_definition': # Only recurse if not inside the class block handled above
                for child in node.children:
                    process_node(child)
            # else: # Optional log if skipping recursion for class children
            #    logger.debug(f"extract_symbols: Skipping explicit recursion for children of handled class_definition {node.text}")

        logger.info("extract_symbols: Starting extraction by calling process_node on root.")
        process_node(tree.root_node)
        logger.info(f"extract_symbols: Finished extraction. Found {len(symbols['imports'])} imports.")

        return symbols, references

    def _convert_ast_to_mock_tree(self, node: ast.AST) -> MockTree:
        """Convert AST node to mock tree."""
        if isinstance(node, ast.Module):
            children = []
            for child in node.body:
                if isinstance(child, ast.Import):
                    children.append(self._convert_ast_node(child))
                elif isinstance(child, ast.ImportFrom):
                    children.append(self._convert_ast_node(child))
                elif isinstance(child, ast.FunctionDef):
                    children.append(self._convert_ast_node(child))
                elif isinstance(child, ast.ClassDef):
                    children.append(self._convert_ast_node(child))
                else:
                    children.append(self._convert_ast_node(child))
            root = MockNode('module', children=children)
        else:
            root = self._convert_ast_node(node)
        return MockTree(root)

    def _convert_ast_node(self, node: ast.AST) -> MockNode:
        """Convert AST node to mock node."""
        if isinstance(node, ast.Import):
            names = [name.name for name in node.names]
            return MockNode('import', text=f"import {', '.join(names)}", start_point=(node.lineno, 0), end_point=(node.lineno, len(f"import {', '.join(names)}")))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            names = [name.name for name in node.names]
            
            # Add dots for relative imports
            module_prefix = '.' * node.level
            full_module = f"{module_prefix}{module}" if module else module_prefix
            
            # For each imported name, create a separate import node
            import_nodes = []
            for name in names:
                import_nodes.append(MockNode('import', text=f"from {full_module} import {name}", start_point=(node.lineno, 0), end_point=(node.lineno, len(f"from {full_module} import {name}"))))
            # Return a module node containing all import nodes
            return MockNode('module', children=import_nodes)
        elif isinstance(node, ast.FunctionDef):
            params = []
            for arg in node.args.args:
                params.append(MockNode('identifier', text=arg.arg, start_point=(node.lineno, 0), end_point=(node.lineno, len(arg.arg))))
            
            return MockNode('function_definition', text=node.name, start_point=(node.lineno, 0), end_point=(node.end_lineno, 0), children=[
                MockNode('name', text=node.name),
                MockNode('parameters', children=params),
                MockNode('body', children=[self._convert_ast_node(child) for child in node.body])
            ])
        elif isinstance(node, ast.ClassDef):
            name_node = MockNode(type='identifier', text=node.name)
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(MockNode(type='identifier', text=base.id))
                elif isinstance(base, ast.Attribute):
                    bases.append(MockNode(type='identifier', text=f"{base.value.id}.{base.attr}"))
            bases_node = MockNode(type='bases', children=bases)
            
            body = []
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    body.append(self._convert_ast_node(child))
                elif isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            body.append(MockNode('attribute', text=target.id))
            body_node = MockNode(type='body', children=body)
            
            return MockNode(
                type='class_definition',
                text=node.name,
                fields={
                    'name': name_node,
                    'bases': bases_node,
                    'body': body_node,
                    'type': 'class',
                    'start_line': node.lineno,
                    'end_line': node.end_lineno or node.lineno,
                    'bases_list': [base.id for base in node.bases if isinstance(base, ast.Name)]
                },
                start_point=(node.lineno - 1, node.col_offset),
                end_point=(node.end_lineno or node.lineno, node.end_col_offset or 0),
                children=[name_node, bases_node, body_node]
            )
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return MockNode('call', text=node.func.id, start_point=(node.lineno, 0), end_point=(node.lineno, len(node.func.id)))
            elif isinstance(node.func, ast.Attribute):
                return MockNode('call', text=f"{node.func.value.id}.{node.func.attr}", start_point=(node.lineno, 0), end_point=(node.lineno, len(f"{node.func.value.id}.{node.func.attr}")))
            else:
                return MockNode('call', text=ast.unparse(node.func), start_point=(node.lineno, 0), end_point=(node.lineno, len(ast.unparse(node.func))))
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return MockNode('attribute', text=f"{node.value.id}.{node.attr}", start_point=(node.lineno, 0), end_point=(node.lineno, len(f"{node.value.id}.{node.attr}")))
            else:
                return MockNode('attribute', text=f"{ast.unparse(node.value)}.{node.attr}", start_point=(node.lineno, 0), end_point=(node.lineno, len(f"{ast.unparse(node.value)}.{node.attr}")))
        elif isinstance(node, ast.Name):
            return MockNode('identifier', text=node.id, start_point=(node.lineno, node.col_offset), end_point=(node.lineno, node.col_offset + len(node.id)))
        elif isinstance(node, ast.Return):
            if isinstance(node.value, ast.Call):
                return self._convert_ast_node(node.value)
            else:
                value_text = ast.unparse(node.value) if node.value else ''
                return MockNode('return', text=value_text, start_point=(node.lineno, 0), end_point=(node.lineno, len(value_text)))
        else:
            try:
                node_text = ast.unparse(node)
            except Exception:
                 node_text = f"[Unparse failed for {type(node).__name__}]"
            logger.warning(f"MockParser: Creating 'unknown' node for unhandled AST type: {type(node).__name__}")
            return MockNode('unknown', text=node_text) 