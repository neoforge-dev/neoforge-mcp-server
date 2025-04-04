# Neo DO MCP Server

The Neo DO MCP Server provides DigitalOcean operations and management capabilities through a REST API.

## Features

- **Operations**: List, create, and delete DigitalOcean droplets
- **Resource Management**: Power on/off, reboot, and shutdown droplets
- **Monitoring**: Get metrics for droplets (CPU, memory, disk, status)
- **Backup**: Create snapshots of droplets
- **Restore**: Restore droplets from snapshots
- **Scaling**: Resize droplets based on scaling factors

## Configuration

The server is configured through `config/neodo_mcp.yaml`:

```yaml
# Server identification
name: "Neo DO MCP Server"
version: "1.0.0"
port: 7449

# Logging
log_level: "DEBUG"
log_file: "logs/neodo_mcp.log"

# Security
auth_required: true
allowed_origins: ["*"]

# Resource limits
max_processes: 10
process_timeout: 300
max_memory_percent: 90.0
max_cpu_percent: 90.0
max_disk_percent: 90.0

# DO settings
enable_do_operations: true
enable_do_management: true
enable_do_monitoring: true
enable_do_backup: true
enable_do_restore: true
enable_do_scaling: true

# Monitoring
enable_metrics: true
metrics_port: 9096
enable_tracing: true
tracing_endpoint: "http://localhost:4317"

# Development
debug_mode: false
reload_on_change: false
```

## Environment Variables

- `DO_TOKEN`: DigitalOcean API token (required)
- `MCP_PORT`: Port to run the server on (default: 7449)

## API Endpoints

### Operations

- `POST /api/v1/do/operations`
  - Perform DigitalOcean operations
  - Supported operations:
    - `list_droplets`: List all droplets
    - `create_droplet`: Create a new droplet
    - `delete_droplet`: Delete a droplet

### Resource Management

- `POST /api/v1/do/management`
  - Manage DigitalOcean resources
  - Supported actions:
    - `power_on`: Power on a droplet
    - `power_off`: Power off a droplet
    - `reboot`: Reboot a droplet
    - `shutdown`: Shutdown a droplet

### Monitoring

- `GET /api/v1/do/monitoring`
  - Monitor DigitalOcean resources
  - Get metrics for:
    - Individual droplets (CPU, memory, disk, status)
    - Overall droplet statistics

### Backup

- `POST /api/v1/do/backup`
  - Create backups of DigitalOcean resources
  - Currently supports droplet snapshots

### Restore

- `POST /api/v1/do/restore`
  - Restore DigitalOcean resources from backups
  - Currently supports restoring droplets from snapshots

### Scaling

- `POST /api/v1/do/scale`
  - Scale DigitalOcean resources
  - Currently supports resizing droplets

## Security

All endpoints require API key authentication. The API key must be provided in the `X-API-Key` header.

Required permissions:
- `perform:operation`: Perform DO operations
- `manage:resources`: Manage DO resources
- `monitor:resources`: Monitor DO resources
- `backup:resources`: Backup DO resources
- `restore:resources`: Restore DO resources
- `scale:resources`: Scale DO resources

## Error Handling

The server uses the shared error handling utilities to provide consistent error responses:

- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Invalid or missing API key
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Monitoring

The server integrates with the shared monitoring utilities:

- Metrics are exposed on port 9096
- Tracing is sent to the configured endpoint
- Logs are written to the configured log file

## Development

To run the server in development mode:

```bash
export DO_TOKEN=your_do_token
python -m server.neodo
```

To run all servers:

```bash
python run_servers.py
``` 