# Catalyst NextGen API

FastAPI backend for workflow management with Azure Cosmos DB integration.

## Features

- ✅ **Workflow Management**: CRUD operations for user workflows
- ✅ **Azure Cosmos DB Integration**: Efficient data storage with partition key optimization
- ✅ **User Authentication**: Header-based authentication (ready for JWT)
- ✅ **RESTful API**: Well-documented endpoints with OpenAPI/Swagger
- ✅ **Async Operations**: High-performance async database operations
- ✅ **Type Safety**: Pydantic models for request/response validation

## Project Structure

```
catalyst-nextgen-api/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── app/
│   ├── __init__.py
│   ├── config.py          # Application configuration
│   ├── database.py        # Cosmos DB client and operations
│   ├── models.py          # Pydantic models and schemas
│   ├── auth.py            # Authentication dependencies
│   └── routes/
│       ├── __init__.py
│       └── workflows.py   # Workflow API endpoints
```

## Setup

### 1. Install Dependencies

```bash
cd src/catalyst-nextgen-api
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and update with your values:

```bash
cp .env.example .env
```

Update the following in your `.env` file:

```env
COSMOS_ENDPOINT=https://your-cosmosdb-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-db-key
COSMOS_DATABASE=InKCatalystNextGenDB
COSMOS_CONTAINER=Projects
```

### 3. Run the Application

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use Python directly
python main.py
```

The API will be available at: `http://localhost:8000`

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### Health Check
- `GET /health` - Check API health status

### Workflows
All workflow endpoints require authentication via the `X-User-Id` header.

- `GET /api/v1/workflows` - List all workflows for authenticated user
  - Query params: `limit` (1-100), `status_filter` (draft|active|completed|archived)
- `GET /api/v1/workflows/{workflow_id}` - Get specific workflow
- `POST /api/v1/workflows` - Create new workflow
- `PUT /api/v1/workflows/{workflow_id}` - Update workflow
- `DELETE /api/v1/workflows/{workflow_id}` - Delete workflow
- `POST /api/v1/workflows/{workflow_id}/duplicate` - Duplicate workflow

## Authentication

Currently uses header-based authentication for development:

```bash
curl -H "X-User-Id: user@example.com" http://localhost:8000/api/v1/workflows
```

**Production**: Update `app/auth.py` to implement JWT or Azure AD authentication.

## Example Usage

### Create a Workflow

```bash
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user@example.com" \
  -d '{
    "name": "Document Analysis Pipeline",
    "description": "Analyze and transform documents using AI",
    "canvas_type": "transformation",
    "status": "draft",
    "steps": [
      {
        "step_id": "step_001",
        "step_type": "transform",
        "step_name": "Extract Text",
        "config": {"model": "gpt-4"},
        "order": 1
      }
    ],
    "metadata": {"tags": ["analysis"]}
  }'
```

### Get All Workflows

```bash
curl -H "X-User-Id: user@example.com" \
  "http://localhost:8000/api/v1/workflows?limit=10&status_filter=active"
```

### Update a Workflow

```bash
curl -X PUT http://localhost:8000/api/v1/workflows/{workflow_id} \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user@example.com" \
  -d '{
    "status": "active",
    "description": "Updated description"
  }'
```

## Data Model

### Workflow Document Structure

```json
{
  "id": "workflow_123",
  "name": "Document Transformation Pipeline",
  "description": "Transform documents using AI",
  "canvas_type": "transformation",
  "status": "active",
  "CreatedBy": "user@example.com",
  "CreatedAt": "2025-12-30T10:00:00Z",
  "UpdatedAt": "2025-12-30T10:00:00Z",
  "steps": [
    {
      "step_id": "step_001",
      "step_type": "transform",
      "step_name": "Extract Text",
      "config": {},
      "order": 1
    }
  ],
  "metadata": {}
}
```

### Cosmos DB Configuration

- **Database**: `InKCatalystNextGenDB`
- **Container**: `Projects`
- **Partition Key**: `/CreatedBy` (user ID)

This design ensures:
- ✅ Efficient user-specific queries (single partition reads)
- ✅ Isolated data per user
- ✅ Optimized RU consumption

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (when implemented)
pytest
```

### Code Quality

```bash
# Format code
black .

# Lint
flake8 .

# Type checking
mypy .
```

## Deployment

### Azure App Service

1. Update `COSMOS_ENDPOINT` and `COSMOS_KEY` in App Service configuration
2. Set `APP_ENV=production`
3. Deploy using Azure CLI:

```bash
az webapp up --name catalyst-nextgen-api --runtime PYTHON:3.11
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Next Steps

- [ ] Implement JWT authentication
- [ ] Add Azure AD integration
- [ ] Implement workflow execution endpoints
- [ ] Add workflow versioning
- [ ] Implement workflow sharing/permissions
- [ ] Add rate limiting
- [ ] Add request logging and monitoring
- [ ] Implement caching layer
- [ ] Add comprehensive unit tests
- [ ] Add integration tests

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

Internal Deloitte Project