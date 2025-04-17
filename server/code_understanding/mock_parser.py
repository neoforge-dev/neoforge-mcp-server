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

    def parse(self, code, language=None):
        """
        Parses code into a mock tree, trying to determine the language if not provided.
        """
        if not code:
            return None

        detected_language = language
        
        # Try to detect the language from the code if not specified
        if not detected_language:
            # Check for Python language markers
            python_markers = ['def ', 'class ', 'import ', 'from ']
            has_python_markers = any(marker in code for marker in python_markers)
            
            # Check for Swift language markers
            swift_markers = ['func ', 'var ', 'let ', 'import ']
            has_swift_markers = any(marker in code for marker in swift_markers)
            
            # Check for JavaScript language markers
            js_markers = ['function ', 'const ', 'let ', 'var ', '=>']
            has_js_markers = any(marker in code for marker in js_markers)
            
            # Prioritize detection based on multiple markers
            if has_python_markers and not (has_swift_markers and has_js_markers):
                detected_language = 'python'
                logger.debug(f"Detected language: {detected_language} (from code patterns)")
            elif has_swift_markers and not has_js_markers:
                detected_language = 'swift'
                logger.debug(f"Detected language: {detected_language} (from code patterns)")
            elif has_js_markers:
                detected_language = 'javascript'
                logger.debug(f"Detected language: {detected_language} (from code patterns)")
        
        # If we still don't have a language, try to parse as Python using AST
        if not detected_language:
            try:
                import ast
                ast.parse(code)
                detected_language = 'python'
                logger.debug("Successfully parsed code with Python AST, assuming Python language")
            except Exception as e:
                logger.debug(f"Failed to parse as Python: {str(e)}")
                # Default to a generic language
                detected_language = 'generic'
        
        logger.info(f"MockParser: Using language '{detected_language}' for code")
        
        # Create a language-specific mock tree
        if detected_language == 'python':
            return self._create_python_mock_tree(code)
        elif detected_language == 'swift':
            return self._create_swift_mock_tree(code)
        else:
            # Generic fallback
            return self._create_generic_mock_tree(code)

    def _create_python_mock_tree(self, code):
        """
        Creates a mock tree for Python code with proper structure for imports, 
        functions, and classes to help the analyzer extract information correctly.
        """
        logger.info("Creating Python-specific mock tree")
        
        try:
            import ast
            tree = ast.parse(code)
            
            # Create the root node
            root = MockNode("module", text="")
            root.start_point = (0, 0)
            root.end_point = (len(code.splitlines()), 0)
            root.children = []
            
            # Process the AST to create mock nodes
            for node in tree.body:
                if isinstance(node, ast.Import):
                    # Handle simple imports: import os, sys
                    for name in node.names:
                        import_node = MockNode("import", text=f"import {name.name}")
                        import_node.start_point = (node.lineno-1, node.col_offset)
                        import_node.end_point = (node.end_lineno-1 if hasattr(node, 'end_lineno') else node.lineno-1, 
                                                node.end_col_offset if hasattr(node, 'end_col_offset') else 100)
                        
                        # Create a proper alias node structure that matches what the analyzer expects
                        name_node = MockNode("identifier", text=name.name)
                        asname_node = MockNode("identifier", text=name.asname) if name.asname else None
                        
                        # Create fields for the alias node
                        alias_fields = {'name': name_node}
                        if asname_node:
                            alias_fields['asname'] = asname_node
                        
                        # Create the alias node that will be a child of the import node
                        alias_node = MockNode("alias", fields=alias_fields)
                        
                        # Set the import node's children and fields
                        import_node.children = [alias_node]
                        
                        root.children.append(import_node)
                        logger.debug(f"Added import node: import {name.name}")
                
                elif isinstance(node, ast.ImportFrom):
                    # Handle from imports: from module import name
                    module_prefix = f"from {node.module} import " if node.module else "from . import "
                    names = ", ".join(n.name for n in node.names)
                    
                    # Create a module node representing a 'from ... import' statement
                    module_node = MockNode("module", text=f"{module_prefix}{names}")
                    module_node.start_point = (node.lineno-1, node.col_offset)
                    module_node.end_point = (node.end_lineno-1 if hasattr(node, 'end_lineno') else node.lineno-1, 
                                            node.end_col_offset if hasattr(node, 'end_col_offset') else 100)
                    
                    # Create source module identifier node
                    # Preserve leading dots for relative imports
                    module_name = node.module if node.module else ""
                    if node.level > 0:
                        # Add the appropriate number of dots for relative imports
                        relative_prefix = '.' * node.level
                        module_name = f"{relative_prefix}{module_name}"
                    
                    source_module_node = MockNode("identifier", text=module_name)
                    
                    # Create alias nodes for each imported name
                    name_alias_nodes = []
                    for n in node.names:
                        name_node = MockNode("identifier", text=n.name)
                        asname_node = MockNode("identifier", text=n.asname) if n.asname else None
                        
                        # Create fields for the alias node
                        alias_fields = {'name': name_node}
                        if asname_node:
                            alias_fields['asname'] = asname_node
                        
                        # Create the alias node
                        name_alias_nodes.append(MockNode("alias", fields=alias_fields))
                    
                    # Setup fields and children
                    module_node.fields = {
                        'module': source_module_node,
                        'names': name_alias_nodes
                    }
                    
                    root.children.append(module_node)
                    logger.debug(f"Added from import node: {module_prefix}{names}")
                
                elif isinstance(node, ast.FunctionDef):
                    # Handle function definitions
                    func_node = MockNode("function_definition", text=f"def {node.name}")
                    func_node.start_point = (node.lineno-1, node.col_offset)
                    func_node.end_point = (node.end_lineno-1 if hasattr(node, 'end_lineno') else node.lineno+5-1, 
                                          node.end_col_offset if hasattr(node, 'end_col_offset') else 100)
                    
                    # Create name node
                    name_node = MockNode("identifier", text=node.name)
                    
                    # Create parameters
                    params_node = MockNode("parameters", text="")
                    param_nodes = []
                    
                    for arg in node.args.args:
                        param_node = MockNode("parameter", text=arg.arg)
                        param_nodes.append(param_node)
                    
                    params_node.children = param_nodes
                    
                    # Setup fields and children
                    func_node.fields = {"name": name_node, "parameters": params_node}
                    func_node.children = [name_node, params_node]
                    
                    root.children.append(func_node)
                    logger.debug(f"Added function node: def {node.name}")
                
                elif isinstance(node, ast.ClassDef):
                    # Handle class definitions
                    class_node = MockNode("class_definition", text=f"class {node.name}")
                    class_node.start_point = (node.lineno-1, node.col_offset)
                    class_node.end_point = (node.end_lineno-1 if hasattr(node, 'end_lineno') else node.lineno+5-1, 
                                           node.end_col_offset if hasattr(node, 'end_col_offset') else 100)
                    
                    # Create name node
                    name_node = MockNode("identifier", text=node.name)
                    
                    # Create base classes
                    base_nodes = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_node = MockNode("type_identifier", text=base.id)
                            base_nodes.append(base_node)
                    
                    # Create inheritance clause if there are bases
                    if base_nodes:
                        inheritance_node = MockNode("inheritance_clause", text="")
                        inheritance_node.children = base_nodes
                        class_node.children = [name_node, inheritance_node]
                    else:
                        class_node.children = [name_node]
                    
                    # Create class body with methods
                    class_body = MockNode("class_body", text="")
                    body_nodes = []
                    
                    for method in node.body:
                        if isinstance(method, ast.FunctionDef):
                            method_node = MockNode("function_definition", text=f"def {method.name}")
                            method_node.start_point = (method.lineno-1, method.col_offset)
                            method_node.end_point = (method.end_lineno-1 if hasattr(method, 'end_lineno') else method.lineno+3-1,
                                                   method.end_col_offset if hasattr(method, 'end_col_offset') else 100)
                            
                            # Create method name node
                            method_name_node = MockNode("identifier", text=method.name)
                            
                            # Create parameters
                            method_params_node = MockNode("parameters", text="")
                            method_param_nodes = []
                            
                            for arg in method.args.args:
                                param_node = MockNode("parameter", text=arg.arg)
                                method_param_nodes.append(param_node)
                            
                            method_params_node.children = method_param_nodes
                            
                            # Setup fields and children
                            method_node.fields = {"name": method_name_node, "parameters": method_params_node}
                            method_node.children = [method_name_node, method_params_node]
                            
                            body_nodes.append(method_node)
                    
                    class_body.children = body_nodes
                    class_node.children.append(class_body)
                    
                    # Setup fields
                    class_node.fields = {"name": name_node, "body": class_body.children}
                    if base_nodes:
                        class_node.fields["bases"] = base_nodes
                    
                    root.children.append(class_node)
                    logger.debug(f"Added class node: class {node.name} with {len(body_nodes)} methods")
            
            # Return a MockTree instead of just the root node
            return MockTree(root_node=root)
            
        except Exception as e:
            logger.error(f"Error creating Python mock tree: {str(e)}")
            # Fall back to generic tree if AST parsing fails
            return self._create_generic_mock_tree(code)

    def _create_swift_mock_tree(self, code):
        """Creates a mock tree for Swift code."""
        logger.info("Creating Swift-specific mock tree")
        # Simple implementation for now
        return self._create_generic_mock_tree(code)

    def _create_generic_mock_tree(self, code):
        """Creates a generic mock tree for any code."""
        logger.info("Creating generic mock tree")
        
        lines = code.splitlines()
        root = MockNode("program", text="")
        root.start_point = (0, 0)
        root.end_point = (len(lines), 0)
        root.children = []
        
        # Simple line-by-line processing
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Try to detect imports
            if line.startswith("import ") or line.startswith("from "):
                import_node = MockNode("import", text=line)
                import_node.start_point = (i, 0)
                import_node.end_point = (i, len(line))
                
                # Extract module name (very basic)
                if line.startswith("import "):
                    module = line[7:].strip()
                else:  # from ... import
                    parts = line.split(" import ")
                    # Preserve the entire module path including any leading dots
                    module = parts[0][5:].strip() if len(parts) > 1 else ""
                
                # Create a module node
                module_node = MockNode("identifier", text=module)
                import_node.fields = {"name": module_node}
                import_node.children = [module_node]
                
                root.children.append(import_node)
            
            # Try to detect function definitions
            elif line.startswith("def "):
                # Extract function name (very basic)
                func_parts = line[4:].split("(")
                func_name = func_parts[0].strip()
                
                func_node = MockNode("function_definition", text=line)
                func_node.start_point = (i, 0)
                # Set an approximate end line (assuming simple functions)
                func_node.end_point = (i + 3, 0)
                
                # Create a name node
                name_node = MockNode("identifier", text=func_name)
                
                # Create a parameters node (very basic)
                params_str = func_parts[1].split(")")[0] if len(func_parts) > 1 else ""
                params_node = MockNode("parameters", text=params_str)
                params_node.children = []
                
                # Add individual parameter nodes
                for param in params_str.split(","):
                    param = param.strip()
                    if param:
                        param_node = MockNode("parameter", text=param)
                        params_node.children.append(param_node)
                
                # Setup fields and children
                func_node.fields = {"name": name_node, "parameters": params_node}
                func_node.children = [name_node, params_node]
                
                root.children.append(func_node)
            
            # Try to detect class definitions
            elif line.startswith("class "):
                # Extract class name (very basic)
                class_parts = line[6:].split(":")
                class_name = class_parts[0].strip().split("(")[0]
                
                class_node = MockNode("class_definition", text=line)
                class_node.start_point = (i, 0)
                # Set an approximate end line (assuming simple classes)
                class_node.end_point = (i + 5, 0)
                
                # Create a name node
                name_node = MockNode("identifier", text=class_name)
                
                # Setup fields and children
                class_node.fields = {"name": name_node, "body": []}
                class_node.children = [name_node]
                
                root.children.append(class_node)
        
        # Return a MockTree instead of just the root node
        return MockTree(root_node=root)

    def query(self, pattern: str) -> MockQuery:
        """Create a mock query."""
        return MockQuery(pattern)

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
                 # Iterate over children 'alias' nodes instead of using regex on text
                 for alias_node in node.children:
                     if alias_node.type == 'alias':
                         name_node = alias_node.fields.get('name')
                         module_name = name_node.text if name_node else 'unknown_module'
                         # Use alias node's location
                         start_line = alias_node.start_point[0]
                         end_line = alias_node.end_point[0]
                         logger.info(f"extract_symbols: Appending simple import: {module_name}")
                         symbols['imports'].append({
                             'type': 'import',
                             'module': module_name,
                             'symbol': None, # No specific symbol for 'import module'
                             'start_line': start_line,
                             'end_line': end_line
                         })
                 #else:
                 #    logger.warning(f"extract_symbols: Regex failed for simple import: {node.text}")
            # --- Handle From Imports (ast.ImportFrom) --- 
            elif node.type == 'module': # This type comes from converting ast.ImportFrom
                 # The children of this 'module' node are individual 'import' nodes like "from x import y"
                 logger.info(f"extract_symbols: Processing node type 'module': {node.text if node.text else '[Root Module]'}")
                 # Iterate over the 'names' field which contains alias nodes for ImportFrom
                 for alias_node in node.fields.get('names', []):
                     # Add check if it's actually an alias node expected here
                     if alias_node.type == 'alias': # Check the child type
                         logger.info(f"extract_symbols: Processing 'module' alias field: {alias_node.fields}")
                         # Extract module name from the parent 'module' node's fields
                         source_module_node = node.fields.get('module')
                         module_name = source_module_node.text if source_module_node else 'unknown_module'
                         
                         # Extract symbol name from the alias node's fields
                         name_node = alias_node.fields.get('name')
                         symbol_name = name_node.text if name_node else 'unknown_symbol'
                         
                         # Extract location from the alias node itself
                         start_line = alias_node.start_point[0]
                         end_line = alias_node.end_point[0]

                         logger.info(f"extract_symbols: Appending from_import: {module_name} -> {symbol_name}")
                         symbols['imports'].append({
                             'type': 'from_import',
                             'module': module_name,
                             'symbol': symbol_name,
                             'start_line': start_line,
                             'end_line': end_line
                         })
                     # else: # Optional: Log if a child of 'module' is not 'import'
                     #    logger.debug(f"extract_symbols: Skipping child of type {import_child.type} within 'module' node processing.")

            # -- Existing Function/Class/Call/Attribute handling ---
            elif node.type == 'function_definition':
                # Adjusted logic for extracting function info from MockNode
                name_node = next((child for child in node.children if child.type == 'name'), None)
                name = name_node.text if name_node else 'unknown_function'
                
                params_node = next((child for child in node.children if child.type == 'parameters'), None)
                params = []
                if params_node:
                    for param_child in params_node.children:
                         if param_child.type == 'identifier': # Check child type within parameters
                            params.append({
                                'name': param_child.text,
                                'start_line': param_child.start_point[0],
                                'end_line': param_child.end_point[0]
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
        # We need to process the actual root node from the converted AST tree
        process_node(tree.root_node)
        logger.info(f"extract_symbols: Finished extraction. Found {len(symbols['imports'])} imports.")

        return symbols, references

    def _convert_ast_to_mock_tree(self, node: ast.AST) -> MockTree:
        """Convert AST node to mock tree."""
        if isinstance(node, ast.Module):
            children = []
            for child in node.body:
                converted_child = self._convert_ast_node(child)
                if converted_child: # Ensure node conversion was successful
                    children.append(converted_child)
                #elif isinstance(child, ast.Import):
                #    children.append(self._convert_ast_node(child))
                #elif isinstance(child, ast.ImportFrom):
                #    children.append(self._convert_ast_node(child))
                #elif isinstance(child, ast.FunctionDef):
                #    children.append(self._convert_ast_node(child))
                #elif isinstance(child, ast.ClassDef):
                #    children.append(self._convert_ast_node(child))
                #else:
                #    children.append(self._convert_ast_node(child))
            root = MockNode('module', children=children) # Root should be 'module' for Python AST
        else:
            root = self._convert_ast_node(node)
        # Make sure root is not None before creating MockTree
        if root is None:
             logger.error("Failed to convert root AST node, returning empty tree.")
             root = MockNode(type='error', children=[], start_point=(0,0), end_point=(0,0))
        return MockTree(root_node=root)

    def _convert_ast_node(self, node: ast.AST) -> Optional[MockNode]:
        """Convert AST node to mock node, ensuring structure matches analyzer expectations."""
        # Common attributes
        start_point = (node.lineno - 1, node.col_offset)
        end_point = (getattr(node, 'end_lineno', node.lineno) -1 , getattr(node, 'end_col_offset', 0))

        if isinstance(node, ast.Import):
            alias_nodes = []
            for alias in node.names:
                name_node = MockNode(type='identifier', text=alias.name)
                asname_node = MockNode(type='identifier', text=alias.asname) if alias.asname else None
                fields = {'name': name_node}
                if asname_node:
                    fields['asname'] = asname_node
                alias_nodes.append(MockNode(type='alias', fields=fields))
            
            return MockNode(
                 type='import',
                 children=alias_nodes,
                 start_point=start_point,
                 end_point=end_point
            )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ''
            level = node.level
            module_prefix = '.' * level
            # Prepend the dots to the module name properly
            full_module_name = f"{module_prefix}{module_name}"
            
            source_module_node = MockNode(type='identifier', text=full_module_name)
            
            name_alias_nodes = []
            for alias in node.names:
                name_node = MockNode(type='identifier', text=alias.name)
                asname_node = MockNode(type='identifier', text=alias.asname) if alias.asname else None
                fields = {'name': name_node}
                if asname_node:
                    fields['asname'] = asname_node
                name_alias_nodes.append(MockNode(type='alias', fields=fields))

            return MockNode(
                type='module', # Represents ImportFrom in analyzer logic
                fields={
                    'module': source_module_node,
                    'names': name_alias_nodes
                },
                start_point=start_point,
                end_point=end_point
            )
        elif isinstance(node, ast.FunctionDef):
            name_node = MockNode(type='name', text=node.name)
            params = []
            for arg in node.args.args:
                # Simple identifier node for parameter name
                param_node = MockNode(type='identifier', text=arg.arg, start_point=(arg.lineno -1, arg.col_offset), end_point=(getattr(arg, 'end_lineno', arg.lineno) -1 , getattr(arg, 'end_col_offset', 0)))
                params.append(param_node)
            parameters_node = MockNode(type='parameters', children=params)
            
            body_nodes = []
            for child in node.body:
                 body_node = self._convert_ast_node(child)
                 if body_node:
                     body_nodes.append(body_node)
            body_container_node = MockNode(type='body', children=body_nodes)
            
            return MockNode(
                 type='function_definition',
                 # text=node.name, # Keep text field or remove? Analyzer uses child node.
                 children=[name_node, parameters_node, body_container_node],
                 start_point=start_point,
                 end_point=end_point
            )
        elif isinstance(node, ast.ClassDef):
            name_node = MockNode(type='identifier', text=node.name)
            bases = []
            for base in node.bases:
                base_node = self._convert_ast_node(base) # Convert base nodes (e.g., ast.Name)
                if base_node:
                     bases.append(base_node)
            # bases_node = MockNode(type='bases', children=bases) # Maybe not needed if fields used
            
            body_content = []
            for child in node.body:
                body_item_node = self._convert_ast_node(child)
                if body_item_node:
                    # Filter for relevant items like methods (function_definition)
                    if body_item_node.type == 'function_definition':
                         body_content.append(body_item_node)
                    # Could add handling for class variables (assignments) here later
            # body_node = MockNode(type='body', children=body_content) # Maybe not needed if fields used
            
            return MockNode(
                type='class_definition',
                fields={
                    'name': name_node,
                    'bases': bases, # Store list of base identifier nodes directly
                    'body': body_content # Store list of method nodes directly
                },
                children=[name_node], # Keep name as child for consistency?
                start_point=start_point,
                end_point=end_point
            )
        elif isinstance(node, ast.Call):
             func_node = self._convert_ast_node(node.func)
             args = [self._convert_ast_node(arg) for arg in node.args if self._convert_ast_node(arg)]
             # Simplified Call representation
             return MockNode(
                  type='call',
                  fields={'function': func_node, 'arguments': args},
                  start_point=start_point,
                  end_point=end_point
             )
        elif isinstance(node, ast.Attribute):
            value_node = self._convert_ast_node(node.value)
            attr_node = MockNode(type='identifier', text=node.attr)
            return MockNode(
                 type='attribute',
                 fields={'object': value_node, 'attribute': attr_node},
                 start_point=start_point,
                 end_point=end_point
            )
        elif isinstance(node, ast.Name):
            return MockNode(
                 type='identifier',
                 text=node.id,
                 start_point=start_point,
                 end_point=end_point
            )
        elif isinstance(node, ast.Assign):
            targets = [self._convert_ast_node(t) for t in node.targets if self._convert_ast_node(t)]
            value = self._convert_ast_node(node.value)
            # Assume single target for simplicity, matching analyzer expectation
            if targets and value:
                return MockNode(
                     type='assignment',
                     fields={'left': targets[0], 'right': value},
                     start_point=start_point,
                     end_point=end_point
                )
        elif isinstance(node, ast.Return):
            value_node = self._convert_ast_node(node.value) if node.value else None
            return MockNode(
                 type='return',
                 fields={'value': value_node},
                 start_point=start_point,
                 end_point=end_point
            )
        # elif isinstance(node, ast.Expr): # Handled in process_node
        #     pass
        
        # Fallback for unhandled nodes (keep simple text representation)
        logger.debug(f"_convert_ast_node: Falling back for unhandled type {type(node).__name__}")
        try:
            node_text = ast.unparse(node)
        except Exception:
             node_text = f"[Unparse failed for {type(node).__name__}]"
        return MockNode(
             type='unknown', 
             text=node_text,
             start_point=start_point,
             end_point=end_point
        ) 