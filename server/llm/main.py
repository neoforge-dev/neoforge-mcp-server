from mcp.server.fastmcp import FastMCP
import os
import json
from typing import Dict, Any, Optional, List
import torch
from transformers import pipeline
import anthropic
import openai
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps
import re
import sys
from fastapi import FastAPI
from decorators import trace_tool, metrics_tool

# Initialize the MCP server
mcp = FastMCP("LLM Tools MCP", port=7444, log_level="DEBUG")

# Create FastAPI app
app = FastAPI() # Add this line to define the app

# Mount app if not testing
if "pytest" not in sys.modules:
    mcp.mount_app(app)

# Initialize tracer
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: "llm-mcp-server",
    ResourceAttributes.SERVICE_VERSION: "1.0.0",
})

# Configure tracing
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

def trace_tool(func):
    """Decorator to add tracing to MCP tools"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with tracer.start_as_current_span(
            name=f"mcp.tool.{func.__name__}",
            attributes={
                "mcp.tool.name": func.__name__,
                "mcp.tool.args": str(args),
                "mcp.tool.kwargs": str(kwargs)
            }
        ) as span:
            try:
                result = func(*args, **kwargs)
                if isinstance(result, dict):
                    span.set_attribute("mcp.tool.status", result.get("status", "unknown"))
                    if "error" in result:
                        span.set_attribute("mcp.tool.error", result["error"])
                return result
            except Exception as e:
                span.set_attribute("mcp.tool.error", str(e))
                span.record_exception(e)
                raise
    return wrapper

@mcp.tool()
@trace_tool
@metrics_tool
def generate_code(prompt: str, model: str = "claude-3-sonnet", context: Optional[Dict[str, Any]] = None, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """Generate code using various models."""
    try:
        if not prompt:
            return {
                "status": "error",
                "error": "Empty prompt provided",
                "language": "python"
            }

        # Get workspace info
        workspace_info = _get_workspace_info()

        # Prepare context
        full_context = {
            "workspace": workspace_info,
            **(context or {})
        }

        # Get system prompt
        if system_prompt is None:
            system_prompt = _get_default_system_prompt("python")

        # Generate code based on model type
        if model in ["claude-3-sonnet", "claude-3-opus"]:
            result = _generate_with_api_model(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=None,
                temperature=0.7
            )
        elif model in ["gpt-4", "gpt-3.5-turbo"]:
            result = _generate_with_api_model(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=None,
                temperature=0.7
            )
        elif model in ["code-llama", "starcoder"]:
            result = _generate_with_local_model(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=None,
                temperature=0.7
            )
        else:
            return {
                "status": "error",
                "error": f"Invalid model: {model}",
                "language": "python"
            }

        return {
            "status": "success",
            "code": result,
            "model": model,
            "language": "python"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "model": model,
            "language": "python"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def manage_llm_context(content: str, model: str = "claude-3-sonnet", max_tokens: int = None) -> Dict[str, Any]:
    """Advanced LLM context management and optimization."""
    try:
        # Model context limits
        model_limits = {
            'claude-3-opus': 200000,
            'claude-3-sonnet': 100000,
            'gpt-4': 128000,
            'gpt-3.5': 16000
        }

        if model not in model_limits:
            return {
                'status': 'error',
                'error': f'Unknown model: {model}'
            }

        # Use specified max_tokens or model limit
        token_limit = max_tokens or model_limits[model]

        # Analyze content
        words = content.split()
        chars = len(content)
        lines = content.count('\n') + 1

        # Estimate tokens (improved estimation)
        estimated_tokens = int(len(words) * 1.3)  # Rough approximation

        # Calculate context metrics
        metrics = {
            'estimated_tokens': estimated_tokens,
            'words': len(words),
            'characters': chars,
            'lines': lines,
            'usage_percent': (estimated_tokens / token_limit) * 100
        }

        # Generate optimization suggestions
        suggestions = []
        if estimated_tokens > token_limit:
            suggestions.append({
                'type': 'truncation',
                'message': f'Content exceeds {model} token limit by approximately {estimated_tokens - token_limit} tokens'
            })

            # Suggest specific optimizations
            if lines > 100:
                suggestions.append({
                    'type': 'structure',
                    'message': 'Consider reducing line count by combining related lines'
                })

            code_blocks = len(re.findall(r'```.*?```', content, re.DOTALL))
            if code_blocks > 5:
                suggestions.append({
                    'type': 'code',
                    'message': 'Consider reducing number of code blocks or showing only relevant portions'
                })

        # Optimize content if needed
        optimized_content = content
        if estimated_tokens > token_limit:
            optimized_content = _optimize_content(content, token_limit)

        return {
            'status': 'success',
            'metrics': metrics,
            'suggestions': suggestions,
            'optimized_content': optimized_content if optimized_content != content else None,
            'model': model,
            'token_limit': token_limit
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
@trace_tool
@metrics_tool
def context_length(text: str) -> Dict[str, Any]:
    """Track LLM context usage."""
    try:
        # Simple tokenization (this is a basic approximation)
        words = text.split()
        characters = len(text)
        lines = text.count('\n') + 1

        # Rough token estimation (OpenAI GPT-style)
        estimated_tokens = len(words) * 1.3

        # Context length limits (example values)
        limits = {
            'claude-3-opus': 200000,
            'claude-3-sonnet': 100000,
            'gpt-4': 128000,
            'gpt-3.5': 16000
        }

        # Calculate percentage of context used
        usage = {model: (estimated_tokens / limit) * 100 for model, limit in limits.items()}

        return {
            'estimated_tokens': int(estimated_tokens),
            'words': len(words),
            'characters': characters,
            'lines': lines,
            'context_usage_percent': usage,
            'approaching_limit': any(pct > 75 for pct in usage.values())
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
@trace_tool
@metrics_tool
def filter_output(content: str, max_lines: int = 50, important_patterns: List[str] = None) -> Dict[str, Any]:
    """Process and format long command outputs for better LLM consumption."""
    try:
        lines = content.split('\n')
        total_lines = len(lines)

        if not important_patterns:
            important_patterns = [
                r'error', r'warning', r'fail', r'exception',
                r'success', r'completed', r'starting', r'finished'
            ]

        # Always keep lines matching important patterns
        important_lines = []
        other_lines = []

        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in important_patterns):
                important_lines.append(line)
            else:
                other_lines.append(line)

        # Calculate remaining space for other lines
        remaining_space = max_lines - len(important_lines)

        if remaining_space <= 0:
            filtered_lines = important_lines[:max_lines]
        else:
            # Select a representative sample of other lines
            step = len(other_lines) // remaining_space if remaining_space > 0 else 1
            sampled_lines = other_lines[::step][:remaining_space]
            filtered_lines = important_lines + sampled_lines

        return {
            'filtered_content': '\n'.join(filtered_lines),
            'total_lines': total_lines,
            'included_lines': len(filtered_lines),
            'important_lines': len(important_lines),
            'truncated': total_lines > len(filtered_lines)
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _get_workspace_info() -> Dict[str, Any]:
    """Get information about the current workspace."""
    return {
        "files": _list_workspace_files(),
        "dependencies": _get_dependencies(),
        "environment": _get_environment_info()
    }

def _get_default_system_prompt(language: str) -> str:
    """Get the default system prompt for code generation."""
    return f"""You are an expert {language} programmer. Generate code that is:
1. Well-documented
2. Follows best practices
3. Is efficient and maintainable
4. Includes error handling
5. Is properly formatted"""

def _generate_with_api_model(prompt: str, model: str, system_prompt: str, max_tokens: Optional[int], temperature: float) -> str:
    """Generate code using API-based models (Claude, GPT)."""
    if model.startswith("claude"):
        client = anthropic.Client()
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    elif model.startswith("gpt"):
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    else:
        raise ValueError(f"Unsupported API model: {model}")

def _generate_with_local_model(prompt: str, model: str, system_prompt: str, max_tokens: Optional[int], temperature: float) -> str:
    """Generate code using local models (CodeLlama, StarCoder)."""
    config = _get_local_model_config(model)
    pipe = pipeline(
        "text-generation",
        model=config["model_name"],
        device=config["device"]
    )

    full_prompt = f"{system_prompt}\n\n{prompt}"
    response = pipe(
        full_prompt,
        max_new_tokens=max_tokens or 1000,
        temperature=temperature,
        do_sample=True
    )

    return response[0]["generated_text"]

def _get_local_model_config(model: str) -> Dict[str, Any]:
    """Get configuration for local models."""
    configs = {
        "code-llama": {
            "model_name": "codellama/CodeLlama-34b-Python",
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        },
        "starcoder": {
            "model_name": "bigcode/starcoder",
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
    }

    if model not in configs:
        raise ValueError(f"Unknown model: {model}")

    return configs[model]

def _optimize_content(content: str, token_limit: int) -> str:
    """Optimize content to fit within token limit."""
    # Simple optimization: truncate content while preserving important parts
    words = content.split()
    estimated_tokens = len(words) * 1.3

    if estimated_tokens <= token_limit:
        return content

    # Keep important parts (error messages, warnings, etc.)
    important_patterns = [
        r'error', r'warning', r'fail', r'exception',
        r'success', r'completed', r'starting', r'finished'
    ]

    lines = content.split('\n')
    important_lines = []
    other_lines = []

    for line in lines:
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in important_patterns):
            important_lines.append(line)
        else:
            other_lines.append(line)

    # Calculate how many other lines we can keep
    important_tokens = sum(len(line.split()) * 1.3 for line in important_lines)
    remaining_tokens = token_limit - important_tokens
    other_tokens_per_line = sum(len(line.split()) * 1.3 for line in other_lines) / len(other_lines)
    max_other_lines = int(remaining_tokens / other_tokens_per_line)

    # Select a representative sample of other lines
    if max_other_lines > 0:
        step = len(other_lines) // max_other_lines if max_other_lines > 0 else 1
        sampled_lines = other_lines[::step][:max_other_lines]
        return '\n'.join(important_lines + sampled_lines)
    else:
        return '\n'.join(important_lines[:int(token_limit / (sum(len(line.split()) * 1.3 for line in important_lines) / len(important_lines)))])

def _list_workspace_files() -> List[str]:
    """List files in the current workspace."""
    try:
        return [f for f in os.listdir('.') if os.path.isfile(f)]
    except Exception:
        return []

def _get_dependencies() -> Dict[str, str]:
    """Get project dependencies."""
    try:
        with open('requirements.txt', 'r') as f:
            return {line.split('==')[0]: line.split('==')[1] if '==' in line else 'latest'
                   for line in f if line.strip() and not line.startswith('#')}
    except Exception:
        return {}

def _get_environment_info() -> Dict[str, str]:
    """Get environment information."""
    return {
        "python_version": sys.version,
        "platform": sys.platform,
        "cuda_available": torch.cuda.is_available() if torch else False
    }

# Add FastAPI app import if not already present
from fastapi import FastAPI 