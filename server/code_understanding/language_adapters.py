'''Language-specific parser adapters for JavaScript and Swift.'''

import ast
import re
from typing import Optional, Dict, Any, List
from tree_sitter import Language, Parser, Tree, Node
import logging # Add logging
import subprocess # For building grammar
import os # For path checks
from pathlib import Path # For path handling

# Import common Mock structure
from .common_types import MockTree, MockNode

logger = logging.getLogger(__name__)

# Define Tree-sitter query strings (or load from .scm files)
# Updated JS Import/Require Queries V5
# Trying to combine default and named captures more reliably
JS_IMPORT_QUERY = """
(import_statement
  source: (string) @source
  [
    (import_clause (identifier) @default_import)
    (import_clause (named_imports (import_specifier name: (identifier) @named_import)*))
  ]* @clauses
)
"""
# Query for require() call - run on the call_expression node
JS_REQUIRE_QUERY = """
(call_expression
  function: (identifier) @require_func
  arguments: (arguments (string) @source)
  (#match? @require_func "^require$") 
)
"""
# Add other queries (export, symbol) if needed for conversion logic

class JavaScriptParserAdapter:
    """JavaScript parser adapter using tree-sitter for robust parsing."""
    
    def __init__(self):
        """Initialize the JavaScript parser adapter."""
        self.parser = Parser()
        self.language = None
        # Store compiled queries if needed for conversion
        self.import_query = None
        self.require_query = None
        # Add others like symbol_query if needed
        self._load_language_and_queries()
        
    def _load_language_and_queries(self):
        """Load the tree-sitter JS language and compile queries."""
        try:
            # Robust grammar loading/building logic from javascript_parser.py
            vendor_path = Path(__file__).parent.parent.parent / 'vendor' / 'tree-sitter-javascript'
            # Standard location for compiled library might be just 'languages.so' 
            # or a specific name in a build/dist dir. Adjust as needed.
            # Let's try a common pattern: build/<lang_name>.so
            build_dir = Path(__file__).parent / 'build'
            language_lib = build_dir / 'javascript.so' 
            
            # Ensure build directory exists
            build_dir.mkdir(exist_ok=True)

            # Clone the repository if grammar source doesn't exist
            if not (vendor_path / 'src' / 'parser.c').exists():
                if vendor_path.exists(): # Clean up if incomplete clone exists
                     try: subprocess.run(['rm', '-rf', str(vendor_path)], check=True)
                     except: pass # Ignore errors
                logger.info("Cloning tree-sitter-javascript repository...")
                # Use https instead of ssh for broader compatibility
                subprocess.run(['git', 'clone', 'https://github.com/tree-sitter/tree-sitter-javascript.git', str(vendor_path)], check=True, capture_output=True)
            
            # Build the language library if it doesn't exist or is older than source
            needs_build = True
            if language_lib.exists() and vendor_path.exists():
                src_mtime = max(p.stat().st_mtime for p in vendor_path.glob('src/*.[ch]'))
                if language_lib.stat().st_mtime >= src_mtime:
                    needs_build = False
            
            if needs_build:
                logger.info(f"Building tree-sitter-javascript library to {language_lib}...")
                try:
                    # Use the Language.build_library method for simplicity
                    Language.build_library(
                        str(language_lib),
                        [str(vendor_path)] # Must be list of directories
                    )
                    logger.info("Successfully built tree-sitter-javascript library.")
                except Exception as e:
                    logger.error(f"Failed to build JS grammar using build_library: {e}")
                    # Optional: Add fallback to manual compile steps if needed
                    raise # Reraise to signal failure
            
            # Load the language
            self.language = Language(str(language_lib), 'javascript')
            self.parser.set_language(self.language)
            logger.info("JavaScript language loaded successfully.")
            
            # Compile queries needed for conversion
            self.import_query = self.language.query(JS_IMPORT_QUERY)
            self.require_query = self.language.query(JS_REQUIRE_QUERY) # Compile require query
            # Compile other queries if needed
            logger.info("JavaScript queries compiled.")
            
        except Exception as e:
            logger.exception(f"Error loading JavaScript language or queries: {e}")
            self.language = None # Ensure language is None if loading failed
            # Do not raise here; CodeParser should handle the lack of a language

    def parse(self, code: str) -> Optional[MockTree]:
        """Parse JavaScript code into a MockTree using tree-sitter."""
        if not self.language:
            logger.error("JavaScript language not loaded for adapter. Cannot parse.")
            raise RuntimeError("JavaScript language not loaded for adapter.")

        # Validate input before the main try block
        if isinstance(code, bytes):
            try:
                 code = code.decode('utf-8')
            except UnicodeDecodeError as e:
                 logger.error(f"Failed to decode input bytes: {e}")
                 raise ValueError("Input code is not valid UTF-8") from e

        # Raise ValueError for empty or whitespace-only code
        if not code.strip():
            raise ValueError("Input code cannot be empty or whitespace only.")

        # Now, proceed with parsing inside the try block
        try:
            tree = self.parser.parse(bytes(code, 'utf8'))
            root_ts_node = tree.root_node
            
            # Optional: Check for errors, but proceed anyway for partial analysis
            if root_ts_node.has_error:
                logger.warning("JS Parsing resulted in errors. Analysis might be incomplete.")
                # Find first error node for logging
                error_node = next((n for n in root_ts_node.descendants if n.has_error), root_ts_node)
                logger.warning(f"First error node: type={error_node.type}, pos={error_node.start_point}")

            # Convert the tree-sitter tree to our MockTree structure
            mock_root = self._tree_sitter_to_mock_node(root_ts_node)
            if mock_root:
                 return MockTree(root=mock_root)
            else:
                 logger.error("Conversion from Tree-sitter to MockNode failed for JS root.")
                 return None
        
        except Exception as e:
            logger.exception(f"Error parsing JS code: {e}")
            return None
            
    def _tree_sitter_to_mock_node(self, ts_node: Node) -> Optional[MockNode]:
         """Recursively convert a tree-sitter node to a MockNode."""
         if not ts_node:
             return None

         node_type = ts_node.type
         # --- Program Node Handling --- 
         if node_type == 'program':
              mock_type = 'program'
              start_point = ts_node.start_point
              end_point = ts_node.end_point
              children = []
              fields = {}
              for child_node in ts_node.children:
                   child_mock = self._tree_sitter_to_mock_node(child_node) # Recursive call first
                   if child_mock:
                        children.append(child_mock)
              return MockNode(type=mock_type, text=mock_type, start_point=start_point, end_point=end_point, children=children, fields=fields)

         # --- Specific Node Type Conversions --- 
         elif node_type == 'import_statement':
             return self._convert_import_statement(ts_node)
         # Let _convert_variable_declarator handle require check internally
         elif node_type == 'variable_declaration' or node_type == 'lexical_declaration':
             return self._convert_variable_declaration(ts_node)
         elif node_type == 'variable_declarator':
             return self._convert_variable_declarator(ts_node)
         elif node_type == 'function_declaration':
             return self._convert_function_definition(ts_node)
         elif node_type == 'class_declaration':
             return self._convert_class_definition(ts_node)
         elif node_type == 'method_definition':
              return self._convert_function_definition(ts_node) # Reuse func helper
         elif node_type == 'export_statement':
             return self._convert_export_statement(ts_node)
         # Arrow functions are usually values, handled in _convert_variable_declarator
         # If encountered elsewhere, convert generically? Or return None?
         elif node_type == 'arrow_function':
              return None # Skip standalone arrow funcs for now
         else:
             # Default: Convert generically ONLY if not handled above
             return self._convert_node_generically(ts_node)

    # --- Refactored Helper Methods --- 
    
    def _convert_import_statement(self, ts_node: Node) -> Optional[MockNode]:
         """Converts a tree-sitter import_statement node."""
         if ts_node.type != 'import_statement': return None
         
         mock_type = 'import_statement'
         start_point=ts_node.start_point
         end_point=ts_node.end_point
         children = [] 
         fields = {}
         source = "<unknown>"
         default_import_name = None
         named_imports = []
         
         captures = self.import_query.captures(ts_node)
         logger.debug(f"JS Import Captures ({ts_node.start_point}): {[(c[1], c[0].text) for c in captures]}")
         for captured_node, capture_name in captures:
             cap_text = captured_node.text.decode('utf-8')
             if capture_name == 'source': 
                 source = cap_text.strip('\'"')
                 fields['module'] = source 
             elif capture_name == 'default_import': 
                 default_import_name = cap_text
                 children.append(MockNode(type='identifier', text=cap_text))
                 fields['is_default'] = True 
             elif capture_name == 'named_import': 
                 named_imports.append(cap_text)
                 children.append(MockNode(type='identifier', text=cap_text))
         
         node_text = source 
         if default_import_name:
             fields['default_name'] = default_import_name 
         if named_imports:
             fields['named_names'] = named_imports 
             
         if fields.get('module'):
              return MockNode(type=mock_type, text=node_text, start_point=start_point, end_point=end_point, children=children, fields=fields)
         else:
              logger.warning(f"Could not extract source from import statement node: {ts_node.text.decode()}")
              return None

    def _create_require_mock_node(self, declarator_node: Node, captures: list) -> Optional[MockNode]:
          """Creates a require_statement MockNode from captures and the declarator node."""
          mock_type = 'require_statement'
          # Get position from the original declaration (parent of declarator)
          parent_node = declarator_node.parent 
          start_point = parent_node.start_point if parent_node else declarator_node.start_point
          end_point = parent_node.end_point if parent_node else declarator_node.end_point
          children = []
          fields = {}
          # Get variable name directly from the declarator node
          name_node_ts = declarator_node.child_by_field_name('name')
          req_var_name = name_node_ts.text.decode('utf-8') if name_node_ts else "<unknown>"
          fields['name'] = req_var_name 
          req_source = "<unknown>"
          
          # Get source from captures
          for captured_node, capture_name in captures:
               if capture_name == 'source': 
                    req_source = captured_node.text.decode('utf-8').strip('\'"')
                    fields['module'] = req_source
                    break # Should only be one source
          
          node_text = req_source 

          if fields.get('module') and fields.get('name') != "<unknown>":
               children.append(MockNode(type='identifier', text=fields['name']))
               children.append(MockNode(type='string', text=fields['module']))
               return MockNode(type=mock_type, text=node_text, start_point=start_point, end_point=end_point, children=children, fields=fields)
          else:
               logger.warning(f"Could not extract require parts. Name: {req_var_name}, Source: {req_source}, Node: {declarator_node.text.decode()}")
               return None

    def _convert_function_definition(self, ts_node: Node) -> Optional[MockNode]:
        """Converts function_declaration or method_definition."""
        if ts_node.type not in ['function_declaration', 'method_definition']: return None

        mock_type = 'function_definition'
        start_point=ts_node.start_point
        end_point=ts_node.end_point
        children = []
        fields = {}
        node_text = "<anonymous_func>"
        
        name_node_ts = ts_node.child_by_field_name('name')
        params_node_ts = ts_node.child_by_field_name('parameters')
        body_node_ts = ts_node.child_by_field_name('body')
        
        if name_node_ts: 
            fields['name'] = self._convert_node_generically(name_node_ts)
            if fields['name']: node_text = fields['name'].text
        if ts_node.type == 'method_definition' and 'static' in [c.type for c in ts_node.children]:
            fields['is_static'] = True
        if params_node_ts: 
            params_mock = self._convert_node_generically(params_node_ts)
            if params_mock: children.append(params_mock)
        if body_node_ts: 
             body_mock = self._convert_node_generically(body_node_ts)
             if body_mock: children.append(body_mock)
             
        return MockNode(type=mock_type, text=node_text, start_point=start_point, end_point=end_point, children=children, fields=fields)
        
    def _convert_arrow_function(self, ts_node: Node, assigned_name: Optional[str]=None) -> Optional[MockNode]:
         """Converts an arrow_function node."""
         # Usually found as value in variable_declarator
         if ts_node.type != 'arrow_function': return None
         
         mock_type = 'function_definition' # Treat as function
         start_point=ts_node.start_point
         end_point=ts_node.end_point
         children = []
         fields = {}
         node_text = assigned_name or "<anonymous_arrow>"
         if assigned_name: fields['name'] = MockNode(type='identifier', text=assigned_name)
         
         params_node_ts = ts_node.child_by_field_name('parameters')
         body_node_ts = ts_node.child_by_field_name('body')
         if params_node_ts: 
            params_mock = self._convert_node_generically(params_node_ts)
            if params_mock: children.append(params_mock)
         if body_node_ts: 
             body_mock = self._convert_node_generically(body_node_ts)
             if body_mock: children.append(body_mock)
             
         return MockNode(type=mock_type, text=node_text, start_point=start_point, end_point=end_point, children=children, fields=fields)
         
    def _convert_class_definition(self, ts_node: Node) -> Optional[MockNode]:
         """Converts a class_declaration node."""
         if ts_node.type != 'class_declaration': return None
         
         mock_type = 'class_definition'
         start_point=ts_node.start_point
         end_point=ts_node.end_point
         children = []
         fields = {}
         node_text = "<anonymous_class>"
         
         name_node_ts = ts_node.child_by_field_name('name')
         body_node_ts = ts_node.child_by_field_name('body') 
         if name_node_ts: 
             fields['name'] = self._convert_node_generically(name_node_ts)
             if fields['name']: node_text = fields['name'].text
         if body_node_ts: 
             body_mock = self._convert_node_generically(body_node_ts)
             if body_mock: children.append(body_mock)
             
         return MockNode(type=mock_type, text=node_text, start_point=start_point, end_point=end_point, children=children, fields=fields)

    def _convert_variable_declaration(self, ts_node: Node) -> Optional[MockNode]:
         """Converts variable_declaration or lexical_declaration.
            Returns a wrapper node containing converted declarators.
         """
         if ts_node.type not in ['variable_declaration', 'lexical_declaration']: return None
         
         mock_type = 'variable_declaration' # Unified type
         start_point=ts_node.start_point; end_point=ts_node.end_point
         children = [] # Store converted declarator nodes
         
         for child_node in ts_node.children:
              if child_node.type == 'variable_declarator':
                   decl_mock = self._convert_variable_declarator(child_node)
                   if decl_mock: children.append(decl_mock)
         
         if not children: return None # Skip empty declarations (e.g., just 'var;')
         # Return a single 'variable_declaration' node wrapping the declarators
         return MockNode(type=mock_type, text=ts_node.type, start_point=start_point, end_point=end_point, children=children)

    def _convert_variable_declarator(self, ts_node: Node) -> Optional[MockNode]:
        """Converts a variable_declarator node. 
           Checks if value is require() or arrow func.
           Returns require_statement, function_definition, or variable_declarator MockNode.
        """
        if ts_node.type != 'variable_declarator': return None
        
        name_node_ts = ts_node.child_by_field_name('name')
        value_node_ts = ts_node.child_by_field_name('value')
        assigned_name = name_node_ts.text.decode('utf-8') if name_node_ts else None

        # --- Check for require --- 
        if value_node_ts and value_node_ts.type == 'call_expression':
            captures = self.require_query.captures(value_node_ts) 
            if captures:
                # Pass the name and source from captures and declarator node
                return self._create_require_mock_node(ts_node, captures)
                
        # --- Check for arrow function --- 
        if value_node_ts and value_node_ts.type == 'arrow_function':
             return self._convert_arrow_function(value_node_ts, assigned_name=assigned_name)
        
        # --- Otherwise, handle as a regular variable declarator --- 
        mock_type = 'variable_declarator' 
        start_point=ts_node.start_point; end_point=ts_node.end_point
        children = [] ; fields = {}
        node_text = assigned_name or "<declarator>"

        if name_node_ts:
             name_mock = self._convert_node_generically(name_node_ts)
             if name_mock: fields['name'] = name_mock
                  
        if value_node_ts:
            value_mock = self._convert_node_generically(value_node_ts)
            if value_mock: fields['value'] = value_mock
                     
        return MockNode(type=mock_type, text=node_text, start_point=start_point, end_point=end_point, children=children, fields=fields)
        
    def _convert_export_statement(self, ts_node: Node) -> Optional[MockNode]:
         """Converts an export_statement node.
            Returns the converted *exported item* (marked) or a special node for named lists.
         """
         if ts_node.type != 'export_statement': return None

         is_default = any(c.type == 'default' for c in ts_node.children)
         export_clause = next((c for c in ts_node.children if c.type == 'export_clause'), None)
         exported_node_ts = ts_node.named_children[0] if ts_node.named_child_count > 0 and not export_clause else None

         # Handle `export { name1, name2 };`
         if export_clause: 
             exported_names = []
             source_node = export_clause.child_by_field_name('source') # Handle export * from 'module'
             source = source_node.text.decode('utf-8').strip('"\'') if source_node else None

             for specifier in export_clause.children:
                 if specifier.type == 'export_specifier':
                      name_node = specifier.child_by_field_name('name')
                      alias_node = specifier.child_by_field_name('alias')
                      name = name_node.text.decode('utf-8') if name_node else None
                      alias = alias_node.text.decode('utf-8') if alias_node else None
                      if name: exported_names.append({'name': name, 'alias': alias})
                          
             if not exported_names and not source: return None # Skip empty/unknown exports
             
             mock_type = 'export_named_list' 
             node_text = ", ".join([e['alias'] or e['name'] for e in exported_names]) + (f" from {source}" if source else "")
             fields = {'names': exported_names, 'source': source, 'is_default': is_default}
             children = [MockNode(type='identifier', text=e['alias'] or e['name']) for e in exported_names]
             return MockNode(type=mock_type, text=node_text, start_point=ts_node.start_point, end_point=ts_node.end_point, children=children, fields=fields)
         
         # Handle `export default ...`, `export function/class/const ...`
         elif exported_node_ts:
             export_mock = self._tree_sitter_to_mock_node(exported_node_ts)
             if export_mock:
                  # Mark the converted node itself as exported
                  export_mock.fields['is_exported'] = True
                  if is_default: export_mock.fields['is_default_export'] = True
                  return export_mock # Return the converted exported item
             else:
                  logger.warning(f"Failed to convert node inside export statement: {exported_node_ts.type}")
                  return None # Failed to convert exported item
         else: 
              logger.warning(f"Unhandled export statement structure: {ts_node.text.decode()}")
              return self._convert_node_generically(ts_node)

    def _convert_node_generically(self, ts_node: Node) -> Optional[MockNode]:
        """Generic fallback conversion for unhandled nodes, focusing on children."""
        if not ts_node: return None
        
        node_type = ts_node.type
        # Skip trivial types more broadly
        if not ts_node.is_named or node_type in ['comment', ';', '{ ', '}', '(', ')', ',', ':', '[', ']']: 
            return None
        
        # Use mapped type if available
        type_map = { 'program': 'module', 'property_identifier': 'identifier', 'formal_parameters': 'parameters', 'statement_block': 'body'} # Basic map
        mock_type = type_map.get(node_type, node_type)
        
        node_text = ts_node.text.decode('utf-8')
        start_point = ts_node.start_point
        end_point = ts_node.end_point
        children = []
        fields = {} # Keep fields empty for generic nodes

        # Recursively convert *named* children only for generic case to reduce noise
        for child_ts_node in ts_node.named_children:
            mock_child = self._tree_sitter_to_mock_node(child_ts_node) # Call main recursive func
            if mock_child:
                children.append(mock_child)
                
        # Create node even if children list is empty, if it's a potentially meaningful type
        # Refine the list of types to potentially skip if they have no children
        skip_if_empty = ['expression_statement', 'parenthesized_expression'] 
        if children or mock_type not in skip_if_empty:
            return MockNode(
                type=mock_type, 
                text=node_text, 
                start_point=start_point, 
                end_point=end_point, 
                children=children,
                fields=fields
            )
        else:
            # Log skipped nodes if needed for debugging
            # logger.debug(f"Skipping generic node conversion for type {mock_type} with no children: {node_text[:50]}...")
            return None

class SwiftParserAdapter:
    def parse(self, code: str) -> Optional[MockTree]:
        if not code or code.strip() == '':
            raise ValueError("Input code cannot be empty or whitespace only.")
        # For now, bypass validation and return a mock tree with a 'source_file' root node
        logger.warning("Swift parsing not implemented, returning basic mock tree.")
        root = MockNode(type='source_file', text='source_file')
        return MockTree(root) 