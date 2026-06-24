FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files    
# Lock file is required for uv to install the exact same dependencies
COPY pyproject.toml uv.lock ./  
# Copy main agent file
COPY agent.py ./

# Install dependencies and create a non-root user
RUN uv sync --no-dev && useradd --create-home appuser
USER appuser

# Expose port 8080
EXPOSE 8080

# Run the agent
CMD ["uv", "run", "agent.py"]
