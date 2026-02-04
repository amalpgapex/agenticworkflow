# Introduction
Deloitte InK Catalyst NextGen AI Foundation is an intelligent, agent-based workflow orchestration system built on Azure that enables:
* Dynamic Workflow Creation: Users define custom workflows by selecting and sequencing skills
* AI-Powered Processing: GenAI for comparison, alignment, classification, summarization, and generation
* Human-in-the-Loop: Configurable review points at any step for human oversight
* Prompt Management: Versioned prompts that can be modified during execution
* Continuous Evaluation: Automated quality assessment at each step


## Project Structure

The project is organized into several key components:

- **`src/catalyst-nextgen-api`**: FastAPI backend for workflow management with Azure Cosmos DB integration
- **`src/catalyst-nextgen-devui`**: Developer UI for running and testing agents and workflows locally
- **`src/catalyst-nextgen-mcp-server`**: Model Context Protocol server for agent capabilities
- **`src/catalyst-nextgen-ui-poc`**: Frontend proof-of-concept interface
- **`infra/`**: Terraform infrastructure as code for Azure deployment
- **`docs/`**: Architecture and configuration documentation


## Getting Started

### Prerequisites

- [VS Code](https://code.visualstudio.com/download)
- **Python 3.12+**
- **uv** (Python package manager) - [Install uv](https://docs.astral.sh/uv/getting-started/)
- **Node.js 18+** (for frontend development)
- **Git**

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd deloitte-ink-genai-catalystfuture
   ```

2. **Install system dependencies** (if needed)
   - For Windows: Use PowerShell with administrator privileges
   - For macOS/Linux: Use your system package manager


## Setting Up the DevUI Project

The `catalyst-nextgen-devui` project is a standalone sample application for running agents and workflows locally with a developer-friendly web interface.

### Local Development Setup

1. **Navigate to the DevUI directory**
   ```bash
   cd src/catalyst-nextgen-devui
   ```

2. **Create and activate virtual environment with uv**
   ```bash
   uv venv
   source .venv/bin/activate          # On macOS/Linux
   # or
   .venv\Scripts\Activate.ps1         # On Windows PowerShell
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```
   This installs:
   - **agent-framework**: Microsoft Agent Framework SDK
   - **azure-identity**: Azure authentication
   - **azure-cosmos**: Azure Cosmos DB client for checkpoint persistence
   - **uvicorn**: ASGI web server
   - **fastapi**: Web framework

4. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```bash
   cp .env.example .env  # If available, or create manually
   ```
   
   Add your configuration:
   ```env
   # OpenAI Configuration (minimum required)
   OPENAI_API_KEY="your-openai-api-key"
   OPENAI_CHAT_MODEL_ID="gpt-4o-mini"

   # Or use Azure OpenAI
   AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
   AZURE_OPENAI_API_KEY="your-azure-api-key"
   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="your-deployment"

   # Optional: Cosmos DB for checkpoint storage
   COSMOS_ENDPOINT="https://your-cosmosdb.documents.azure.com:443/"
   COSMOS_KEY="your-cosmos-primary-key"
   COSMOS_DATABASE="checkpoint_db"
   COSMOS_CONTAINER="checkpoints"
   ```

### Running the DevUI Server

#### Option 1: In-Memory Mode (Quick Testing)
```bash
# Run with built-in sample workflows
uv run -m agent_framework_devui
```

This will:
- Start the DevUI server on `http://localhost:8080`
- Load sample agents and workflows from the `samples/` directory
- Provide a web interface for testing

#### Option 2: Custom Workflows
```bash
# Create your agents/workflows in the appropriate directory
# See Directory Structure section below

# Launch with directory discovery
devui ./workflows --port 8080
```

#### Option 3: Programmatic Launch
Create a Python script to launch with custom entities:
```python
from agent_framework_devui import serve
from your_module import your_agent, your_workflow

if __name__ == "__main__":
    serve(
        entities=[your_agent, your_workflow],
        port=8080,
        host="127.0.0.1",
        ui_enabled=True
    )
```

### Accessing the DevUI

Once the server is running:
- **Web UI**: Open http://localhost:8080 in your browser
- **API Endpoint**: http://localhost:8080/v1/
- **Documentation**: http://localhost:8080/docs (if enabled)

### Frontend Development

To develop or modify the DevUI frontend:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

The frontend is built with Vite and TypeScript.

### Checkpoint Storage - Work in progress

The project supports two checkpoint storage backends:

#### File-Based Storage (Default)
```python
from agent_framework_devui import FileCheckpointStorage

storage = FileCheckpointStorage(storage_path="./checkpoints")
```

#### Azure Cosmos DB Storage (Recommended for Production)
```python
from agent_framework_devui import CosmosDBCheckpointStorage

storage = CosmosDBCheckpointStorage(
    cosmos_endpoint=os.environ["COSMOS_ENDPOINT"],
    cosmos_key=os.environ["COSMOS_KEY"],
    database_name="checkpoint_db",
    container_name="checkpoints"
)
await storage.initialize()
```

### Troubleshooting

**"asyncio.run() cannot be called from a running event loop"**
- This occurs when `asyncio.run()` is called from within an async context
- Ensure your main entry point doesn't wrap the `serve()` call in `asyncio.run()`
- Solution: Only use `asyncio.run()` for async setup, not for the `serve()` call itself

**Port already in use**
```bash
# Change the port
uv run -m agent_framework_devui -- --port 8081
```

**Module not found errors**
- Ensure `PYTHONPATH` includes parent directories if importing from sibling modules
- Use `PYTHONPATH=.. uv run -m agent_framework_devui`

**Cosmos DB connection fails**
- Verify `COSMOS_ENDPOINT` and `COSMOS_KEY` in `.env`
- Check that the database and container exist in your Cosmos DB account
- Ensure Azure credentials have necessary permissions

## Build and Test

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_checkpoints.py

# Run with coverage
uv run pytest --cov=agent_framework_devui
```

### Code Quality

```bash
# Format code
uv run black .

# Lint
uv run ruff check .

# Type checking
uv run mypy src/
```

### Building the Project

```bash
# Build distribution packages
uv build

# This creates:
# - dist/devui-0.1.0-py3-none-any.whl
# - dist/devui-0.1.0.tar.gz
```

## Contribute

Please make all changes to the codebase using a feature branch. Then, request a PR and have a colleague review the change before merging to the main branch.

### Development Workflow

1. Create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and test locally
   ```bash
   uv run pytest
   uv run black .
   uv run ruff check .
   ```

3. Commit and push
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature/your-feature-name
   ```

4. Create a pull request on GitHub

### Key Files to Review

- [DevUI README](./src/catalyst-nextgen-devui/README.md) - Detailed DevUI documentation
- [Dev Setup Guide](./src/catalyst-nextgen-devui/dev.md) - Development environment guide
- [Architecture](./docs/ARCHITECTURE.MD) - System architecture overview
- [MCP Server Documentation](./docs/MCP_Server_documentation.md) - MCP server details