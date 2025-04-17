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
    """LLM MCP Server implementation."""

    def __init__(self):
        """Initialize LLM MCP Server (Managers only)."""
        super().__init__("llm_mcp")
        self._init_llm_manager()

    def _init_llm_manager(self) -> None:
        """Initialize the language model manager."""
        try:
            # Pass the config object to ModelManager
            self.model_manager = ModelManager(config=self.config)
            self.logger.info("ModelManager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize ModelManager: {e}", exc_info=True)
            # Decide if this is fatal. If so, raise an exception.
            # For now, let it continue but log the error.
            self.model_manager = None # Ensure it's None if failed

    def register_routes(self, app: FastAPI) -> None:
        """Register LLM specific API routes."""
        super().register_routes(app)

        prefix = self.config.api_prefix

        @app.get(f"{prefix}/models", tags=["LLM"], response_model=ListModelsResponse)
        @handle_exceptions()
        async def list_models(
            request: Request,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> ListModelsResponse:
            """List available language models."""
            logger = request.state.log_manager
            logger.info("Received request to list models")

            if not self.security.check_permission(api_key, "llm:read"):
                raise AuthorizationError(
                    message="Insufficient permissions to list models",
                    details={"required_permission": "llm:read"}
                )

            if not self.model_manager:
                raise HTTPException(status_code=503, detail="Model manager not available")

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

        @app.post(f"{prefix}/tokenize", tags=["LLM"], response_model=TokenizeResponse)
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

            if not self.model_manager:
                raise HTTPException(status_code=503, detail="Model manager not available")

            try:
                result = self.model_manager.tokenize(
                    text=tokenize_request.text,
                    model_id=tokenize_request.model_name
                )
                return TokenizeResponse(**result)
            except ConfigurationError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(f"Tokenization error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Tokenization failed")

        @app.post(f"{prefix}/generate", tags=["LLM"], response_model=GenerateResponse)
        @handle_exceptions()
        async def generate(
            request: Request,
            generate_request: GenerateRequest,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> GenerateResponse:
            """Generate text using specified model."""
            logger = request.state.log_manager
            logger.info(f"Received generate request for model: {generate_request.model_name or 'default'}")

            if not self.security.check_permission(api_key, "llm:generate"):
                raise AuthorizationError(
                    message="Insufficient permissions to generate text",
                    details={"required_permission": "llm:generate"}
                )

            if not self.model_manager:
                raise HTTPException(status_code=503, detail="Model manager not available")

            try:
                # Convert Pydantic model to dict for generate method if needed
                # Or update generate method to accept the Pydantic model directly
                generation_params = generate_request.model_dump(
                    exclude_none=True, exclude={'model', 'prompt'}
                )

                result = await self.model_manager.generate(
                    prompt=generate_request.prompt,
                    model_id=generate_request.model_name,
                    **generation_params
                )
                return GenerateResponse(**result)
            except ConfigurationError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(f"Generation error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Generation failed")

def create_app() -> FastAPI:
    """Factory function to create the LLMServer FastAPI app."""
    server = LLMServer()
    return server.app

# Create server instance ONLY when run directly or via app factory
# server = LLMServer() # Avoid module-level instantiation
# app = server.app # Avoid module-level instantiation

# You might need to adjust server/llm/__init__.py and tests/conftest.py
# if they directly imported the 'app' variable previously. 