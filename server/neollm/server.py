"""
Neo Local LLM MCP Server - Provides local LLM functionality.
"""

from typing import Any, Dict, Optional, List, AsyncGenerator
from fastapi import Depends, HTTPException, FastAPI
import os
import json
import time
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TextIteratorStreamer,
    BitsAndBytesConfig
)
from threading import Thread
import asyncio
import hashlib
from functools import lru_cache
from transformers import pipeline

from ..utils.base_server import BaseServer
from ..utils.error_handling import handle_exceptions, MCPError
from ..utils.security import ApiKey

class NeoLocalLLMServer(BaseServer):
    """Neo Local LLM MCP Server implementation."""
    
    def __init__(self):
        """Initialize Neo Local LLM MCP Server."""
        super().__init__("neollm_mcp")
        
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.cache = None
        self.get_cached_response = None
        
        # Create the FastAPI app
        self.app = FastAPI(title="Neo Local LLM MCP Server", version="0.1.0")
        
        # Initialize LLM
        self._init_llm()
        
        # Initialize cache
        self._init_cache()
        
        # Setup app state and middleware
        self.setup_app_state(self.app)
        self.setup_middleware(self.app)
        
        # Register routes
        self.register_routes(self.app)
        
    def _init_llm(self) -> None:
        """Initialize local LLM."""
        if not self.config.enable_local_models:
            self.logger.info("Local LLM is disabled")
            return

        model_path = self.config.local_model_path
        self.logger.info(f"Loading model from {model_path}")

        try:
            with self.monitor.span_in_context(
                "load_local_model",
                attributes={
                    "model_path": model_path
                }
            ):
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    device_map="auto",
                    torch_dtype=torch.float16,
                    trust_remote_code=True
                )
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    trust_remote_code=True
                )
                self.pipeline = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True
                )
                self.logger.info("Local LLM initialized successfully")
        except Exception as e:
            self.logger.error(
                f"Failed to load LLM model from path: {model_path}",
                exc_info=True,
                extra={
                    "model_path": model_path,
                    "error": str(e)
                }
            )
            self.model = None
            self.tokenizer = None
            # Don't raise here, allow the server to start without LLM
            # Endpoints will handle the error case
            
    def _init_cache(self) -> None:
        """Initialize response cache."""
        try:
            if self.config.enable_caching:
                self.cache = {}
                self.get_cached_response = lru_cache(maxsize=self.config.cache_size)(self._get_response)
                self.logger.info(
                    f"Cache initialized with size {self.config.cache_size}"
                )
            else:
                self.cache = None
                self.get_cached_response = None
                self.logger.info("Caching disabled")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize cache: {str(e)}")
            # Don't raise here, allow the server to start without cache
            
    def _get_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get response from cache.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached response or None
        """
        return self.cache.get(cache_key)
            
    def register_routes(self, app: FastAPI) -> None:
        """Register API routes."""
        super().register_routes(app)
        
        @app.post("/api/v1/llm/generate")
        @handle_exceptions()
        async def generate_text(
            prompt: str,
            model: Optional[str] = None,
            max_tokens: Optional[int] = None,
            temperature: Optional[float] = None,
            top_p: Optional[float] = None,
            top_k: Optional[int] = None,
            repetition_penalty: Optional[float] = None,
            stream: bool = False,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Generate text using local LLM.
            
            Args:
                prompt: Input prompt
                model: Model to use
                max_tokens: Maximum tokens to generate
                temperature: Sampling temperature
                top_p: Top-p sampling parameter
                top_k: Top-k sampling parameter
                repetition_penalty: Repetition penalty
                stream: Whether to stream the response
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
                
            # Check if local LLM is enabled
            if not self.config.enable_local_models:
                raise HTTPException(
                    status_code=503,
                    detail="Local LLM is disabled"
                )
                
            # Check if model is loaded
            if self.model is None or self.tokenizer is None:
                raise HTTPException(
                    status_code=503,
                    detail="Local LLM is not initialized properly"
                )
                
            # Set generation parameters
            gen_params = {
                "max_tokens": max_tokens or self.config.default_max_tokens,
                "temperature": temperature or self.config.default_temperature,
                "top_p": top_p or self.config.default_top_p,
                "top_k": top_k or self.config.default_top_k,
                "repetition_penalty": repetition_penalty or self.config.default_repetition_penalty
            }
                
            # Check if response is cached
            if self.config.enable_caching and not stream:
                # Create cache key
                cache_key = hashlib.md5(
                    json.dumps({
                        "prompt": prompt,
                        "model": model,
                        "params": gen_params
                    }).encode()
                ).hexdigest()
                
                # Check cache
                cached_response = self.get_cached_response(cache_key)
                if cached_response:
                    return cached_response
                
            # Generate text
            with self.monitor.span_in_context(
                "generate_text",
                attributes={
                    "model": model or self.config.local_model_path,
                    "max_tokens": gen_params["max_tokens"],
                    "temperature": gen_params["temperature"],
                    "prompt_length": len(prompt)
                }
            ):
                try:
                    # Tokenize input
                    inputs = self.tokenizer(
                        prompt,
                        return_tensors="pt"
                    ).to(self.model.device)
                    
                    # Generate text
                    if stream and self.config.enable_streaming:
                        # Create streamer
                        streamer = TextIteratorStreamer(
                            self.tokenizer,
                            skip_prompt=True
                        )
                        
                        # Start generation in separate thread
                        thread = Thread(
                            target=self.model.generate,
                            kwargs={
                                **inputs,
                                "streamer": streamer,
                                **gen_params
                            }
                        )
                        thread.start()
                        
                        # Stream response
                        async def stream_response():
                            async for token in streamer:
                                yield token
                                
                        return stream_response()
                    
                    else:
                        # Generate text (non-streaming)
                        outputs = self.model.generate(
                            **inputs,
                            **gen_params
                        )
                        
                        # Decode output
                        response = self.tokenizer.decode(
                            outputs[0],
                            skip_special_tokens=True
                        )
                        
                        # Remove prompt from response
                        response = response[len(prompt):].strip()
                        
                        # Cache response
                        if self.config.enable_caching:
                            result = {
                                "text": response,
                                "model": model or self.config.local_model_path
                            }
                            self.cache[cache_key] = result
                            return result
                        
                        return {
                            "text": response,
                            "model": model or self.config.local_model_path
                        }
                    
                except Exception as e:
                    self.logger.error(
                        f"Text generation failed: {str(e)}",
                        model=model or self.config.local_model_path,
                        prompt_length=len(prompt)
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Text generation failed: {str(e)}"
                    )
                    
        @app.post("/api/v1/llm/embed")
        @handle_exceptions()
        async def generate_embeddings(
            text: str,
            model: Optional[str] = None,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Generate embeddings using local LLM.
            
            Args:
                text: Input text
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
                
            # Check if local LLM is enabled
            if not self.config.enable_local_models:
                raise HTTPException(
                    status_code=503,
                    detail="Local LLM is disabled"
                )
                
            # Check if model is loaded
            if self.model is None or self.tokenizer is None:
                raise HTTPException(
                    status_code=503,
                    detail="Local LLM is not initialized properly"
                )
                
            # Get embeddings
            with self.monitor.span_in_context(
                "generate_embeddings",
                attributes={
                    "model": model or self.config.local_model_path,
                    "text_length": len(text)
                }
            ):
                try:
                    # TODO: Implement embeddings
                    # This is a placeholder; actual embeddings
                    # would require a specific embedding model
                    
                    # Tokenize input
                    inputs = self.tokenizer(
                        text,
                        return_tensors="pt",
                        padding=True,
                        truncation=True
                    ).to(self.model.device)
                    
                    # Get embeddings from last hidden state
                    with torch.no_grad():
                        outputs = self.model(**inputs, output_hidden_states=True)
                        embeddings = outputs.hidden_states[-1].mean(dim=1)
                    
                    return {
                        "embeddings": embeddings[0].cpu().numpy().tolist(),
                        "model": model or self.config.local_model_path,
                        "dimensions": embeddings.shape[-1]
                    }
                    
                except Exception as e:
                    self.logger.error(
                        f"Embedding generation failed: {str(e)}",
                        model=model or self.config.local_model_path,
                        text_length=len(text)
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Embedding generation failed: {str(e)}"
                    )

        @app.post("/api/v1/llm/tokenize")
        @handle_exceptions()
        async def tokenize_text(
            text: str,
            model: Optional[str] = None,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Tokenize text using local LLM.
            
            Args:
                text: Input text
                model: Model to use
                api_key: Validated API key
                
            Returns:
                Tokenized text
            """
            # Check permissions
            if not self.security.check_permission(api_key, "generate:tokenize"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Check if local LLM is enabled
            if not self.config.enable_local_models:
                raise HTTPException(
                    status_code=503,
                    detail="Local LLM is disabled"
                )
                
            # Check if model is loaded
            if self.model is None or self.tokenizer is None:
                raise HTTPException(
                    status_code=503,
                    detail="Local LLM is not initialized properly"
                )
                
            # Tokenize text
            with self.monitor.span_in_context(
                "tokenize_text",
                attributes={
                    "model": model or self.config.local_model_path,
                    "text_length": len(text)
                }
            ):
                try:
                    # Tokenize input
                    inputs = self.tokenizer(
                        text,
                        return_tensors="pt",
                        padding=True,
                        truncation=True
                    ).to(self.model.device)
                    
                    # Get tokenized text
                    tokenized_text = self.tokenizer.decode(
                        inputs.input_ids[0],
                        skip_special_tokens=True
                    )
                    
                    return {
                        "tokenized_text": tokenized_text,
                        "model": model or self.config.local_model_path
                    }
                    
                except Exception as e:
                    self.logger.error(
                        f"Tokenization failed: {str(e)}",
                        model=model or self.config.local_model_path,
                        text_length=len(text)
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Tokenization failed: {str(e)}"
                    )

        @app.post("/api/v1/llm/complete")
        @handle_exceptions()
        async def complete_text(
            prompt: str,
            model: Optional[str] = None,
            max_tokens: Optional[int] = None,
            temperature: Optional[float] = None,
            top_p: Optional[float] = None,
            top_k: Optional[int] = None,
            repetition_penalty: Optional[float] = None,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Complete text using local LLM.
            
            Args:
                prompt: Input prompt
                model: Model to use
                max_tokens: Maximum tokens to generate
                temperature: Sampling temperature
                top_p: Top-p sampling parameter
                top_k: Top-k sampling parameter
                repetition_penalty: Repetition penalty
                api_key: Validated API key
                
            Returns:
                Completed text
            """
            # Check permissions
            if not self.security.check_permission(api_key, "generate:complete"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Check if local LLM is enabled
            if not self.config.enable_local_models:
                raise HTTPException(
                    status_code=503,
                    detail="Local LLM is disabled"
                )
                
            # Check if model is loaded
            if self.model is None or self.tokenizer is None:
                raise HTTPException(
                    status_code=503,
                    detail="Local LLM is not initialized properly"
                )
                
            # Set generation parameters
            gen_params = {
                "max_tokens": max_tokens or self.config.default_max_tokens,
                "temperature": temperature or self.config.default_temperature,
                "top_p": top_p or self.config.default_top_p,
                "top_k": top_k or self.config.default_top_k,
                "repetition_penalty": repetition_penalty or self.config.default_repetition_penalty
            }
                
            # Generate text
            with self.monitor.span_in_context(
                "complete_text",
                attributes={
                    "model": model or self.config.local_model_path,
                    "max_tokens": gen_params["max_tokens"],
                    "temperature": gen_params["temperature"],
                    "prompt_length": len(prompt)
                }
            ):
                try:
                    # Tokenize input
                    inputs = self.tokenizer(
                        prompt,
                        return_tensors="pt"
                    ).to(self.model.device)
                    
                    # Generate text
                    outputs = self.model.generate(
                        **inputs,
                        **gen_params
                    )
                    
                    # Decode output
                    response = self.tokenizer.decode(
                        outputs[0],
                        skip_special_tokens=True
                    )
                    
                    # Remove prompt from response
                    response = response[len(prompt):].strip()
                    
                    return {
                        "completed_text": response,
                        "model": model or self.config.local_model_path
                    }
                    
                except Exception as e:
                    self.logger.error(
                        f"Text completion failed: {str(e)}",
                        model=model or self.config.local_model_path,
                        prompt_length=len(prompt)
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Text completion failed: {str(e)}"
                    )

        @app.get("/api/v1/llm/models")
        @handle_exceptions()
        async def list_models(
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """List available models.
            
            Args:
                api_key: Validated API key
                
            Returns:
                List of models
            """
            # Check permissions
            if not self.security.check_permission(api_key, "generate:list_models"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # List models
            models = {
                "models": [self.config.local_model_path]
            }
            
            return models

# Do not create server instance at import time
# server = NeoLocalLLMServer()
# app = server.get_app()

# Instead, provide a function to get initialized instance when needed
def get_server_instance():
    """Get the server instance, initializing it only when needed."""
    return NeoLocalLLMServer()

def get_app():
    """Get the FastAPI app instance, initializing it only when needed."""
    return get_server_instance().get_app() 