# Use an official Python runtime as a parent image
# Choose a slim version for smaller image size
# Ensure Python version matches project requirement (>=3.13)
FROM python:3.13-slim

# Set environment variables
# Prevents Python from writing pyc files to disc (equivalent to python -B)
ENV PYTHONDONTWRITEBYTECODE 1
# Ensures Python output is sent straight to terminal (useful for logs)
ENV PYTHONUNBUFFERED 1

# Install uv for package management
# Using pip here as it's guaranteed to be in the base image
RUN pip install --no-cache-dir uv

# Set the working directory in the container
WORKDIR /app

# Copy the dependency definition file
COPY pyproject.toml ./

# Install project dependencies, including the [llm] optional group
# Use --system to install into the global site-packages, common in containers
# Include --no-cache to keep image size down
RUN uv pip install --system --no-cache --no-deps .[llm]
# Run install again to ensure all transitive dependencies are present (uv might optimize this in future)
# Alternatively, generate uv.lock locally and copy+sync it
RUN uv pip install --system --no-cache .[llm]

# Copy the application code into the container
COPY ./server /app/server/
COPY ./logs /app/logs/
# Add any other necessary files or directories here

# --- Runtime Configuration ---
# Define expected environment variables (can be set during `docker run`)
ENV MCP_PORT=7444
ENV LOG_LEVEL=INFO
# Note: API Keys like OPENAI_API_KEY should ideally be passed securely,
# e.g., via Docker secrets or runtime injection, not directly via -e in production.
# ENV OPENAI_API_KEY=""

# Expose the port the LLM server runs on (using the ENV variable)
EXPOSE $MCP_PORT

# Define the command to run the application
# Use environment variables to configure the server startup
# This requires the server's main entrypoint (__main__.py or similar)
# to parse these environment variables or use a config loader that does.
CMD ["python", "-m", "server.llm", "--port", "$MCP_PORT", "--log-level", "$LOG_LEVEL"] 