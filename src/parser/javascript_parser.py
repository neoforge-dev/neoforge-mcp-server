from typing import Set, Optional
from tree_sitter import Node, Tree

class JavaScriptParser:
    """Parser for JavaScript code using tree-sitter."""
    
    def __init__(self):
        self.exported_symbols: Set[str] = set()
        self.imported_symbols: Set[str] = set()
        
    def parse(self, tree: Tree) -> None:
        """Parse the AST and extract exported and imported symbols."""
        root = tree.root_node
        if not root:
            return
            
        self._parse_node(root)
        
    def _parse_node(self, node: Node) -> None:
        """Recursively parse a node and its children."""
        if not node:
            return
            
        # Handle export declarations
        if node.type == 'export_statement':
            self._parse_export_declaration(node)
        # Handle import declarations
        elif node.type == 'import_statement':
            self._parse_import_declaration(node)
            
        # Recursively parse children
        for child in node.children:
            self._parse_node(child)
            
    def _parse_export_declaration(self, node: Node) -> None:
        """Parse an export declaration."""
        if not node.children:
            return
            
        # Get the exported declaration
        decl_node = node.children[0]
        if not decl_node.children:
            return
            
        # Get the actual declaration (function, class, etc.)
        actual_decl = decl_node.children[0]
        if not actual_decl.children:
            return
            
        # Get the identifier
        identifier_node = actual_decl.children[0]
        if not identifier_node.children:
            return
            
        # Get the name
        name_node = identifier_node.children[0]
        if not name_node.children:
            return
            
        name = name_node.children[0].text.decode()
        self.exported_symbols.add(name)
        
    def _parse_import_declaration(self, node: Node) -> None:
        """Parse an import declaration."""
        if not node.children:
            return
            
        # Get the import specifiers
        specifiers = node.children[1:]
        for specifier in specifiers:
            if not specifier.children:
                continue
                
            # Get the imported name
            name_node = specifier.children[0]
            if not name_node.children:
                continue
                
            name = name_node.children[0].text.decode()
            self.imported_symbols.add(name)
            
    def get_exported_symbols(self) -> Set[str]:
        """Get the set of exported symbols."""
        return self.exported_symbols
        
    def get_imported_symbols(self) -> Set[str]:
        """Get the set of imported symbols."""
        return self.imported_symbols 