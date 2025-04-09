"""
Shared configuration management for MCP servers.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Set
from dataclasses import dataclass, field
from .error_handling import MCPError

@dataclass
class ServerConfig:
    """Server configuration."""
    
    def __init__(
        self,
        name: str = "mcp_server",
        version: str = "1.0.0",
        port: int = 8000,
        log_level: str = "info",
        max_processes: int = 4,
        max_memory_percent: float = 90.0,
        max_cpu_percent: float = 90.0,
        max_disk_percent: float = 90.0,
        max_runtime: int = 3600,
        check_resources: bool = True,
        resource_limits: Optional[Dict[str, float]] = None,
        # Connection settings
        connection_timeout: int = 30,
        keep_alive_timeout: int = 60,
        max_requests_per_connection: int = 1000,
        # File operations
        enable_file_operations: bool = True,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        allowed_extensions: List[str] = None,
        # DigitalOcean settings
        enable_do_operations: bool = False,
        enable_do_management: bool = False,
        enable_do_monitoring: bool = False,
        enable_do_backup: bool = False,
        enable_do_restore: bool = False,
        enable_do_scaling: bool = False,
        # Local model settings
        enable_local_models: bool = False,
        model_path: str = "models",
        local_model_path: str = "models/local",
        model_cache_size: int = 100,
        # LLM generation settings
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        repetition_penalty: float = 1.1,
        stop_sequences: List[str] = None,
        # API keys
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        do_token: Optional[str] = None,
        api_keys: Optional[Dict[str, str]] = None,
        # Security settings
        enable_auth: bool = False,
        auth_token: Optional[str] = None,
        allowed_origins: List[str] = None,
        # Session settings (Added)
        enable_sessions: bool = False,
        session_secret: Optional[str] = None,
        # Monitoring settings
        enable_metrics: bool = False,
        metrics_port: int = 9090,
        enable_health_checks: bool = True,
        health_check_interval: int = 30,
        enable_tracing: bool = False,
        tracing_endpoint: str = "http://localhost:4317",
        # Logging settings
        log_file: str = "mcp_server.log",
        log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        log_rotation: str = "1 day",
        log_retention: int = 7,
        # Cache settings
        enable_cache: bool = True,
        cache_size: int = 1000,
        cache_ttl: int = 3600,
        # Rate limiting
        enable_rate_limiting: bool = True,
        default_rate_limit: str = "100/minute",
        # SSL/TLS settings
        enable_ssl: bool = False,
        ssl_cert: Optional[str] = None,
        ssl_key: Optional[str] = None,
        # Proxy settings
        enable_proxy: bool = False,
        proxy_protocol: bool = False,
        trusted_proxies: List[str] = None,
        # Compression settings
        enable_compression: bool = True,
        compression_level: int = 6,
        # Timeout settings
        request_timeout: int = 30,
        response_timeout: int = 30,
        connect_timeout: int = 5,
        # Worker settings
        worker_class: str = "uvicorn.workers.UvicornWorker",
        worker_connections: int = 1000,
        worker_timeout: int = 30,
        # Debug settings
        debug: bool = False,
        reload: bool = False,
        reload_dirs: List[str] = None,
        # API documentation
        enable_docs: bool = True,
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        openapi_url: str = "/openapi.json",
        # Development settings
        enable_code_generation: bool = False,
        enable_code_analysis: bool = False,
        enable_test_generation: bool = False,
        enable_documentation: bool = False,
        enable_debugging: bool = False,
        enable_profiling: bool = False,
        enable_quantization: bool = False,
        enable_caching: bool = False,
        enable_streaming: bool = False,
        # Local development settings
        enable_local_development: bool = False,
        enable_local_testing: bool = False,
        enable_local_deployment: bool = False,
        enable_local_monitoring: bool = False,
        enable_local_backup: bool = False,
        enable_local_restore: bool = False,
        # Operations settings
        enable_process_management: bool = False,
        enable_resource_monitoring: bool = False,
        enable_system_commands: bool = False,
        enable_network_operations: bool = False,
        enable_backup_operations: bool = False,
    ):
        """Initialize server configuration."""
        self.name = name
        self.version = version
        self.port = port
        self.log_level = log_level
        self.max_processes = max_processes
        self.max_memory_percent = max_memory_percent
        self.max_cpu_percent = max_cpu_percent
        self.max_disk_percent = max_disk_percent
        self.max_runtime = max_runtime
        self.check_resources = check_resources
        self.resource_limits = resource_limits or {
            "cpu_percent": 95.0,
            "memory_percent": 95.0,
            "disk_percent": 95.0
        }
        
        # Connection settings
        self.connection_timeout = connection_timeout
        self.keep_alive_timeout = keep_alive_timeout
        self.max_requests_per_connection = max_requests_per_connection
        
        # File operations
        self.enable_file_operations = enable_file_operations
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions or []
        
        # DigitalOcean settings
        self.enable_do_operations = enable_do_operations
        self.enable_do_management = enable_do_management
        self.enable_do_monitoring = enable_do_monitoring
        self.enable_do_backup = enable_do_backup
        self.enable_do_restore = enable_do_restore
        self.enable_do_scaling = enable_do_scaling
        
        # Local model settings
        self.enable_local_models = enable_local_models
        self.model_path = model_path
        self.local_model_path = local_model_path
        self.model_cache_size = model_cache_size
        
        # LLM generation settings
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.repetition_penalty = repetition_penalty
        self.stop_sequences = stop_sequences or []
        
        # API keys
        self.anthropic_api_key = anthropic_api_key
        self.openai_api_key = openai_api_key
        self.do_token = do_token
        self.api_keys = api_keys or {}
        
        # Security settings
        self.enable_auth = enable_auth
        self.auth_token = auth_token
        self.allowed_origins = allowed_origins or []
        
        # Session settings (Added)
        self.enable_sessions = enable_sessions
        self.session_secret = session_secret

        # Monitoring settings
        self.enable_metrics = enable_metrics
        self.metrics_port = metrics_port
        self.enable_health_checks = enable_health_checks
        self.health_check_interval = health_check_interval
        self.enable_tracing = enable_tracing
        self.tracing_endpoint = tracing_endpoint
        
        # Logging settings
        self.log_file = log_file
        self.log_format = log_format
        self.log_rotation = log_rotation
        self.log_retention = log_retention
        
        # Cache settings
        self.enable_cache = enable_cache
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        
        # Rate limiting
        self.enable_rate_limiting = enable_rate_limiting
        self.default_rate_limit = default_rate_limit
        
        # SSL/TLS settings
        self.enable_ssl = enable_ssl
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        
        # Proxy settings
        self.enable_proxy = enable_proxy
        self.proxy_protocol = proxy_protocol
        self.trusted_proxies = trusted_proxies or []
        
        # Compression settings
        self.enable_compression = enable_compression
        self.compression_level = compression_level
        
        # Timeout settings
        self.request_timeout = request_timeout
        self.response_timeout = response_timeout
        self.connect_timeout = connect_timeout
        
        # Worker settings
        self.worker_class = worker_class
        self.worker_connections = worker_connections
        self.worker_timeout = worker_timeout
        
        # Debug settings
        self.debug = debug
        self.reload = reload
        self.reload_dirs = reload_dirs or []
        
        # API documentation
        self.enable_docs = enable_docs
        self.docs_url = docs_url
        self.redoc_url = redoc_url
        self.openapi_url = openapi_url
        
        # Development settings
        self.enable_code_generation = enable_code_generation
        self.enable_code_analysis = enable_code_analysis
        self.enable_test_generation = enable_test_generation
        self.enable_documentation = enable_documentation
        self.enable_debugging = enable_debugging
        self.enable_profiling = enable_profiling
        self.enable_quantization = enable_quantization
        self.enable_caching = enable_caching
        self.enable_streaming = enable_streaming
        
        # Local development settings
        self.enable_local_development = enable_local_development
        self.enable_local_testing = enable_local_testing
        self.enable_local_deployment = enable_local_deployment
        self.enable_local_monitoring = enable_local_monitoring
        self.enable_local_backup = enable_local_backup
        self.enable_local_restore = enable_local_restore
        
        # Operations settings
        self.enable_process_management = enable_process_management
        self.enable_resource_monitoring = enable_resource_monitoring
        self.enable_system_commands = enable_system_commands
        self.enable_network_operations = enable_network_operations
        self.enable_backup_operations = enable_backup_operations

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

class ConfigManager:
    """Manages server configuration loading and validation."""
    
    def __init__(
        self,
        config_dir: Union[str, Path] = "config",
        env_prefix: str = "MCP_"
    ):
        """Initialize config manager.
        
        Args:
            config_dir: Directory containing config files
            env_prefix: Prefix for environment variables
        """
        self.config_dir = Path(config_dir)
        self.env_prefix = env_prefix
        self.configs: Dict[str, ServerConfig] = {}
        
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML config file."""
        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise MCPError(
                f"Failed to load config file: {path}",
                error_code="CONFIG_ERROR",
                details={"error": str(e)}
            )
            
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON config file."""
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            raise MCPError(
                f"Failed to load config file: {path}",
                error_code="CONFIG_ERROR",
                details={"error": str(e)}
            )
            
    def _get_env_value(self, key: str) -> Optional[str]:
        """Get value from environment variables."""
        env_key = f"{self.env_prefix}{key.upper()}"
        return os.environ.get(env_key)
        
    def _apply_env_overrides(self, config: Dict[str, Any]) -> None:
        """Apply environment variable overrides."""
        for key in config:
            env_value = self._get_env_value(key)
            if env_value is not None:
                # Convert environment value to appropriate type
                current_value = config[key]
                if isinstance(current_value, bool):
                    config[key] = env_value.lower() in ('true', '1', 'yes')
                elif isinstance(current_value, int):
                    config[key] = int(env_value)
                elif isinstance(current_value, float):
                    config[key] = float(env_value)
                elif isinstance(current_value, (list, set)):
                    config[key] = env_value.split(',')
                else:
                    config[key] = env_value
                    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration values."""
        required_fields = {'name', 'port'}
        missing = required_fields - set(config.keys())
        if missing:
            raise MCPError(
                "Missing required config fields",
                error_code="CONFIG_ERROR",
                details={"missing_fields": list(missing)}
            )
            
        # Validate port range
        if not 1024 <= config['port'] <= 65535:
            raise MCPError(
                "Invalid port number",
                error_code="CONFIG_ERROR",
                details={"port": config['port']}
            )
            
        # Validate percentage values
        for key in ['max_memory_percent', 'max_cpu_percent', 'max_disk_percent']:
            if key in config and not 0 <= config[key] <= 100:
                raise MCPError(
                    f"Invalid percentage value for {key}",
                    error_code="CONFIG_ERROR",
                    details={key: config[key]}
                )
                
    def load_config(self, server_name: str) -> ServerConfig:
        """Load configuration for a server, merging with default.yaml."""
        if server_name in self.configs:
            return self.configs[server_name]

        # 1. Load default config first
        default_config_data = {}
        default_path = self.config_dir / "default.yaml"
        if default_path.exists():
            try:
                default_config_data = self._load_yaml(default_path)
            except Exception as e:
                # Handle potential errors loading default config, maybe log?
                print(f"Warning: Could not load default config {default_path}: {e}") 

        # 2. Load server-specific config
        server_config_data = {}
        config_files = [
            (self.config_dir / f"{server_name}.yaml", self._load_yaml),
            (self.config_dir / f"{server_name}.yml", self._load_yaml),
            (self.config_dir / f"{server_name}.json", self._load_json)
        ]
        for path, loader in config_files:
            if path.exists():
                try:
                    server_config_data = loader(path)
                    break # Found server specific, stop looking
                except Exception as e:
                     print(f"Warning: Could not load server config {path}: {e}") 
                     break # Stop trying if error on specific file

        # 3. Merge configs (server-specific overrides default)
        # Use dict unpacking for merging (Python 3.5+)
        # Ensure nested dictionaries are merged recursively if needed (simple update here)
        # A more robust merge might be needed for deeply nested structures
        merged_config_data = {**default_config_data, **server_config_data}

        # 4. Ensure server name is set (use provided name over config file)
        merged_config_data['name'] = server_name

        # 5. Apply environment overrides (after merging)
        self._apply_env_overrides(merged_config_data)

        # 6. Validate final merged config
        self._validate_config(merged_config_data)

        # 7. Create config object
        try:
            config = ServerConfig(**merged_config_data)
            self.configs[server_name] = config
            return config
        except TypeError as e:
            # Catch errors if merged_config_data has keys not in ServerConfig
            raise MCPError(f"Configuration error for {server_name}: Invalid key found - {e}")
        
    def save_config(self, config: ServerConfig, format: str = 'yaml') -> None:
        """Save configuration to file.
        
        Args:
            config: ServerConfig to save
            format: Output format ('yaml' or 'json')
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        config_dict = config.to_dict()
        
        if format == 'yaml':
            path = self.config_dir / f"{config.name}.yaml"
            with open(path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        elif format == 'json':
            path = self.config_dir / f"{config.name}.json"
            with open(path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    def get_all_configs(self) -> Dict[str, ServerConfig]:
        """Get all loaded configurations.
        
        Returns:
            Dictionary of server name to ServerConfig
        """
        return self.configs.copy() 