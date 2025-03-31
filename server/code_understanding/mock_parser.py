"""Mock parser for testing purposes."""

from typing import Any, Optional, List, Dict, Tuple
import ast
import logging

logger = logging.getLogger(__name__)

class MockNode:
    """Mock node for testing."""
    def __init__(self, type: str, text: str = "", start_point: tuple = (0, 0), end_point: tuple = (0, 0), children: List['MockNode'] = None, fields: Dict[str, Any] = None):
        self.type = type
        self.text = text
        self.start_point = start_point
        self.end_point = end_point
        self.children = children or []
        self.fields = fields or {}

    def child_by_field_name(self, name: str) -> Optional['MockNode']:
        """Get child by field name."""
        return next((child for child in self.children if child.type == name), None)

    def children_by_field_name(self, name: str) -> List['MockNode']:
        """Get children by field name."""
        return [child for child in self.children if child.type == name]

class MockTree:
    """Mock tree for testing."""
    def __init__(self, root_node: MockNode):
        self.root_node = root_node

class MockParser:
    """Mock parser for testing."""
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
            if node.type == 'import_statement':
                for child in node.children:
                    symbols['imports'].append({
                        'type': 'import',
                        'module': child.text,
                        'start_line': node.start_point[0],
                        'end_line': node.end_point[0]
                    })
            elif node.type == 'import_from_statement':
                module = next((child.text for child in node.children if child.type == 'dotted_name'), '')
                for child in node.children:
                    if child.type == 'identifier':
                        symbols['imports'].append({
                            'type': 'import',
                            'module': module,
                            'symbol': child.text,
                            'start_line': node.start_point[0],
                            'end_line': node.end_point[0]
                        })
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
                symbols['functions'].append({
                    'type': 'function',
                    'name': name,
                    'parameters': params,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0]
                })
                old_scope = current_scope
                current_scope = name
                for child in node.children:
                    if child.type == 'body':
                        for child_node in child.children:
                            process_node(child_node)
                current_scope = old_scope
            elif node.type == 'class_definition':
                name = node.text
                methods = []
                bases = []
                for child in node.children:
                    if child.type == 'bases':
                        bases.extend([base.text for base in child.children if base.type == 'identifier'])
                    elif child.type == 'body':
                        for method in child.children:
                            if method.type == 'function_definition':
                                methods.append({
                                    'name': method.text,
                                    'start_line': method.start_point[0] + 1,
                                    'end_line': method.end_point[0]
                                })
                symbols['classes'].append({
                    'type': 'class',
                    'name': name,
                    'bases': bases,
                    'methods': methods,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0]
                })
                old_scope = current_scope
                current_scope = name
                for child in node.children:
                    if child.type == 'body':
                        for child_node in child.children:
                            process_node(child_node)
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

            for child in node.children:
                process_node(child)

        process_node(tree.root_node)

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
            return MockNode(
                type='import_statement', 
                text=f"import {', '.join(names)}", 
                start_point=(node.lineno - 1, 0), 
                end_point=(node.lineno - 1, len(f"import {', '.join(names)}")), 
                children=[MockNode('identifier', text=name) for name in names]
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            level = node.level # Get the relative import level
            
            # Prepend dots for relative imports
            relative_prefix = '.' * level
            full_module_name = f"{relative_prefix}{module}"
            
            names = [name.name for name in node.names]
            
            # Create the module node with the full name including dots
            module_node = MockNode('dotted_name', text=full_module_name)
            
            return MockNode(
                type='import_from_statement', 
                text=f"from {full_module_name} import {', '.join(names)}", # Use full name in text too
                start_point=(node.lineno - 1, 0), 
                end_point=(node.lineno - 1, len(f"from {full_module_name} import {', '.join(names)}")), 
                children=[
                    module_node,
                    *[MockNode('identifier', text=name) for name in names]
                ]
            )
        elif isinstance(node, ast.FunctionDef):
            params = []
            for arg in node.args.args:
                params.append(MockNode('identifier', text=arg.arg, start_point=(node.lineno, 0), end_point=(node.lineno, len(arg.arg))))
            
            body_nodes = []
            for child in node.body:
                if isinstance(child, ast.Return):
                    if isinstance(child.value, ast.Call):
                        body_nodes.append(self._convert_ast_node(child.value))
                    else:
                        body_nodes.append(self._convert_ast_node(child))
                else:
                    body_nodes.append(self._convert_ast_node(child))
            
            return MockNode('function_definition', text=node.name, start_point=(node.lineno, 0), end_point=(node.end_lineno, 0), children=[
                MockNode('name', text=node.name),
                MockNode('parameters', children=params),
                MockNode('body', children=body_nodes)
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