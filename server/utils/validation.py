"""
Shared validation utilities for MCP servers.
"""

import re
import json
from typing import Any, Dict, List, Optional, Union, Type, TypeVar, Callable
from dataclasses import dataclass, field
from .error_handling import ValidationError

T = TypeVar('T')

@dataclass
class ValidationRule:
    """Validation rule definition."""
    
    # Rule type and parameters
    type: str
    params: Dict[str, Any] = field(default_factory=dict)
    
    # Error message
    message: Optional[str] = None
    
    def validate(self, value: Any) -> None:
        """Validate a value against this rule.
        
        Args:
            value: Value to validate
            
        Raises:
            ValidationError if validation fails
        """
        validator = VALIDATORS.get(self.type)
        if not validator:
            raise ValueError(f"Unknown validator type: {self.type}")
            
        if not validator(value, **self.params):
            raise ValidationError(
                self.message or f"Validation failed for rule: {self.type}",
                details={
                    "rule": self.type,
                    "params": self.params,
                    "value": str(value)
                }
            )

@dataclass
class FieldValidator:
    """Field validator with rules."""
    
    # Field name and type
    name: str
    type: Type
    
    # Validation rules
    rules: List[ValidationRule] = field(default_factory=list)
    
    # Whether field is required
    required: bool = True
    
    def validate(self, value: Any) -> None:
        """Validate a value against all rules.
        
        Args:
            value: Value to validate
            
        Raises:
            ValidationError if validation fails
        """
        # Check if field is required
        if value is None:
            if self.required:
                raise ValidationError(
                    f"Field '{self.name}' is required",
                    details={"field": self.name}
                )
            return
            
        # Check type
        try:
            if not isinstance(value, self.type):
                # Try to convert
                value = self.type(value)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Field '{self.name}' must be of type {self.type.__name__}",
                details={
                    "field": self.name,
                    "expected_type": self.type.__name__,
                    "actual_type": type(value).__name__
                }
            )
            
        # Apply all rules
        for rule in self.rules:
            rule.validate(value)

class SchemaValidator:
    """Schema validator for structured data."""
    
    def __init__(self):
        """Initialize schema validator."""
        self.fields: Dict[str, FieldValidator] = {}
        
    def add_field(
        self,
        name: str,
        type: Type,
        rules: Optional[List[ValidationRule]] = None,
        required: bool = True
    ) -> None:
        """Add a field to the schema.
        
        Args:
            name: Field name
            type: Field type
            rules: Validation rules
            required: Whether field is required
        """
        self.fields[name] = FieldValidator(
            name=name,
            type=type,
            rules=rules or [],
            required=required
        )
        
    def validate(self, data: Dict[str, Any]) -> None:
        """Validate data against the schema.
        
        Args:
            data: Data to validate
            
        Raises:
            ValidationError if validation fails
        """
        # Check for unknown fields
        unknown = set(data.keys()) - set(self.fields.keys())
        if unknown:
            raise ValidationError(
                "Unknown fields in data",
                details={"unknown_fields": list(unknown)}
            )
            
        # Validate each field
        for name, validator in self.fields.items():
            value = data.get(name)
            validator.validate(value)

# Built-in validators
def validate_length(
    value: Union[str, List, Dict],
    min: Optional[int] = None,
    max: Optional[int] = None
) -> bool:
    """Validate length of string, list or dict."""
    length = len(value)
    if min is not None and length < min:
        return False
    if max is not None and length > max:
        return False
    return True

def validate_range(
    value: Union[int, float],
    min: Optional[Union[int, float]] = None,
    max: Optional[Union[int, float]] = None
) -> bool:
    """Validate numeric range."""
    if min is not None and value < min:
        return False
    if max is not None and value > max:
        return False
    return True

def validate_regex(value: str, pattern: str) -> bool:
    """Validate string against regex pattern."""
    return bool(re.match(pattern, value))

def validate_enum(value: Any, choices: List[Any]) -> bool:
    """Validate value is in enum choices."""
    return value in choices

def validate_email(value: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, value))

def validate_url(value: str) -> bool:
    """Validate URL format."""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, value))

def validate_json(value: str) -> bool:
    """Validate JSON string."""
    try:
        json.loads(value)
        return True
    except json.JSONDecodeError:
        return False

def validate_ipv4(value: str) -> bool:
    """Validate IPv4 address."""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, value):
        return False
    return all(0 <= int(x) <= 255 for x in value.split('.'))

def validate_port(value: int) -> bool:
    """Validate port number."""
    return 1 <= value <= 65535

def validate_hostname(value: str) -> bool:
    """Validate hostname."""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(pattern, value))

# Register validators
VALIDATORS: Dict[str, Callable] = {
    'length': validate_length,
    'range': validate_range,
    'regex': validate_regex,
    'enum': validate_enum,
    'email': validate_email,
    'url': validate_url,
    'json': validate_json,
    'ipv4': validate_ipv4,
    'port': validate_port,
    'hostname': validate_hostname
}

# Example usage:
"""
# Create schema validator
schema = SchemaValidator()

# Add fields with rules
schema.add_field('name', str, [
    ValidationRule('length', {'min': 2, 'max': 50})
])

schema.add_field('age', int, [
    ValidationRule('range', {'min': 0, 'max': 120})
])

schema.add_field('email', str, [
    ValidationRule('email')
])

# Validate data
data = {
    'name': 'John Doe',
    'age': 30,
    'email': 'john@example.com'
}

try:
    schema.validate(data)
    print("Validation successful")
except ValidationError as e:
    print(f"Validation failed: {e}")
""" 