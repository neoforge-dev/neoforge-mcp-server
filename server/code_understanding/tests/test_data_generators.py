"""
Test data generators for code understanding tests.
Provides generators for Python, JavaScript, and Swift code samples.
"""

import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    SWIFT = "swift"

@dataclass
class CodeSample:
    """Represents a generated code sample."""
    language: Language
    code: str
    description: str
    expected_symbols: List[Dict[str, Any]]
    expected_relationships: List[Dict[str, Any]]
    complexity: str  # "simple", "medium", "complex"

class CodeGenerator:
    """Base class for code generators."""
    
    def __init__(self):
        self.var_names = ["x", "y", "z", "count", "result", "value", "data", "item"]
        self.func_names = ["process", "calculate", "transform", "validate", "handle"]
        self.class_names = ["Processor", "Calculator", "Transformer", "Validator"]
        
    def generate_var_name(self) -> str:
        """Generate a random variable name."""
        return random.choice(self.var_names)
    
    def generate_func_name(self) -> str:
        """Generate a random function name."""
        return random.choice(self.func_names)
    
    def generate_class_name(self) -> str:
        """Generate a random class name."""
        return random.choice(self.class_names)

class PythonGenerator(CodeGenerator):
    """Generator for Python code samples."""
    
    def generate_simple_function(self) -> CodeSample:
        """Generate a simple Python function."""
        func_name = self.generate_func_name()
        var_name = self.generate_var_name()
        code = f"""
def {func_name}({var_name}):
    result = {var_name} * 2
    return result
"""
        return CodeSample(
            language=Language.PYTHON,
            code=code,
            description="Simple function with parameter and return",
            expected_symbols=[
                {"name": func_name, "type": "function", "scope": "module"},
                {"name": var_name, "type": "parameter", "scope": func_name},
                {"name": "result", "type": "variable", "scope": func_name}
            ],
            expected_relationships=[
                {"type": "defines", "source": func_name, "target": var_name},
                {"type": "defines", "source": func_name, "target": "result"}
            ],
            complexity="simple"
        )
    
    def generate_class_with_methods(self) -> CodeSample:
        """Generate a Python class with methods."""
        class_name = self.generate_class_name()
        method_name = self.generate_func_name()
        var_name = self.generate_var_name()
        code = f"""
class {class_name}:
    def __init__(self, {var_name}):
        self.{var_name} = {var_name}
    
    def {method_name}(self):
        return self.{var_name} * 2
"""
        return CodeSample(
            language=Language.PYTHON,
            code=code,
            description="Class with constructor and method",
            expected_symbols=[
                {"name": class_name, "type": "class", "scope": "module"},
                {"name": "__init__", "type": "method", "scope": class_name},
                {"name": method_name, "type": "method", "scope": class_name},
                {"name": var_name, "type": "parameter", "scope": "__init__"},
                {"name": f"self.{var_name}", "type": "instance_variable", "scope": class_name}
            ],
            expected_relationships=[
                {"type": "defines", "source": class_name, "target": "__init__"},
                {"type": "defines", "source": class_name, "target": method_name},
                {"type": "defines", "source": "__init__", "target": var_name}
            ],
            complexity="medium"
        )
    
    def generate_complex_module(self) -> CodeSample:
        """Generate a complex Python module with imports and multiple components."""
        code = """
import os
from typing import List, Dict

class DataProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data: List[int] = []
    
    def process(self, input_data: List[int]) -> List[int]:
        result = []
        for item in input_data:
            if item > 0:
                result.append(item * 2)
        return result

def main():
    processor = DataProcessor({"threshold": 0})
    data = [1, 2, 3, -1, -2]
    result = processor.process(data)
    print(result)

if __name__ == "__main__":
    main()
"""
        return CodeSample(
            language=Language.PYTHON,
            code=code,
            description="Complex module with imports, class, and main function",
            expected_symbols=[
                {"name": "os", "type": "module", "scope": "module"},
                {"name": "List", "type": "type", "scope": "module"},
                {"name": "Dict", "type": "type", "scope": "module"},
                {"name": "DataProcessor", "type": "class", "scope": "module"},
                {"name": "main", "type": "function", "scope": "module"},
                {"name": "config", "type": "parameter", "scope": "__init__"},
                {"name": "data", "type": "instance_variable", "scope": "DataProcessor"},
                {"name": "process", "type": "method", "scope": "DataProcessor"},
                {"name": "input_data", "type": "parameter", "scope": "process"},
                {"name": "result", "type": "variable", "scope": "process"},
                {"name": "item", "type": "variable", "scope": "process"},
                {"name": "processor", "type": "variable", "scope": "main"},
                {"name": "data", "type": "variable", "scope": "main"},
                {"name": "result", "type": "variable", "scope": "main"}
            ],
            expected_relationships=[
                {"type": "imports", "source": "module", "target": "os"},
                {"type": "imports", "source": "module", "target": "List"},
                {"type": "imports", "source": "module", "target": "Dict"},
                {"type": "defines", "source": "module", "target": "DataProcessor"},
                {"type": "defines", "source": "module", "target": "main"},
                {"type": "defines", "source": "DataProcessor", "target": "process"},
                {"type": "calls", "source": "main", "target": "DataProcessor"},
                {"type": "calls", "source": "main", "target": "process"}
            ],
            complexity="complex"
        )

class JavaScriptGenerator(CodeGenerator):
    """Generator for JavaScript code samples."""
    
    def generate_simple_function(self) -> CodeSample:
        """Generate a simple JavaScript function."""
        func_name = self.generate_func_name()
        var_name = self.generate_var_name()
        code = f"""
function {func_name}({var_name}) {{
    const result = {var_name} * 2;
    return result;
}}
"""
        return CodeSample(
            language=Language.JAVASCRIPT,
            code=code,
            description="Simple function with parameter and return",
            expected_symbols=[
                {"name": func_name, "type": "function", "scope": "module"},
                {"name": var_name, "type": "parameter", "scope": func_name},
                {"name": "result", "type": "variable", "scope": func_name}
            ],
            expected_relationships=[
                {"type": "defines", "source": func_name, "target": var_name},
                {"type": "defines", "source": func_name, "target": "result"}
            ],
            complexity="simple"
        )
    
    def generate_class_with_methods(self) -> CodeSample:
        """Generate a JavaScript class with methods."""
        class_name = self.generate_class_name()
        method_name = self.generate_func_name()
        var_name = self.generate_var_name()
        code = f"""
class {class_name} {{
    constructor({var_name}) {{
        this.{var_name} = {var_name};
    }}
    
    {method_name}() {{
        return this.{var_name} * 2;
    }}
}}
"""
        return CodeSample(
            language=Language.JAVASCRIPT,
            code=code,
            description="Class with constructor and method",
            expected_symbols=[
                {"name": class_name, "type": "class", "scope": "module"},
                {"name": "constructor", "type": "method", "scope": class_name},
                {"name": method_name, "type": "method", "scope": class_name},
                {"name": var_name, "type": "parameter", "scope": "constructor"},
                {"name": f"this.{var_name}", "type": "instance_variable", "scope": class_name}
            ],
            expected_relationships=[
                {"type": "defines", "source": class_name, "target": "constructor"},
                {"type": "defines", "source": class_name, "target": method_name},
                {"type": "defines", "source": "constructor", "target": var_name}
            ],
            complexity="medium"
        )
    
    def generate_complex_module(self) -> CodeSample:
        """Generate a complex JavaScript module with imports and multiple components."""
        code = """
import { process } from './utils.js';

class DataProcessor {
    constructor(config) {
        this.config = config;
        this.data = [];
    }
    
    async process(inputData) {
        const result = [];
        for (const item of inputData) {
            if (item > 0) {
                result.push(await process(item));
            }
        }
        return result;
    }
}

export const main = async () => {
    const processor = new DataProcessor({ threshold: 0 });
    const data = [1, 2, 3, -1, -2];
    const result = await processor.process(data);
    console.log(result);
};

if (import.meta.main) {
    main();
}
"""
        return CodeSample(
            language=Language.JAVASCRIPT,
            code=code,
            description="Complex module with imports, class, and async functions",
            expected_symbols=[
                {"name": "process", "type": "import", "scope": "module"},
                {"name": "DataProcessor", "type": "class", "scope": "module"},
                {"name": "main", "type": "function", "scope": "module"},
                {"name": "config", "type": "parameter", "scope": "constructor"},
                {"name": "data", "type": "instance_variable", "scope": "DataProcessor"},
                {"name": "process", "type": "method", "scope": "DataProcessor"},
                {"name": "inputData", "type": "parameter", "scope": "process"},
                {"name": "result", "type": "variable", "scope": "process"},
                {"name": "item", "type": "variable", "scope": "process"},
                {"name": "processor", "type": "variable", "scope": "main"},
                {"name": "data", "type": "variable", "scope": "main"},
                {"name": "result", "type": "variable", "scope": "main"}
            ],
            expected_relationships=[
                {"type": "imports", "source": "module", "target": "process"},
                {"type": "defines", "source": "module", "target": "DataProcessor"},
                {"type": "defines", "source": "module", "target": "main"},
                {"type": "defines", "source": "DataProcessor", "target": "process"},
                {"type": "calls", "source": "main", "target": "DataProcessor"},
                {"type": "calls", "source": "main", "target": "process"}
            ],
            complexity="complex"
        )

class SwiftGenerator(CodeGenerator):
    """Generator for Swift code samples."""
    
    def generate_simple_function(self) -> CodeSample:
        """Generate a simple Swift function."""
        func_name = self.generate_func_name()
        var_name = self.generate_var_name()
        code = f"""
func {func_name}(_ {var_name}: Int) -> Int {{
    let result = {var_name} * 2
    return result
}}
"""
        return CodeSample(
            language=Language.SWIFT,
            code=code,
            description="Simple function with parameter and return",
            expected_symbols=[
                {"name": func_name, "type": "function", "scope": "module"},
                {"name": var_name, "type": "parameter", "scope": func_name},
                {"name": "result", "type": "variable", "scope": func_name}
            ],
            expected_relationships=[
                {"type": "defines", "source": func_name, "target": var_name},
                {"type": "defines", "source": func_name, "target": "result"}
            ],
            complexity="simple"
        )
    
    def generate_class_with_methods(self) -> CodeSample:
        """Generate a Swift class with methods."""
        class_name = self.generate_class_name()
        method_name = self.generate_func_name()
        var_name = self.generate_var_name()
        code = f"""
class {class_name} {{
    private var {var_name}: Int
    
    init({var_name}: Int) {{
        self.{var_name} = {var_name}
    }}
    
    func {method_name}() -> Int {{
        return {var_name} * 2
    }}
}}
"""
        return CodeSample(
            language=Language.SWIFT,
            code=code,
            description="Class with initializer and method",
            expected_symbols=[
                {"name": class_name, "type": "class", "scope": "module"},
                {"name": "init", "type": "initializer", "scope": class_name},
                {"name": method_name, "type": "method", "scope": class_name},
                {"name": var_name, "type": "parameter", "scope": "init"},
                {"name": f"self.{var_name}", "type": "instance_variable", "scope": class_name}
            ],
            expected_relationships=[
                {"type": "defines", "source": class_name, "target": "init"},
                {"type": "defines", "source": class_name, "target": method_name},
                {"type": "defines", "source": "init", "target": var_name}
            ],
            complexity="medium"
        )
    
    def generate_complex_module(self) -> CodeSample:
        """Generate a complex Swift module with imports and multiple components."""
        code = """
import Foundation

protocol DataProcessable {
    func process(_ data: [Int]) async throws -> [Int]
}

class DataProcessor: DataProcessable {
    private let config: [String: Any]
    private var data: [Int] = []
    
    init(config: [String: Any]) {
        self.config = config
    }
    
    func process(_ inputData: [Int]) async throws -> [Int] {
        var result: [Int] = []
        for item in inputData where item > 0 {
            result.append(try await processItem(item))
        }
        return result
    }
    
    private func processItem(_ item: Int) async throws -> Int {
        return item * 2
    }
}

@main
struct Main {
    static func main() async throws {
        let processor = DataProcessor(config: ["threshold": 0])
        let data = [1, 2, 3, -1, -2]
        let result = try await processor.process(data)
        print(result)
    }
}
"""
        return CodeSample(
            language=Language.SWIFT,
            code=code,
            description="Complex module with protocol, class, and async functions",
            expected_symbols=[
                {"name": "Foundation", "type": "module", "scope": "module"},
                {"name": "DataProcessable", "type": "protocol", "scope": "module"},
                {"name": "DataProcessor", "type": "class", "scope": "module"},
                {"name": "Main", "type": "struct", "scope": "module"},
                {"name": "config", "type": "instance_variable", "scope": "DataProcessor"},
                {"name": "data", "type": "instance_variable", "scope": "DataProcessor"},
                {"name": "process", "type": "method", "scope": "DataProcessor"},
                {"name": "processItem", "type": "method", "scope": "DataProcessor"},
                {"name": "inputData", "type": "parameter", "scope": "process"},
                {"name": "result", "type": "variable", "scope": "process"},
                {"name": "item", "type": "variable", "scope": "process"},
                {"name": "processor", "type": "variable", "scope": "main"},
                {"name": "data", "type": "variable", "scope": "main"},
                {"name": "result", "type": "variable", "scope": "main"}
            ],
            expected_relationships=[
                {"type": "imports", "source": "module", "target": "Foundation"},
                {"type": "defines", "source": "module", "target": "DataProcessable"},
                {"type": "defines", "source": "module", "target": "DataProcessor"},
                {"type": "defines", "source": "module", "target": "Main"},
                {"type": "conforms_to", "source": "DataProcessor", "target": "DataProcessable"},
                {"type": "defines", "source": "DataProcessor", "target": "process"},
                {"type": "defines", "source": "DataProcessor", "target": "processItem"},
                {"type": "calls", "source": "process", "target": "processItem"},
                {"type": "calls", "source": "main", "target": "DataProcessor"},
                {"type": "calls", "source": "main", "target": "process"}
            ],
            complexity="complex"
        )

class TestDataGenerator:
    """Main class for generating test data across all languages."""
    
    def __init__(self):
        self.python_generator = PythonGenerator()
        self.javascript_generator = JavaScriptGenerator()
        self.swift_generator = SwiftGenerator()
    
    def generate_samples(self, language: Language, complexity: Optional[str] = None) -> List[CodeSample]:
        """Generate test samples for a specific language and complexity level."""
        generator = self._get_generator(language)
        samples = []
        
        if complexity is None or complexity == "simple":
            samples.append(generator.generate_simple_function())
        if complexity is None or complexity == "medium":
            samples.append(generator.generate_class_with_methods())
        if complexity is None or complexity == "complex":
            samples.append(generator.generate_complex_module())
        
        return samples
    
    def _get_generator(self, language: Language) -> CodeGenerator:
        """Get the appropriate generator for a language."""
        generators = {
            Language.PYTHON: self.python_generator,
            Language.JAVASCRIPT: self.javascript_generator,
            Language.SWIFT: self.swift_generator
        }
        return generators[language]
    
    def generate_all_samples(self, complexity: Optional[str] = None) -> Dict[Language, List[CodeSample]]:
        """Generate test samples for all languages."""
        return {
            language: self.generate_samples(language, complexity)
            for language in Language
        } 