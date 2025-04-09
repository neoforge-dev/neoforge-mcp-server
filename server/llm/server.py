"""
LLM MCP Server - Provides LLM-related tools and functionality.
"""

import os
from typing import Any, Dict, Optional, List
from fastapi import Depends, HTTPException, Security, Request, FastAPI
from fastapi.security import APIKeyHeader
import anthropic
import openai
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging
from pydantic import BaseModel

# Import BaseServer and necessary utilities
from server.utils.base_server import BaseServer
from server.utils.error_handling import handle_exceptions
from server.utils.security import ApiKey # Import ApiKey
# Removed ApiKey, get_api_key import - get_api_key is a BaseServer method
# from server.utils.security import ApiKey, get_api_key
from ..utils.logging import LogManager

# Import LLM specific logic - Using local placeholders
# from server.core import LanguageModel, ModelConfig, Tokenizer, ModelManager
from .models import LanguageModel, ModelConfig, Tokenizer
from .manager import ModelManager

# API key header
api_key_header = APIKeyHeader(name="X-API-Key")

# --- Pydantic Models for API --- (Keep these)
class GenerateRequest(BaseModel):
    prompt: str
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    # Add other generation parameters as needed

class GenerateResponse(BaseModel):
    text: str
    model_name: str
    tokens_generated: int

class TokenizeRequest(BaseModel):
    text: str
    model_name: Optional[str] = None

class TokenizeResponse(BaseModel):
    tokens: List[int]
    count: int
    model_name: str

class ModelInfo(BaseModel):
    name: str
    config: Dict[str, Any]
    type: str # e.g., 'local', 'openai', 'anthropic'

class ListModelsResponse(BaseModel):
    models: List[ModelInfo]

class LLMServer(BaseServer):
    """LLM Server implementation inheriting from BaseServer."""

    def __init__(self):
        """Initialize LLM Server."""
        # Call BaseServer init with the specific app name
        # BaseServer handles config loading, logging, monitoring, security setup
        super().__init__(app_name="llm_server") # Use correct app name if different

        # Initialize LLM specific components (using config from BaseServer)
        self.model_manager = ModelManager(config=self.config)
        # BaseServer setup logger, access via self.logger
        self.logger.info("LLM Server initialized with Model Manager")

    def register_routes(self) -> None:
        """Register LLM specific routes after base routes."""
        # Register base routes (like /health) from BaseServer
        super().register_routes()

        # Add LLM specific routes
        @self.app.post("/api/v1/generate", response_model=GenerateResponse, tags=["LLM"])
        @handle_exceptions()
        async def generate(
            request_body: GenerateRequest,
            request: Request, # Access logger/managers via request state
            api_key: ApiKey = Depends(self.get_api_key) # Re-integrate security
        ) -> GenerateResponse:
            """Generate text using a specified or default LLM."""
            # Access logger from request state (set up by BaseServer middleware)
            logger = request.state.log_manager
            logger.info(
                f"Received generation request for model: {request_body.model_name or 'default'}",
                extra={"prompt_start": request_body.prompt[:50]}
            )

            # Use ModelManager (initialized in __init__)
            model = self.model_manager.get_model(request_body.model_name)

            # Override generation parameters if provided in request
            gen_params = {
                'max_tokens': request_body.max_tokens,
                'temperature': request_body.temperature,
            }
            gen_params = {k: v for k, v in gen_params.items() if v is not None}

            # Generate text using the model from ModelManager
            generated_text = model.generate(request_body.prompt, **gen_params)
            # Use the model's tokenizer
            tokens_generated = len(model.tokenizer.encode(generated_text))

            logger.info(
                f"Generated {tokens_generated} tokens using model: {model.name}",
                extra={"generated_text_start": generated_text[:50]}
            )

            return GenerateResponse(
                text=generated_text,
                model_name=model.name,
                tokens_generated=tokens_generated
            )

        @self.app.post("/api/v1/tokenize", response_model=TokenizeResponse, tags=["LLM"])
        @handle_exceptions()
        async def tokenize(
            request_body: TokenizeRequest,
            request: Request,
            api_key: ApiKey = Depends(self.get_api_key) # Re-integrate security
       ) -> TokenizeResponse:
            """Tokenize text using a specified or default model's tokenizer."""
            logger = request.state.log_manager
            logger.info(
                f"Received tokenization request for model: {request_body.model_name or 'default'}",
                extra={"text_start": request_body.text[:50]}
            )

            model = self.model_manager.get_model(request_body.model_name)
            tokens = model.tokenizer.encode(request_body.text)
            count = len(tokens)

            logger.info(f"Tokenized text into {count} tokens using tokenizer for: {model.name}")

            return TokenizeResponse(
                tokens=tokens,
                count=count,
                model_name=model.name
            )

        @self.app.get("/api/v1/models", response_model=ListModelsResponse, tags=["LLM"])
        @handle_exceptions()
        async def list_models(
            request: Request,
            api_key: ApiKey = Depends(self.get_api_key) # Re-integrate security
        ) -> ListModelsResponse:
            """List available language models."""
            logger = request.state.log_manager
            logger.info("Received request to list models")

            available_models = self.model_manager.list_models()
            # Ensure ModelConfig can be dict converted if needed by ModelInfo
            # If ModelConfig is a Pydantic model, .dict() works.
            model_infos = [
                ModelInfo(name=m.name, config=m.config.dict(), type=m.type)
                for m in available_models
            ]

            logger.info(f"Returning {len(model_infos)} available models")
            return ListModelsResponse(models=model_infos)

# Create server instance ONLY when run directly or via app factory
# server = LLMServer() # Avoid module-level instantiation
# app = server.app # Avoid module-level instantiation

# App Factory pattern (optional, but good practice)
def create_app() -> FastAPI:
    server = LLMServer()
    return server.app

# You might need to adjust server/llm/__init__.py and tests/conftest.py
# if they directly imported the 'app' variable previously. 