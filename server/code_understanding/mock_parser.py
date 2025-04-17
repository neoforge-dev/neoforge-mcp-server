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

    def parse(self, code):
        """Parse code and return a MockTree.
        
        Args:
            code: Code to parse
            
        Returns:
            MockTree: Parsed tree
        """
        print("--- ENTERING MockParser.parse ---")
        
        try:
            # Convert bytes to string if necessary
            if isinstance(code, bytes):
                code_str = code.decode('utf-8', errors='replace')
            else:
                code_str = code
                
            # Check for empty code
            if not code_str or code_str.strip() == '':
                print("--- EXITING MockParser.parse WITH WARNING: Empty code ---")
                root = MockNode(type='file', children=[], start_point=(0, 0), end_point=(0, 0))
                return MockTree(root_node=root)
            
            # For test purposes, create a simple parse tree based on the language of the code
            # Detect language based on patterns in the code
            if 'import Foundation' in code_str or 'class ' in code_str or 'struct ' in code_str or 'func ' in code_str and '{' in code_str:
                return self._create_swift_mock_tree(code_str)
            elif 'import' in code_str and '{' in code_str and 'function' in code_str:
                return self._create_js_mock_tree(code_str)
            else:
                # Default to Python-style parsing for backward compatibility
                try:
                    tree = ast.parse(code)
                    root = self._convert_ast_to_mock_tree(tree)
                    print(f"--- EXITING MockParser.parse SUCCESSFULLY ---")
                    return MockTree(root_node=root)
                except SyntaxError as e:
                    # If Python parsing fails, try one more language detection
                    if 'import' in code_str or 'class' in code_str or 'func' in code_str:
                        return self._create_swift_mock_tree(code_str)
                    else:
                        # Create a generic file structure for any code
                        return self._create_generic_mock_tree(code_str)
                
        except Exception as e:
            logging.error(f"MockParser: Failed to parse code", exc_info=True)
            print(f"--- EXITING MockParser.parse WITH ERROR: {str(e)} ---")
            
            # Even on error, return a minimal tree with error flag
            root = MockNode(type='file', children=[], start_point=(0, 0), end_point=(0, 0))
            tree = MockTree(root_node=root)
            tree.has_error = True
            return tree

    def _create_swift_mock_tree(self, code_str):
        """Create a mock tree for Swift code.
        
        Args:
            code_str: Swift code as a string
            
        Returns:
            MockTree: Mock tree representing Swift code
        """
        print("--- Creating Swift mock tree ---")
        lines = code_str.split('\n')
        line_count = len(lines)
        
        # Create root node
        root = MockNode(
            type='source_file',
            children=[],
            start_point=(0, 0),
            end_point=(line_count, 0)
        )
        
        # Add import declarations
        import_pattern = r'import\s+(\w+)'
        for i, line in enumerate(lines):
            match = re.search(import_pattern, line)
            if match:
                module = match.group(1)
                import_node = MockNode(
                    type='import_declaration',
                    children=[],
                    start_point=(i, line.find('import')),
                    end_point=(i, len(line))
                )
                
                # Add module name as a child
                module_node = MockNode(
                    type='import_path_component',
                    children=[],
                    start_point=(i, line.find(module)),
                    end_point=(i, line.find(module) + len(module))
                )
                
                import_node.children.append(module_node)
                root.children.append(import_node)
        
        # Add function declarations
        func_pattern = r'func\s+(\w+)'
        for i, line in enumerate(lines):
            match = re.search(func_pattern, line)
            if match:
                func_name = match.group(1)
                
                # Find the closing brace for this function
                end_line = i
                brace_count = 0
                for j in range(i, line_count):
                    if '{' in lines[j]:
                        brace_count += lines[j].count('{')
                    if '}' in lines[j]:
                        brace_count -= lines[j].count('}')
                    if brace_count <= 0 and '}' in lines[j]:
                        end_line = j
                        break
                
                func_node = MockNode(
                    type='function_declaration',
                    children=[],
                    start_point=(i, line.find('func')),
                    end_point=(end_line, len(lines[end_line]) if end_line < line_count else 0)
                )
                
                # Add function name as a child
                name_node = MockNode(
                    type='identifier',
                    children=[],
                    start_point=(i, line.find(func_name)),
                    end_point=(i, line.find(func_name) + len(func_name))
                )
                
                func_node.children.append(name_node)
                
                # Add parameter list if present
                if '(' in line:
                    param_start = line.find('(')
                    param_end = line.find(')')
                    if param_end > param_start:
                        param_clause = MockNode(
                            type='parameter_clause',
                            children=[],
                            start_point=(i, param_start),
                            end_point=(i, param_end + 1)
                        )
                        func_node.children.append(param_clause)
                
                # Add return type if present
                if '->' in line:
                    return_start = line.find('->') + 2
                    return_end = line.find('{', return_start)
                    if return_end == -1:
                        return_end = len(line)
                    return_type = line[return_start:return_end].strip()
                    
                    return_node = MockNode(
                        type='return_type',
                        children=[],
                        start_point=(i, return_start),
                        end_point=(i, return_start + len(return_type))
                    )
                    func_node.children.append(return_node)
                
                root.children.append(func_node)
        
        # Add class declarations
        class_pattern = r'class\s+(\w+)'
        for i, line in enumerate(lines):
            match = re.search(class_pattern, line)
            if match:
                class_name = match.group(1)
                
                # Find the closing brace for this class
                end_line = i
                brace_count = 0
                for j in range(i, line_count):
                    if '{' in lines[j]:
                        brace_count += lines[j].count('{')
                    if '}' in lines[j]:
                        brace_count -= lines[j].count('}')
                    if brace_count <= 0 and '}' in lines[j]:
                        end_line = j
                        break
                
                class_node = MockNode(
                    type='class_declaration',
                    children=[],
                    start_point=(i, line.find('class')),
                    end_point=(end_line, len(lines[end_line]) if end_line < line_count else 0)
                )
                
                # Add class name as a child
                name_node = MockNode(
                    type='identifier',
                    children=[],
                    start_point=(i, line.find(class_name)),
                    end_point=(i, line.find(class_name) + len(class_name))
                )
                
                class_node.children.append(name_node)
                
                # Add inheritance if present
                if ':' in line:
                    inherit_start = line.find(':') + 1
                    inherit_end = line.find('{', inherit_start)
                    if inherit_end == -1:
                        inherit_end = len(line)
                    inherit_text = line[inherit_start:inherit_end].strip()
                    
                    inherit_node = MockNode(
                        type='inheritance_clause',
                        children=[],
                        start_point=(i, inherit_start),
                        end_point=(i, inherit_start + len(inherit_text))
                    )
                    
                    # Add each inherited type
                    for inherited_type in inherit_text.split(','):
                        inherited_type = inherited_type.strip()
                        type_start = inherit_start + inherit_text.find(inherited_type)
                        
                        type_node = MockNode(
                            type='type_identifier',
                            children=[],
                            start_point=(i, type_start),
                            end_point=(i, type_start + len(inherited_type))
                        )
                        inherit_node.children.append(type_node)
                    
                    class_node.children.append(inherit_node)
                
                # Add class body
                body_node = MockNode(
                    type='class_body',
                    children=[],
                    start_point=(i, line.find('{')),
                    end_point=(end_line, lines[end_line].find('}') + 1 if end_line < line_count else 0)
                )
                class_node.children.append(body_node)
                
                root.children.append(class_node)
        
        # Create and return the tree
        tree = MockTree(root_node=root)
        print(f"--- EXITING MockParser.parse SUCCESSFULLY (Swift) ---")
        return tree

    def _create_js_mock_tree(self, code_str):
        """Create a mock tree for JavaScript code.
        
        Args:
            code_str: JavaScript code as a string
            
        Returns:
            MockTree: Mock tree representing JavaScript code
        """
        # Similar implementation for JavaScript
        print("--- Creating JS mock tree ---")
        lines = code_str.split('\n')
        line_count = len(lines)
        
        # Create root node
        root = MockNode(
            type='program',
            children=[],
            start_point=(0, 0),
            end_point=(line_count, 0)
        )
        
        # Create a simpler tree for JS 
        # Add some basic nodes based on patterns in the code
        
        # Create and return the tree
        tree = MockTree(root_node=root)
        print(f"--- EXITING MockParser.parse SUCCESSFULLY (JS) ---")
        return tree

    def _create_generic_mock_tree(self, code_str):
        """Create a generic mock tree for any code.
        
        Args:
            code_str: Code as a string
            
        Returns:
            MockTree: Generic mock tree
        """
        print("--- Creating generic mock tree ---")
        lines = code_str.split('\n')
        line_count = len(lines)
        
        # Create root node
        root = MockNode(
            type='file',
            children=[],
            start_point=(0, 0),
            end_point=(line_count, 0)
        )
        
        # Create a simple tree with line nodes
        for i, line in enumerate(lines):
            if line.strip():  # Skip empty lines
                line_node = MockNode(
                    type='line',
                    children=[],
                    start_point=(i, 0),
                    end_point=(i, len(line))
                )
                root.children.append(line_node)
        
        # Create and return the tree
        tree = MockTree(root_node=root)
        print(f"--- EXITING MockParser.parse SUCCESSFULLY (Generic) ---")
        return tree

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