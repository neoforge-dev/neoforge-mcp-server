"""LLM Model Manager implementation."""

import logging
from typing import List, Dict, Any, Optional
from pydantic import ValidationError

# Import new model structures
from .models import (
    BaseLanguageModel,
    BaseModelConfig,
    PlaceholderModelConfig,
    OpenAIModelConfig,
    LocalModelConfig,
    ModelConfigUnion # Union type for parsing
)

# Import ServerConfig for type hinting
from server.utils.config import ServerConfig
from server.utils.error_handling import ConfigurationError

# Mapping from provider string to config class
PROVIDER_CONFIG_MAP: Dict[str, type[BaseModelConfig]] = {
    "placeholder": PlaceholderModelConfig,
    "openai": OpenAIModelConfig,
    "local": LocalModelConfig,
}

class ModelManager:
    """Manages loading and accessing available language models based on configuration."""

    def __init__(self, config: ServerConfig):
        """Initialize the model manager and load models."""
        print(f"\nDEBUG: ModelManager.__init__ called with id={id(self)}")
        print(f"DEBUG: Config provided: name='{config.name}', models={config.llm_models}\n")
        self.config: ServerConfig = config
        self.logger = logging.getLogger(__name__) # Get logger instance
        self.models: Dict[str, BaseLanguageModel] = {}
        self._load_models()

    def _load_models(self):
        """Load models based on the server configuration."""
        self.logger.info("Loading language models...")
        if not hasattr(self.config, 'llm_models') or not self.config.llm_models:
            self.logger.warning("No language models defined in configuration ('llm_models' attribute missing or empty).")
            # Optionally load a default placeholder if none are defined?
            # For now, we just log and proceed with an empty model list.
            # default_config = PlaceholderModelConfig(model_id="fallback-placeholder")
            # ModelClass = default_config.get_model_class()
            # self.models[default_config.model_id] = ModelClass(config=default_config)
            # self.logger.info(f"Loaded fallback: {default_config.model_id}")
            # self.models['default'] = self.models[default_config.model_id]
            return

        loaded_model_ids = []
        for i, model_def in enumerate(self.config.llm_models):
            if not isinstance(model_def, dict):
                self.logger.error(f"Skipping invalid model definition at index {i}: Expected dict, got {type(model_def)}")
                continue

            provider = model_def.get("provider")
            if not provider or provider not in PROVIDER_CONFIG_MAP:
                self.logger.error(f"Skipping model definition at index {i}: Missing or unknown provider '{provider}'. Known providers: {list(PROVIDER_CONFIG_MAP.keys())}")
                continue

            ConfigClass = PROVIDER_CONFIG_MAP[provider]
            try:
                # Parse the dictionary into the specific config model
                model_config = ConfigClass(**model_def)
                model_id = model_config.model_id

                if model_id in self.models:
                     self.logger.warning(f"Skipping duplicate model_id '{model_id}' defined at index {i}.")
                     continue

                ModelClass = model_config.get_model_class()
                self.logger.info(f"Loading model '{model_id}' (Provider: {provider})...")

                # Instantiate the model
                # Add error handling for model instantiation (e.g., missing API key, invalid path)
                try:
                    self.models[model_id] = ModelClass(config=model_config)
                    self.logger.info(f"Successfully loaded model '{model_id}'.")
                    loaded_model_ids.append(model_id)
                except Exception as model_init_error:
                     self.logger.error(f"Failed to initialize model '{model_id}': {model_init_error}", exc_info=True)
                     # Decide if this should be fatal or just skip the model
                     # For now, we skip.

            except ValidationError as e:
                self.logger.error(f"Skipping model definition at index {i} due to validation error: {e}")
            except Exception as e:
                 self.logger.error(f"Skipping model definition at index {i} due to unexpected error: {e}", exc_info=True)

        # Set default model - use the first successfully loaded model
        if loaded_model_ids:
            default_model_id = loaded_model_ids[0]
            self.models['default'] = self.models[default_model_id]
            self.logger.info(f"Set default model to: '{default_model_id}'")
        else:
            self.logger.warning("No models were loaded successfully. No default model set.")


    def get_model(self, model_name: Optional[str] = None) -> BaseLanguageModel:
        """Get a specific model instance or the default."""
        target_name = model_name or 'default'

        if target_name in self.models:
            return self.models[target_name]
        elif model_name and model_name not in self.models:
             # Explicit name given, but not found (and not 'default')
             self.logger.error(f"Requested model '{model_name}' not found.")
             raise ValueError(f"Model '{model_name}' not found. Available models: {self.list_model_names()}")
        else: # 'default' was requested (explicitly or implicitly) but not set
            self.logger.error("Default model requested but no default model is configured or loaded.")
            raise ConfigurationError("No default language model available.")

    def list_models(self) -> List[BaseLanguageModel]:
        """List all successfully loaded models (excluding the 'default' alias)."""
        return [model for name, model in self.models.items() if name != 'default']

    def list_model_names(self) -> List[str]:
         """List the names (IDs) of all successfully loaded models."""
         return [name for name in self.models.keys() if name != 'default'] 