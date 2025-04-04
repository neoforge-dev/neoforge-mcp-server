"""
LLM MCP Server - Provides LLM-related tools and functionality.
"""

import os
from typing import Any, Dict, Optional, List
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
import anthropic
import openai
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from ..utils.base_server import BaseServer
from ..utils.error_handling import handle_exceptions, MCPError
from ..utils.security import ApiKey
from ..utils.logging import LogManager

# API key header
api_key_header = APIKeyHeader(name="X-API-Key")

class LLMMCPServer(BaseServer):
    """LLM MCP Server implementation."""
    
    def __init__(self, app_name: str = "llm_mcp"):
        """Initialize LLM MCP Server.
        
        Args:
            app_name: Name of the application
        """
        super().__init__(app_name)
        
        # Initialize LLM clients
        self._init_llm_clients()
        
        # Register routes
        self._register_routes()
        
    def _init_llm_clients(self) -> None:
        """Initialize LLM clients and models."""
        # Initialize Anthropic client
        anthropic_api_key = self.config.anthropic_api_key
        if anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        else:
            self.anthropic_client = None
            
        # Initialize OpenAI client
        openai_api_key = self.config.openai_api_key
        if openai_api_key:
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
        else:
            self.openai_client = None
            
        # Initialize local models if enabled
        self.local_models = {}
        if self.config.enable_local_models:
            try:
                # Load local models
                model_path = self.config.local_model_path
                if model_path and os.path.exists(model_path):
                    for model_dir in os.listdir(model_path):
                        full_path = os.path.join(model_path, model_dir)
                        if os.path.isdir(full_path):
                            try:
                                model = AutoModelForCausalLM.from_pretrained(full_path)
                                tokenizer = AutoTokenizer.from_pretrained(full_path)
                                self.local_models[model_dir] = {
                                    "model": model,
                                    "tokenizer": tokenizer
                                }
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to load local model {model_dir}",
                                    error=str(e)
                                )
            except Exception as e:
                self.logger.error(
                    "Failed to initialize local models: %s",
                    str(e)
                )
                
    async def get_api_key(self, api_key: str = Security(api_key_header)) -> ApiKey:
        """Validate API key and return key info.
        
        Args:
            api_key: API key from request header
            
        Returns:
            ApiKey object
            
        Raises:
            HTTPException if key is invalid
        """
        try:
            return self.security.validate_api_key(api_key)
        except MCPError as e:
            raise HTTPException(
                status_code=401,
                detail=str(e)
            )
            
    def _register_routes(self) -> None:
        """Register API routes."""
        super().register_routes()
        
        @self.app.post("/api/v1/generate")
        @handle_exceptions()
        async def generate_text(
            prompt: str,
            model: Optional[str] = None,
            max_tokens: Optional[int] = None,
            temperature: Optional[float] = None,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Generate text using an LLM.
            
            Args:
                prompt: Text prompt
                model: Model to use (default: config)
                max_tokens: Maximum tokens to generate
                temperature: Sampling temperature
                api_key: Validated API key
                
            Returns:
                Generated text
            """
            # Check permissions
            if not self.security.check_permission(api_key, "generate:text"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Use defaults from config
            model = model or self.config.default_model
            max_tokens = max_tokens or self.config.max_tokens
            temperature = temperature or self.config.temperature
            
            # Generate text
            with self.monitor.span_in_context(
                "generate_text",
                attributes={
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            ):
                try:
                    # Route to appropriate model
                    if model in self.local_models:
                        result = self._generate_local(
                            prompt,
                            model,
                            max_tokens,
                            temperature
                        )
                    elif model.startswith("claude-"):
                        if not self.anthropic_client:
                            raise HTTPException(
                                status_code=503,
                                detail="Anthropic API not configured"
                            )
                        result = self._generate_anthropic(
                            prompt,
                            model,
                            max_tokens,
                            temperature
                        )
                    elif model.startswith("gpt-"):
                        if not self.openai_client:
                            raise HTTPException(
                                status_code=503,
                                detail="OpenAI API not configured"
                            )
                        result = self._generate_openai(
                            prompt,
                            model,
                            max_tokens,
                            temperature
                        )
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported model: {model}"
                        )
                        
                    return result
                    
                except Exception as e:
                    self.logger.error(
                        "Text generation failed",
                        error=str(e),
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )
                    
        @self.app.post("/api/v1/embed")
        @handle_exceptions()
        async def embed_text(
            text: str,
            model: Optional[str] = None,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Generate embeddings for text.
            
            Args:
                text: Text to embed
                model: Model to use
                api_key: Validated API key
                
            Returns:
                Text embeddings
            """
            # Check permissions
            if not self.security.check_permission(api_key, "generate:embeddings"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Use default model
            model = model or self.config.default_model
            
            # Generate embeddings
            with self.monitor.span_in_context(
                "embed_text",
                attributes={"model": model}
            ):
                try:
                    # Use OpenAI embeddings
                    if model.startswith("text-embedding"):
                        if not self.openai_client:
                            raise HTTPException(
                                status_code=400,
                                detail="OpenAI API not configured"
                            )
                        return self._embed_openai(text, model)
                        
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported embedding model: {model}"
                        )
                        
                except Exception as e:
                    self.logger.error(
                        "Embedding generation failed",
                        error=str(e),
                        model=model
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )
                    
    def _generate_local(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate text using a local model.
        
        Args:
            prompt: Text prompt
            model: Model name
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        model_info = self.local_models[model]
        inputs = model_info["tokenizer"](prompt, return_tensors="pt")
        
        with torch.no_grad():
            outputs = model_info["model"].generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True
            )
            
        text = model_info["tokenizer"].decode(outputs[0])
        return {
            "status": "success",
            "text": text,
            "model": model
        }
        
    def _generate_anthropic(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate text using Anthropic API.
        
        Args:
            prompt: Text prompt
            model: Model name
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        response = self.anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return {
            "status": "success",
            "text": response.content[0].text,
            "model": model
        }
        
    def _generate_openai(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate text using OpenAI API.
        
        Args:
            prompt: Text prompt
            model: Model name
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        response = self.openai_client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return {
            "status": "success",
            "text": response.choices[0].message.content,
            "model": model
        }
        
    def _embed_openai(
        self,
        text: str,
        model: str
    ) -> Dict[str, Any]:
        """Generate embeddings using OpenAI API.
        
        Args:
            text: Text to embed
            model: Model name
            
        Returns:
            Text embeddings
        """
        response = self.openai_client.embeddings.create(
            model=model,
            input=text
        )
        
        return {
            "status": "success",
            "embeddings": response.data[0].embedding,
            "model": model
        }

# Create server instance
server = LLMMCPServer()
app = server.app 