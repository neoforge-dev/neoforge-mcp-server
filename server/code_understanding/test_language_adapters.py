import pytest
from .language_adapters import JavaScriptParserAdapter

@pytest.fixture
def js_parser():
    return JavaScriptParserAdapter()

def test_empty_input(js_parser):
    """Test handling of empty input"""
    result = js_parser.parse("")
    assert not result.has_errors
    assert result.features['imports'] == []
    assert result.features['functions'] == []
    assert result.features['classes'] == []
    assert result.features['variables'] == []
    assert result.features['exports'] == []

def test_es6_imports(js_parser):
    """Test ES6 import statements"""
    code = """
    import defaultExport from 'module';
    import { named1, named2 } from 'module2';
    import defaultExport2, { named3 } from 'module3';
    """
    result = js_parser.parse(code)
    assert not result.has_errors
    
    imports = result.features['imports']
    assert len(imports) == 4
    
    # Check default import
    default_import = next(i for i in imports if i['name'] == 'defaultExport')
    assert default_import['type'] == 'import'
    assert default_import['module'] == 'module'
    assert default_import['is_default'] == True
    
    # Check named imports
    named_imports = [i for i in imports if i['name'] in ['named1', 'named2']]
    assert len(named_imports) == 2
    assert all(i['type'] == 'import' and not i['is_default'] for i in named_imports)
    
    # Check mixed import
    mixed_import = next(i for i in imports if i['name'] == 'defaultExport2')
    assert mixed_import['is_default'] == True

def test_require_statements(js_parser):
    """Test CommonJS require statements"""
    code = """
    const module1 = require('module1');
    let module2 = require('module2');
    """
    result = js_parser.parse(code)
    assert not result.has_errors
    
    imports = result.features['imports']
    assert len(imports) == 2
    assert all(i['type'] == 'require' for i in imports)

def test_async_await(js_parser):
    """Test async/await patterns"""
    code = """
    async function fetchData() {
        const response = await fetch('api/data');
        return response.json();
    }
    
    class DataService {
        async getData() {
            const result = await this.fetchFromDB();
            return result;
        }
    }
    """
    result = js_parser.parse(code)
    assert not result.has_errors
    
    functions = result.features['functions']
    assert len(functions) == 2
    assert all(f['is_async'] for f in functions)
    
    classes = result.features['classes']
    assert len(classes) == 1
    assert len(classes[0]['methods']) == 1
    assert classes[0]['methods'][0]['is_async']

def test_decorators(js_parser):
    """Test class and method decorators"""
    code = """
    @decorator
    class Example {
        @methodDecorator
        method() {}
        
        @propertyDecorator
        property = 'value';
    }
    """
    result = js_parser.parse(code)
    assert not result.has_errors
    
    classes = result.features['classes']
    assert len(classes) == 1
    assert len(classes[0]['methods']) == 1

def test_class_fields(js_parser):
    """Test class fields and methods"""
    code = """
    class Example {
        static field = 'static';
        instanceField = 'instance';
        
        static method() {}
        instanceMethod() {}
        
        #privateField = 'private';
        #privateMethod() {}
    }
    """
    result = js_parser.parse(code)
    assert not result.has_errors
    
    classes = result.features['classes']
    assert len(classes) == 1
    methods = classes[0]['methods']
    assert len(methods) == 4
    assert any(m['is_static'] for m in methods)

def test_modern_features(js_parser):
    """Test modern JavaScript features"""
    code = """
    // Optional chaining
    const value = obj?.prop?.method?.();
    
    // Nullish coalescing
    const name = user.name ?? 'Anonymous';
    
    // Dynamic imports
    const module = await import('module');
    
    // Top-level await
    const data = await fetch('api/data');
    
    // Private class fields
    class Example {
        #private = 'private';
    }
    """
    result = js_parser.parse(code)
    assert not result.has_errors

def test_error_handling(js_parser):
    """Test error handling for malformed code"""
    code = """
    import { from 'module';  // Missing identifier
    class {  // Missing class name
        method()
    }
    """
    result = js_parser.parse(code)
    assert result.has_errors
    assert len(result.error_details) > 0
    assert all('message' in error for error in result.error_details)

def test_exports(js_parser):
    """Test export statements"""
    code = """
    export const name = 'value';
    export default class Example {}
    export { name1, name2 };
    """
    result = js_parser.parse(code)
    assert not result.has_errors
    
    exports = result.features['exports']
    assert len(exports) == 4
    assert any(e['is_default'] for e in exports)

def test_variable_declarations(js_parser):
    """Test variable declarations"""
    code = """
    const immutable = 'value';
    let mutable = 'value';
    var oldStyle = 'value';
    """
    result = js_parser.parse(code)
    assert not result.has_errors
    
    variables = result.features['variables']
    assert len(variables) == 3
    assert any(v['is_const'] for v in variables) 