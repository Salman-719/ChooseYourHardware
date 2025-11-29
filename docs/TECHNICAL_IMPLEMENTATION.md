# Technical Implementation Documentation

This document describes the actual implementation details of the ChooseYourHardware project, focusing on the functional API, user interface, reproducibility, and code structure.

## 1. Functional API (Dockerized)

### 1.1 API Framework

**Technology Stack:**
- **Framework**: FastAPI (Python web framework)
- **Server**: Uvicorn ASGI server
- **Python Version**: 3.11 (as specified in Dockerfile)

### 1.2 API Structure

The API is organized under `src/api/`:

```
src/api/
├── main.py                    # Application entry point
└── v1/
    ├── endpoints/
    │   ├── models.py         # Model analysis endpoints
    │   ├── hardware.py       # Hardware analysis endpoints
    │   ├── metadata.py       # Metadata extraction endpoints
    │   └── matcher.py        # Hardware matching endpoints
    └── schemas/              # Pydantic request/response models
```

### 1.3 Available Endpoints

**Core Endpoints:**
- `GET /health` - Health check endpoint
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

**API v1 Endpoints (prefix: `/api/v1`):**
- `POST /models/analyze` - Analyze ML model requirements
- `POST /hardware/analyze` - Analyze hardware specifications
- `POST /metadata/extract` - Interactive metadata extraction (requires OpenAI API key)
- `POST /matcher/best` - Find best hardware match for a model
- `GET /hardware/` - List available hardware devices
- `POST /hardware/crawl` - Trigger hardware catalog crawl (requires OpenAI API key)

### 1.4 Dockerization

**Dockerfile Configuration:**
```dockerfile
Base Image: python:3.11-slim
Working Directory: /app
Environment Variables:
  - PYTHONUNBUFFERED=1
  - PYTHONDONTWRITEBYTECODE=1
  - PYTHONPATH=/app/src
Port: 8080 (configurable via $PORT environment variable)
User: Non-root user (appuser, uid 1000)
Health Check: HTTP GET to /health endpoint every 30s
```

**Build Process:**
1. Install system dependencies (gcc for compilation)
2. Install Python dependencies from `requirements.txt`
3. Copy application code
4. Install package in editable mode (`pip install -e .`)
5. Create non-root user for security
6. Configure health checks

**Running the Container:**
```bash
docker build -t chooseyourhardware .
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your-key \
  -e PORT=8080 \
  chooseyourhardware
```

### 1.5 API Configuration

Configuration is managed via Pydantic Settings (`src/config/settings.py`):

**Settings Class:**
```python
class Settings(BaseSettings):
    # API Configuration
    app_version: str = "1.0.0"
    environment: str = "development" (alias: ENV)
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # OpenAI Configuration (optional)
    openai_api_key: Optional[str] (alias: OPENAI_API_KEY)
    openai_model: str = "gpt-4.1-2025-04-14" (alias: OPENAI_LLM_MODEL)
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "text"  # "json" or "text"
    
    # CORS
    cors_origins: list[str] = ["*"]
```

Configuration is loaded from:
1. Environment variables
2. `.env` file (if present)
3. Default values

### 1.6 CORS Configuration

The API includes CORS middleware configuration:
```python
CORSMiddleware(
    allow_origins=["*"],  # Configurable for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

---

## 2. User Interface

### 2.1 Technology Stack

**Frontend Framework:**
- **Library**: React 18.3.1
- **Language**: TypeScript 5.8.3
- **Build Tool**: Vite 5.4.19
- **Routing**: React Router DOM 6.30.1

### 2.2 UI Component Library

**shadcn/ui** - A collection of re-usable components built with:
- Radix UI primitives (accessibility-focused)
- Tailwind CSS for styling
- Class Variance Authority for component variants

**Installed Radix UI Components:**
- Accordion, Alert Dialog, Aspect Ratio, Avatar
- Checkbox, Collapsible, Context Menu, Dialog
- Dropdown Menu, Hover Card, Label, Menubar
- Navigation Menu, Popover, Progress, Radio Group
- Scroll Area, Select, Separator, Slider
- Switch, Tabs, Toast, Toggle, Tooltip

### 2.3 Application Structure

```
Frontend/northlane-partner-hub/
├── src/
│   ├── pages/
│   │   ├── Index.tsx          # Landing page
│   │   ├── Chatbot.tsx        # Main interaction interface
│   │   ├── HardwareFilter.tsx # Hardware filtering interface
│   │   └── NotFound.tsx       # 404 page
│   ├── components/            # Reusable UI components
│   ├── hooks/                 # Custom React hooks
│   ├── lib/                   # Utility functions
│   ├── App.tsx               # Main application component
│   └── main.tsx              # Application entry point
├── public/                   # Static assets
├── index.html               # HTML template
├── vite.config.ts          # Vite configuration
├── tailwind.config.ts      # Tailwind CSS configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Dependencies and scripts
```

### 2.4 Development & Build Scripts

**Available Commands:**
```json
"dev": "vite"                    # Start development server
"build": "vite build"            # Production build
"build:dev": "vite build --mode development"  # Development build
"lint": "eslint ."               # Lint code
"preview": "vite preview"        # Preview production build
```

### 2.5 Development Server Configuration

```typescript
server: {
  host: "::",      # Listen on all interfaces (IPv6)
  port: 8080       # Development server port
}
```

### 2.6 State Management & Data Fetching

**TanStack Query (React Query) v5.83.0**
- Server state management
- Automatic caching and refetching
- Background updates

**React Hook Form v7.61.1**
- Form state management
- Validation with Zod schemas

### 2.7 Additional UI Features

- **Theming**: `next-themes` for dark/light mode
- **Charts**: `recharts` for data visualization
- **Toast Notifications**: `sonner` for user feedback
- **Date Picker**: `react-day-picker` with `date-fns`
- **Carousels**: `embla-carousel-react`
- **Resizable Panels**: `react-resizable-panels`

### 2.8 Styling Approach

- **Tailwind CSS** - Utility-first CSS framework
- **CSS Animations** - `tailwindcss-animate`
- **Typography Plugin** - `@tailwindcss/typography`
- **Custom Utilities** - `tailwind-merge`, `class-variance-authority`, `clsx`

---

## 3. Reproducibility

### 3.1 Environment Files

#### 3.1.1 Backend Environment (`.env`)

**Example Configuration** (`.env.example`):
```bash
# OpenAI Configuration (Optional)
OPENAI_API_KEY=your-api-key-here
OPENAI_LLM_MODEL=gpt-4o-mini

# API Configuration
ENV=production
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text

# Google Cloud Configuration (Backend Deployment)
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCP_SERVICE_NAME=chooseyourhardware-api
GCP_MEMORY=2Gi
GCP_CPU=1
GCP_MIN_INSTANCES=0
GCP_MAX_INSTANCES=10
GCP_TIMEOUT=300

# Firebase Configuration (Frontend Deployment)
FIREBASE_SITE_ID=easyware
FIREBASE_BACKEND_URL=https://your-backend-url.a.run.app/api/v1
```

#### 3.1.2 Python Dependencies

**`requirements.txt`** - Contains all Python dependencies with version constraints:
- Core framework dependencies (FastAPI, Uvicorn, Pydantic)
- OpenAI SDK for LLM features
- HTTP client libraries (httpx)
- Configuration management (python-dotenv, pydantic-settings)
- Data processing (numpy)
- Network and ML libraries

**Note**: Currently uses `>=` version constraints. For strict reproducibility, consider pinning exact versions.

#### 3.1.3 Frontend Dependencies

**`package.json`** - Locked dependencies:
- Dependencies locked via `bun.lockb` (Bun package manager)
- All packages have specific versions (not ranges)
- Dev dependencies separated from production dependencies

**Lock File**: `bun.lockb` ensures exact dependency versions across installations.

### 3.2 Python Package Configuration

**`pyproject.toml`** - Package metadata and configuration:

```toml
[project]
name = "choose-your-hardware"
version = "1.0.0"
requires-python = ">=3.9"

[project.scripts]
analyze-model = "cli.model_cli:cli_entry"
analyze-hardware = "cli.hardware_cli:cli_entry"
```

**Installation Methods:**
1. **Editable Install** (Development):
   ```bash
   pip install -e .
   ```

2. **From Requirements** (Deployment):
   ```bash
   pip install -r requirements.txt
   ```

### 3.3 Version Control

**`.gitignore`** excludes:
- Environment files (`.env`)
- Virtual environments (`.venv`, `venv`)
- Python cache files (`__pycache__`, `*.pyc`)
- Node modules (`Frontend/northlane-partner-hub/node_modules`)
- Local environment files (`.env.local`)
- System files (`.DS_Store`)
- Log files (`logs/`)

### 3.4 Reproducible Setup Instructions

#### Backend Setup
```bash
# 1. Clone repository
git clone https://github.com/Salman-719/ChooseYourHardware.git
cd ChooseYourHardware

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install package
pip install -e .

# 5. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 6. Run API
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
# 1. Navigate to frontend
cd Frontend/northlane-partner-hub

# 2. Install dependencies (using Bun)
bun install

# 3. Start development server
bun run dev

# 4. Build for production
bun run build
```

#### Docker Setup
```bash
# 1. Build image
docker build -t chooseyourhardware .

# 2. Run container
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your-key \
  -e PORT=8080 \
  chooseyourhardware
```

### 3.5 Deterministic Behavior

**Current State:**
- ✅ Python dependencies specified in `requirements.txt`
- ✅ Frontend dependencies locked via `bun.lockb`
- ✅ Docker base image pinned (`python:3.11-slim`)
- ✅ Environment configuration via `.env.example`
- ⚠️ Python versions use `>=` constraints (not fully pinned)
- ❌ No explicit random seeds in code (for analytical models, not ML training)

**Recommendations for Enhanced Reproducibility:**
1. Pin exact Python package versions (`package==version` instead of `package>=version`)
2. Use `pip freeze > requirements-lock.txt` for deployment
3. Document Python interpreter version explicitly
4. Add checksums for downloaded models/data if applicable

---

## 4. Clean Code Structure

### 4.1 Project Organization

The project follows a modular, domain-driven structure:

```
ChooseYourHardware/
├── src/                      # Backend source code
│   ├── analyzers/           # Domain: Model & Hardware Analysis
│   ├── matchers/            # Domain: Hardware Matching Logic
│   ├── metadata_extractor/  # Domain: LLM-powered Extraction
│   ├── api/                 # Presentation: REST API
│   ├── cli/                 # Presentation: Command-line Interface
│   ├── config/              # Configuration & Constants
│   └── utils/               # Shared Utilities
├── Frontend/                # Frontend application
├── deployment/              # Deployment automation scripts
├── device_data/            # Hardware specifications (data)
├── docs/                   # Documentation
└── [config files]          # Root-level configuration
```

### 4.2 Backend Architecture

#### 4.2.1 Analyzers Module (`src/analyzers/`)

**Purpose**: Compute requirements for models and normalize hardware specifications

**Structure:**
```
analyzers/
├── model/
│   ├── core.py              # Model analysis orchestrator
│   ├── classical/           # Classical ML algorithms
│   │   ├── knn.py          # K-Nearest Neighbors
│   │   ├── kmeans.py       # K-Means Clustering
│   │   └── trees.py        # Decision Trees & Ensembles
│   └── neural/              # Neural Network models
│       ├── layers.py        # Layer-wise analysis
│       ├── transformers.py  # Transformer models
│       └── llm.py          # Large Language Models
└── hardware/
    ├── core.py             # Hardware spec normalization
    └── utils.py            # FLOPS & bandwidth calculations
```

**Design Principles:**
- Single Responsibility: Each analyzer handles one model type
- Composition: `core.py` orchestrates specialized analyzers
- Pure Functions: Analyzers are stateless, deterministic functions

#### 4.2.2 Matchers Module (`src/matchers/`)

**Purpose**: Match models to hardware based on latency estimation and constraints

**Structure:**
```
matchers/
└── core.py                 # Matching algorithm implementation
```

**Key Functions:**
- `_scenario_flops()` - Calculate FLOPs based on scenario
- `_choose_dtype()` - Select appropriate precision
- `_memory_profile()` - Check memory feasibility
- `_latency_overhead()` - Compute latency overhead

#### 4.2.3 Metadata Extractor (`src/metadata_extractor/`)

**Purpose**: LLM-powered extraction of model specs from natural language

**Structure:**
```
metadata_extractor/
├── service.py              # Main extraction service
├── schemas.py              # Pydantic models for requests/responses
├── prompts/                # LLM prompt templates
├── routers/                # API routers
└── services/               # Supporting services (crawler, storage)
```

#### 4.2.4 API Layer (`src/api/`)

**Purpose**: Expose functionality via REST endpoints

**Structure:**
```
api/
├── main.py                 # FastAPI application factory
└── v1/
    ├── endpoints/          # API route handlers
    │   ├── models.py      # Model analysis routes
    │   ├── hardware.py    # Hardware analysis routes
    │   ├── metadata.py    # Metadata extraction routes
    │   └── matcher.py     # Matching routes
    └── schemas/            # Request/response models
```

**Design Pattern**: Router pattern with versioned API (`v1/`)

#### 4.2.5 CLI Layer (`src/cli/`)

**Purpose**: Command-line interface for batch processing

**Structure:**
```
cli/
├── model_cli.py           # analyze-model command
└── hardware_cli.py        # analyze-hardware command
```

**Entry Points** (defined in `pyproject.toml`):
- `analyze-model` → `cli.model_cli:cli_entry`
- `analyze-hardware` → `cli.hardware_cli:cli_entry`

#### 4.2.6 Configuration (`src/config/`)

**Purpose**: Centralized configuration and constants

**Structure:**
```
config/
├── settings.py            # Pydantic Settings (environment config)
└── constants.py           # Application constants (scenarios, dtypes)
```

**Pattern**: Settings singleton with environment variable support

#### 4.2.7 Utilities (`src/utils/`)

**Purpose**: Shared helper functions

**Structure:**
```
utils/
├── logging.py             # Logging configuration
├── validators.py          # Input validation helpers
└── converters.py          # Data type conversions
```

### 4.3 Frontend Architecture

#### 4.3.1 Component Organization

**Pages** (`src/pages/`):
- `Index.tsx` - Landing page
- `Chatbot.tsx` - Main interaction interface
- `HardwareFilter.tsx` - Hardware filtering
- `NotFound.tsx` - 404 error page

**Components** (`src/components/`):
- Reusable UI components built with shadcn/ui
- Follows atomic design principles where applicable

**Hooks** (`src/hooks/`):
- Custom React hooks for shared logic

**Library** (`src/lib/`):
- Utility functions and helpers

#### 4.3.2 Type Safety

- **TypeScript**: Strict type checking enabled
- **Zod**: Runtime schema validation
- **React Hook Form + Zod**: Type-safe form validation

### 4.4 Code Quality Practices

#### 4.4.1 Type Safety

**Backend:**
- Type hints throughout Python code
- Pydantic models for data validation
- `from __future__ import annotations` for forward references

**Frontend:**
- TypeScript strict mode
- Interface definitions for props
- Type-safe API client integration

#### 4.4.2 Error Handling

**Backend:**
- Custom exception classes
- FastAPI HTTP exception handling
- Structured error responses

**Frontend:**
- React Error Boundaries (where applicable)
- TanStack Query error handling
- Toast notifications for user feedback

#### 4.4.3 Configuration Management

**Environment-based Configuration:**
- Development vs Production settings
- Environment variable validation (Pydantic)
- Sensible defaults for optional settings

#### 4.4.4 Separation of Concerns

**Clear Layer Separation:**
1. **Domain Layer**: Analyzers, Matchers (business logic)
2. **Application Layer**: Services, Orchestrators
3. **Presentation Layer**: API, CLI, Frontend
4. **Infrastructure Layer**: Configuration, Utilities

#### 4.4.5 Documentation

**Code Documentation:**
- Module-level docstrings
- Function docstrings with Args/Returns
- Type annotations serve as inline documentation

**External Documentation:**
- README.md with setup instructions
- deployment/README.md for deployment
- This technical documentation
- API documentation (auto-generated by FastAPI at `/docs`)

### 4.5 Code Style & Linting

**Python:**
- Follows PEP 8 style guide (implied by structure)
- Import organization: `from __future__`, stdlib, third-party, local

**TypeScript:**
- ESLint configuration (`eslint.config.js`)
- React-specific linting rules
- Prettier-compatible formatting (via Vite/Bun ecosystem)

### 4.6 Dependency Management

**Backend:**
- `pyproject.toml` - Package metadata
- `requirements.txt` - Runtime dependencies
- Editable install for development (`pip install -e .`)

**Frontend:**
- `package.json` - Dependencies and scripts
- `bun.lockb` - Locked dependency versions
- Separate dev and production dependencies

### 4.7 Testing Structure

**Current State:**
- ✅ Project structure supports testing
- ❌ No test suite currently implemented
- ✅ `pytest` included in dev dependencies (`pyproject.toml`)

**Recommended Test Structure:**
```
tests/
├── unit/
│   ├── test_analyzers/
│   ├── test_matchers/
│   └── test_utils/
├── integration/
│   ├── test_api/
│   └── test_cli/
└── fixtures/
    ├── models/
    └── hardware/
```

---

## 5. Deployment Architecture

### 5.1 Backend Deployment (Google Cloud Run)

**Platform**: Serverless container platform
**Configuration** (from `deployment/backend/deploy_gcloud.sh`):
- Memory: 2Gi
- CPU: 1
- Min instances: 0 (scale to zero)
- Max instances: 10
- Timeout: 300s
- Region: us-central1

**Deployment Process:**
1. Build Docker image
2. Push to Google Container Registry
3. Deploy to Cloud Run
4. Configure environment variables
5. Expose public URL

### 5.2 Frontend Deployment (Firebase Hosting)

**Platform**: Static site hosting
**Configuration** (`firebase.json`):
- Single-page application routing
- Build output from Vite

**Deployment Process:**
1. Build production bundle (`bun run build`)
2. Deploy to Firebase Hosting
3. Configure backend API URL

### 5.3 Automated Deployment

**Script**: `deployment/deploy_all.sh`
- Deploys both backend and frontend
- Captures backend URL automatically
- Configures frontend with correct API endpoint
- Stores configuration in `.env` for future deployments

---

## 6. Data Files

### 6.1 Hardware Device Specifications

**Location**: `device_data/`

**Format**: JSON files with normalized hardware specifications

**Device Coverage** (13 devices):
- NVIDIA GPUs: H100 SXM, A100 PCIe, L4, RTX 5090, RTX 5080
- NVIDIA Jetson: AGX Orin, AGX Orin Nano, AGX Orin NX
- AMD GPUs: MI300X, RX 9090 XT, RX 9070 XT
- Google TPUs: TPU v5e
- Intel: Gaudi3

**Schema Elements:**
- Compute performance (FLOPS for multiple precisions)
- Memory capacity and bandwidth
- Power consumption
- Pricing information
- Latency characteristics

### 6.2 Example Model Configurations

**Files**:
- `model_config.json` - Complex model example
- `model_config1.json` - Alternative configuration
- `device_spec.json` - Hardware specification example

---

## Summary

This project demonstrates:

✅ **Functional API**: Dockerized FastAPI application with comprehensive endpoints
✅ **User Interface**: Modern React application with TypeScript and component library
✅ **Reproducibility**: Environment files, dependency management, Docker containerization
✅ **Clean Code**: Modular architecture, type safety, clear separation of concerns

**Areas for Enhancement:**
- Implement comprehensive test suite
- Pin exact dependency versions for full reproducibility
- Add CI/CD pipeline
- Implement code coverage tracking
- Add automated code quality checks (linting, formatting)
