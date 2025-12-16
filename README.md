# test-k

> ## 📚 **IMPORTANT: Full Documentation available**
> 
> **All project documentation, architecture details, and implementation guides are available at:**
> 
> ### **[https://osstorres.github.io/test-k/](https://osstorres.github.io/test-k/)**
> 
> Please refer to the documentation site for comprehensive information about the project.

---

## Kavak Commercial AI Agent

A commercial AI agent built with FastAPI, LlamaIndex, and OpenAI to answer questions about Kavak's value proposition, provide car catalog information, and calculate financing plans.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Python 3.12+ (if running locally)
- Environment variables configured (see `.env` file)

### Running with Docker

1. **Clone the repository:**
   ```bash
   git clone https://github.com/osstorres/test-k.git
   cd test-k
   ```

2. **Set up environment variables:**
   Create a `.env` file in the root directory with the required configuration variables.

3. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

4. **Access the API:**
   The API will be available at `http://localhost:8000`

5. **Check health endpoint:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

### Running Locally (Development)

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set up environment variables:**
   Configure your `.env` file with the necessary credentials and settings.

3. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Project Structure

```
test-k/
├── app/                    # Main application code
│   ├── api/               # API routes and endpoints
│   ├── core/              # Core configuration and services
│   ├── domain/            # Domain logic and agent workflows
│   ├── models/            # Data models and schemas
│   ├── persistence/       # Database models
│   └── repository/        # Data access layer
├── docs/                  # Documentation
├── infrastructure/        # Infrastructure as code (Terraform)
├── scripts/              # Utility scripts
└── tests/                # Test suite
```

## Key Technologies

- **FastAPI** - Web framework
- **LlamaIndex** - Agent orchestration
- **OpenAI** - LLM and embeddings
- **Qdrant** - Vector database
- **PostgreSQL** - Relational database
- **Redis** - Caching
- **Twilio** - WhatsApp integration
- **Arize** - LLM monitoring

## Documentation

For detailed documentation including:
- Architecture overview
- Development phases
- API endpoints
- Configuration guide
- Roadmap

Visit: **[https://osstorres.github.io/test-k/](https://osstorres.github.io/test-k/)**
