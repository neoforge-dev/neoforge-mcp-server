"""Tests for the JavaScript module resolver."""

import unittest
import tempfile
import os
from pathlib import Path
from server.code_understanding.module_resolver import ModuleResolver

class TestModuleResolver(unittest.TestCase):
    """Test cases for the ModuleResolver class."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.resolver = ModuleResolver(self.temp_dir)
        
        # Create test files
        self._create_test_files()
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def _create_test_files(self):
        """Create test JavaScript files with various import patterns."""
        # Create main.js
        main_content = """
        import { helper } from './utils/helper';
        import { Component } from 'react';
        import { asyncOperation } from './services/async';
        """
        self._write_file('main.js', main_content)
        
        # Create utils/helper.js
        helper_content = """
        import { format } from 'date-fns';
        
        export function helper() {
            return format(new Date(), 'yyyy-MM-dd');
        }
        """
        self._write_file('utils/helper.js', helper_content)
        
        # Create services/async.js
        async_content = """
        import { fetch } from 'node-fetch';
        
        export async function asyncOperation() {
            const response = await fetch('https://api.example.com');
            return response.json();
        }
        """
        self._write_file('services/async.js', async_content)
        
        # Create package.json
        package_json = {
            'dependencies': {
                'react': '^17.0.0',
                'date-fns': '^2.29.0',
                'node-fetch': '^2.6.0'
            }
        }
        self._write_file('package.json', str(package_json))
        
    def _write_file(self, rel_path: str, content: str):
        """Helper to write test files."""
        full_path = Path(self.temp_dir) / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        
    def test_resolve_import(self):
        """Test resolving import paths."""
        # Test relative import
        helper_path = self.resolver.resolve_import('./utils/helper', 'main.js')
        self.assertIsNotNone(helper_path)
        self.assertTrue(helper_path.exists())
        
        # Test package import
        react_path = self.resolver.resolve_import('react', 'main.js')
        self.assertIsNotNone(react_path)
        self.assertTrue(react_path.exists())
        
        # Test non-existent import
        invalid_path = self.resolver.resolve_import('./nonexistent', 'main.js')
        self.assertIsNone(invalid_path)
        
    def test_get_module_dependencies(self):
        """Test getting module dependencies."""
        deps = self.resolver.get_module_dependencies('main.js')
        
        # Check direct dependencies
        self.assertEqual(len(deps['direct']), 3)
        self.assertIn('utils/helper.js', deps['direct'])
        self.assertIn('services/async.js', deps['direct'])
        
        # Check transitive dependencies
        self.assertGreater(len(deps['transitive']), 0)
        
    def test_get_module_graph(self):
        """Test generating module dependency graph."""
        graph = self.resolver.get_module_graph()
        
        # Check nodes
        self.assertEqual(len(graph['nodes']), 3)  # main.js, helper.js, async.js
        
        # Check edges
        self.assertEqual(len(graph['edges']), 3)  # main.js -> helper.js, main.js -> async.js, helper.js -> date-fns
        
    def test_find_circular_dependencies(self):
        """Test finding circular dependencies."""
        # Create circular dependency
        circular_content = """
        import { circular } from './circular';
        export function circular() {}
        """
        self._write_file('circular.js', circular_content)
        
        cycles = self.resolver.find_circular_dependencies()
        self.assertEqual(len(cycles), 1)
        
    def test_get_module_stats(self):
        """Test getting module statistics."""
        stats = self.resolver.get_module_stats()
        
        # Check basic stats
        self.assertEqual(stats['total_modules'], 3)
        self.assertGreater(stats['total_dependencies'], 0)
        
        # Check module types
        self.assertEqual(stats['module_types']['.js'], 3)
        
        # Check dependency counts
        self.assertGreater(len(stats['dependency_counts']), 0)
        
    def test_resolve_package_import(self):
        """Test resolving package imports."""
        # Test existing package
        react_path = self.resolver._resolve_package_import('react')
        self.assertIsNotNone(react_path)
        
        # Test non-existent package
        invalid_path = self.resolver._resolve_package_import('nonexistent-package')
        self.assertIsNone(invalid_path)
        
    def test_extension_resolution(self):
        """Test resolving imports with different extensions."""
        # Create TypeScript file
        ts_content = "export const tsHelper = () => {};"
        self._write_file('utils/helper.ts', ts_content)
        
        # Test resolving .ts extension
        ts_path = self.resolver.resolve_import('./utils/helper', 'main.js')
        self.assertIsNotNone(ts_path)
        self.assertEqual(ts_path.suffix, '.ts')
        
    def test_index_file_resolution(self):
        """Test resolving index file imports."""
        # Create index.js
        index_content = "export const indexHelper = () => {};"
        self._write_file('utils/index.js', index_content)
        
        # Test resolving directory import
        index_path = self.resolver.resolve_import('./utils', 'main.js')
        self.assertIsNotNone(index_path)
        self.assertEqual(index_path.name, 'index.js')
        
    def test_dynamic_imports(self):
        """Test resolving dynamic imports."""
        # Create file with dynamic import
        dynamic_content = """
        const loadModule = () => import('./dynamic');
        """
        self._write_file('dynamic.js', dynamic_content)
        
        # Test resolving dynamic import
        deps = self.resolver.get_module_dependencies('dynamic.js')
        self.assertEqual(len(deps['direct']), 0)  # Dynamic imports are not included in static analysis 