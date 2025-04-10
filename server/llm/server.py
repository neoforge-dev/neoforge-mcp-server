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
from server.utils.error_handling import (
    handle_exceptions, ValidationError, AuthenticationError,
    AuthorizationError, NotFoundError, ConfigurationError
)
from server.utils.security import ApiKey
from ..utils.logging import LogManager

# Import LLM specific logic
from .models import BaseLanguageModel, Tokenizer
from .manager import ModelManager

# API key header
api_key_header = APIKeyHeader(name="X-API-Key")

# --- Pydantic Models for API ---
class GenerateRequest(BaseModel):
    prompt: str
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    # Add other generation parameters as needed

class TokenizeRequest(BaseModel):
    text: str
    model_name: Optional[str] = None

class ListModelsResponse(BaseModel):
    models: List[Dict[str, Any]]

class TokenizeResponse(BaseModel):
    tokens: List[int]
    count: int
    model_name: str

class GenerateResponse(BaseModel):
    text: str
    model_name: str
    tokens_generated: int

class LLMServer(BaseServer):
    """LLM Server implementation inheriting from BaseServer."""

    def __init__(self):
        """Initialize LLM Server."""
        super().__init__(app_name="llm_server")
        self.model_manager = ModelManager(config=self.config)
        self.logger.info("LLM Server initialized with Model Manager")

    def register_routes(self) -> None:
        """Register LLM specific routes after base routes."""
        super().register_routes()

        @self.app.get("/api/v1/models", response_model=ListModelsResponse, tags=["LLM"])
        @handle_exceptions()
        async def list_llm_models(
            request: Request,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> ListModelsResponse:
            """List available language models."""
            logger = request.state.log_manager
            logger.info("Received request to list models")

            if not self.security.check_permission(api_key, "llm:list_models"):
                raise AuthorizationError(
                    message="Insufficient permissions to list models",
                    details={"required_permission": "llm:list_models"}
                )

            try:
                available_models = self.model_manager.list_models()

                model_infos = [
                    {
                        "name": m.name,
                        "config": m.config.dict(),
                        "type": m.type
                    }
                    for m in available_models
                ]

                logger.info(f"Returning {len(model_infos)} available models: {model_infos}")
                return ListModelsResponse(models=model_infos)
            except Exception as e:
                 logger.exception("Error processing models in list_models route")
                 raise

        @self.app.post("/api/v1/tokenize", response_model=TokenizeResponse, tags=["LLM"])
        @handle_exceptions()
        async def tokenize(
            request: Request,
            tokenize_request: TokenizeRequest,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> TokenizeResponse:
            """Tokenize text using specified model."""
            logger = request.state.log_manager
            requested_model_name = tokenize_request.model_name
            logger.info(f"Received tokenize request for model: {requested_model_name or 'default'}")

            if not self.security.check_permission(api_key, "llm:tokenize"):
                raise AuthorizationError(
                    message="Insufficient permissions to tokenize",
                    details={"required_permission": "llm:tokenize"}
                )

            try:
                # Wrap get_model call to handle potential ValueError
                try:
                    model = self.model_manager.get_model(requested_model_name)
                except ValueError as e:
                    # Reraise ValueError as NotFoundError for proper HTTP response
                    raise NotFoundError(
                        message=f"Model not found: {requested_model_name or 'default'}",
                        details={"model_name": requested_model_name or 'default', "original_error": str(e)}
                    )

                if not model: # Should technically be unreachable if get_model raises ValueError
                    if requested_model_name is None:
                         raise ConfigurationError(
                             message="Tokenization requested with default model, but no default model is configured.",
                             details={"model_name": None}
                         )
                    else:
                        # This case might still be relevant if get_model returns None instead of raising error
                        raise NotFoundError(
                            message=f"Model not found: {requested_model_name}",
                            details={"model_name": requested_model_name}
                        )

                tokens = model.tokenizer.encode(tokenize_request.text)
                actual_model_name = model.name
                return TokenizeResponse(
                    tokens=tokens,
                    count=len(tokens),
                    model_name=actual_model_name
                )

            except Exception as e:
                logger.error(f"Error during tokenization: {str(e)}")
                raise # Re-raise other exceptions (like AuthorizationError or unexpected ones)

        @self.app.post("/api/v1/generate", response_model=GenerateResponse, tags=["LLM"])
        @handle_exceptions()
        async def generate(
            request: Request,
            generate_request: GenerateRequest,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> GenerateResponse:
            """Generate text using specified model."""
            logger = request.state.log_manager
            logger.info(f"Received generate request for model: {generate_request.model_name}")

            if not self.security.check_permission(api_key, "llm:generate"):
                raise AuthorizationError(
                    message="Insufficient permissions to generate text",
                    details={"required_permission": "llm:generate"}
                )

            try:
                # Wrap get_model call to handle potential ValueError
                try:
                    model = self.model_manager.get_model(generate_request.model_name)
                except ValueError as e:
                     # Reraise ValueError as NotFoundError for proper HTTP response
                    raise NotFoundError(
                        message=f"Model not found: {generate_request.model_name or 'default'}",
                        details={"model_name": generate_request.model_name or 'default', "original_error": str(e)}
                    )

                if not model: # Should technically be unreachable now
                     raise NotFoundError( # Keep as fallback just in case get_model returns None
                         message=f"Model not found: {generate_request.model_name or 'default'}",
                         details={"model_name": generate_request.model_name or 'default'}
                     )

                actual_model_name = model.name # Get the actual model name used

                generated_text = model.generate(
                    generate_request.prompt,
                    max_tokens=generate_request.max_tokens,
                    temperature=generate_request.temperature
                )

                tokens = model.tokenizer.encode(generated_text)
                return GenerateResponse(
                    text=generated_text,
                    model_name=actual_model_name,
                    tokens_generated=len(tokens)
                )

            except Exception as e:
                 logger.error(f"Error during text generation: {str(e)}")
                 raise

def create_app() -> FastAPI:
    """Factory function to create the LLMServer FastAPI app."""
    server = LLMServer()
    return server.app

# Create server instance ONLY when run directly or via app factory
# server = LLMServer() # Avoid module-level instantiation
# app = server.app # Avoid module-level instantiation

# You might need to adjust server/llm/__init__.py and tests/conftest.py
# if they directly imported the 'app' variable previously. 