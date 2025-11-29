# ChooseYourHardware

**AI-powered hardware selection assistant for ML model deployment** - Analyze model requirements, evaluate hardware capabilities, and find the optimal device for your ML workload.

## 🎯 Overview

ChooseYourHardware is a system that helps ML engineers and researchers select the fitting hardware for deploying machine learning models. It combines analytical modeling of ML workloads with intelligent hardware matching to provide latency estimates, bottleneck analysis, and cost-effective recommendations.

**Status**: v1.0.0 - Research prototype with cloud deployment capabilities. Latency estimates are analytical predictions based on theoretical models and have not been validated against real hardware measurements.

**Live Demo:**
- Frontend: https://easyware.web.app
- Backend API: https://chooseyourhardware-rhen2vww6a-uc.a.run.app
- API Documentation: https://chooseyourhardware-rhen2vww6a-uc.a.run.app/docs

**⚠️ Important Note**: This is an academic research project. Latency predictions are theoretical and should be validated against actual hardware before making production decisions.

### Key Capabilities

- **Model Analysis**: Calculate FLOPs, memory requirements, and activation sizes for ML models
  - Classical ML: KNN, K-Means, Decision Trees, Random Forest, Gradient Boosted Trees
  - Neural Networks: Layer-by-layer analysis for general neural architectures
  - Transformers & LLMs: Support for transformer models with attention mechanisms
  - Multi-precision support: FP32, FP16, BF16, INT8

- **Hardware Analysis**: Normalize and evaluate device specifications
  - Device types: CPUs, GPUs, TPUs, accelerators, Jetson
  - Performance metrics: FLOPS, memory bandwidth, latency characteristics
  - Specification normalization from various device spec formats

- **Intelligent Matching**: Analytical latency estimation
  - Bottleneck detection: Compute-bound vs memory-bound analysis
  - Dtype feasibility: Precision selection based on hardware support
  - Constraint filtering: Budget, power consumption, compatibility checks

- **LLM-Powered Features**:
  - **Metadata Extractor**: Conversational interface to extract model specs from free-form descriptions
  - **Hardware Crawler**: Automated extraction of device specs from HTML catalogs

- **Multiple Interfaces**:
  - **Web UI**: chatbot interface for interactive model analysis
  - **REST API**: FastAPI-based service for programmatic integration
  - **CLI Tools**: Command-line interfaces for batch processing

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Frontend (React + TypeScript)                  │
│           Interactive UI • Constraint Input • Results            │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS/REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Cloud Run)                    │
├─────────────────────────────────────────────────────────────────┤
│  Model Analyzers         Hardware Analyzers      Matcher         │
│  ├─ Classical ML         ├─ Normalization       ├─ Latency      │
│  ├─ Neural Networks      ├─ FLOPS Calculation   ├─ Bottleneck   │
│  └─ Transformers         └─ Memory Analysis     └─ Filtering    │
│                                                                   │
│  Metadata Extractor (Optional - requires OpenAI API key)         │
│  ├─ LLM Conversation        Hardware Crawler                     │
│  ├─ Field Templates         ├─ HTML Parsing                     │
│  └─ Validation              └─ LLM Extraction                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ (Optional)
                             ▼
                    ┌────────────────┐
                    │  OpenAI GPT    │
                    │  (gpt-4o-mini) │
                    └────────────────┘
```

### Component Overview

1. **Analyzers** (`src/analyzers/`)
   - **Model Analyzers**: Compute FLOPs, parameters, activations, and memory requirements
     - Classical: Analytical models for KNN, K-Means, decision trees, ensembles
     - Neural: Layer-wise analysis for neural network architectures
     - Transformers: Attention mechanism and feed-forward computation analysis
   - **Hardware Analyzers**: Normalize device specs, infer missing fields, validate constraints

2. **Matchers** (`src/matchers/`)
   - Estimate inference latency based on analytical models
   - Identify bottlenecks: compute-bound vs memory-bandwidth-bound
   - Filter devices by constraints (cost, power, compatibility)

3. **Metadata Extractor** (`src/metadata_extractor/`) *(Requires OpenAI API Key)*
   - LLM-powered conversational interface for model specification extraction
   - Two-step prompt flow: state update + follow-up questions
   - Template-based validation for classical models

4. **API Endpoints** (`src/api/v1/endpoints/`)
   - `/models/analyze` - Analyze ML model requirements
   - `/hardware/analyze` - Normalize hardware specifications  
   - `/metadata/extract` - Interactive metadata extraction (requires OpenAI)
   - `/matcher/best` - Find optimal device for a model
   - `/hardware/` - List available hardware devices

5. **Frontend** (`Frontend/northlane-partner-hub/`)
   - React + TypeScript + Vite
   - Tailwind CSS + shadcn/ui components
   - Interactive interface for model specification and hardware recommendations

6. **CLI Tools** (`src/cli/`)
   - `analyze-model` - Command-line model analysis
   - `analyze-hardware` - Command-line hardware analysis

## 🚀 Quick Start

### Option 1: Use the Live Web Interface

Visit **https://easyware.web.app** to use the interactive web interface for model analysis and hardware selection.

### Option 2: Use the Public API

**API Base URL**: https://chooseyourhardware-rhen2vww6a-uc.a.run.app

```bash
# Analyze a transformer model
curl -X POST https://chooseyourhardware-rhen2vww6a-uc.a.run.app/api/v1/models/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "model_json": "{\"model_type\": \"transformer\", \"num_layers\": 12, \"d_model\": 768, \"num_heads\": 12, \"d_ff\": 3072, \"sequence_length\": 512, \"inference_config\": {\"batch_size\": 1}}"
  }'

# Find best hardware match for a model
curl -X POST https://chooseyourhardware-rhen2vww6a-uc.a.run.app/api/v1/matcher/best \
  -H "Content-Type: application/json" \
  -d '{
    "model": {"model_type": "transformer", "num_layers\": 12, \"d_model\": 768, \"num_heads\": 12, \"d_ff\": 3072, \"sequence_length\": 512, \"inference_config\": {\"batch_size\": 1}},
    "device_dir": "device_data"
  }'

# List available hardware devices
curl https://chooseyourhardware-rhen2vww6a-uc.a.run.app/api/v1/hardware/

# View API documentation
# Visit: https://chooseyourhardware-rhen2vww6a-uc.a.run.app/docs
```

### Option 3: Run Locally

## Installation

### From Source

```bash
### Option 3: Run Locally

See the [Installation](#installation) section below for setup instructions.

## Installation

### Prerequisites

- Python 3.9 or higher
- Git
- (Optional) OpenAI API key for metadata extraction features

### From Source

```bash
# Clone the repository
git clone https://github.com/Salman-719/ChooseYourHardware.git
cd ChooseYourHardware

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in editable mode
pip install -e .
```

### Configuration

Create a `.env` file in the project root (optional, only needed for LLM features):

```bash
# Optional - Required only for metadata extractor and hardware crawler
OPENAI_API_KEY=sk-your-key-here
OPENAI_LLM_MODEL=gpt-4o-mini

# API Configuration (optional, has defaults)
ENV=development
LOG_LEVEL=INFO
```

**Note**: The core model and hardware analyzers work without an OpenAI API key. The metadata extractor and hardware crawler features require it.

## Usage

### Command Line Interface

The package provides two CLI commands installed via `pip install -e .`:

```bash
# Analyze a model from JSON file
analyze-model model_config.json

# Analyze hardware specification from JSON file
analyze-hardware device_spec.json

# Or pipe JSON via stdin
echo '{"model_type": "knn", ...}' | analyze-model
```

**Example Model Configurations:**
- See `model_config.json` and `model_config1.json` in the project root for examples
- Hardware device specs are in `device_data/` directory

### REST API (Local Development)

Start the API server locally:

```bash
# Using uvicorn directly (recommended for development)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python module
python -m src.api.main
```

The API will be available at `http://localhost:8000`

**Interactive API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Core API Endpoints:**
- `GET /health` - Health check
- `POST /api/v1/models/analyze` - Analyze ML model requirements
- `POST /api/v1/hardware/analyze` - Analyze hardware specifications
- `POST /api/v1/matcher/best` - Find best hardware for a model
- `GET /api/v1/hardware/` - List available hardware devices
- `POST /api/v1/metadata/extract` - Interactive metadata extraction (requires OpenAI)
- `POST /api/v1/hardware/crawl` - Trigger hardware catalog crawl (requires OpenAI)

## 📁 Project Structure

```
ChooseYourHardware/
├── src/                        # Source code
│   ├── analyzers/              # Analysis engines
│   │   ├── model/              # Model analyzers
│   │   │   ├── classical/      # KNN, K-Means, Trees
│   │   │   │   ├── kmeans.py
│   │   │   │   ├── knn.py
│   │   │   │   └── trees.py
│   │   │   └── neural/         # Neural networks, Transformers
│   │   │       ├── layers.py
│   │   │       ├── transformers.py
│   │   │       └── llm.py
│   │   └── hardware/           # Hardware analyzers
│   │       ├── core.py
│   │       └── utils.py
│   ├── matchers/               # Latency estimation & matching
│   │   └── core.py
│   ├── metadata_extractor/     # LLM-powered extraction
│   │   ├── service.py
│   │   ├── schemas.py
│   │   ├── prompts/
│   │   ├── routers/
│   │   └── services/
│   ├── api/                    # FastAPI application
│   │   ├── main.py
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── schemas/
│   ├── cli/                    # Command-line tools
│   │   ├── model_cli.py
│   │   └── hardware_cli.py
│   ├── config/                 # Configuration
│   │   ├── settings.py
│   │   └── constants.py
│   └── utils/                  # Utility functions
│       ├── logging.py
│       ├── validators.py
│       └── converters.py
├── Frontend/                   # Web interface
│   └── northlane-partner-hub/  # React + TypeScript app
│       ├── src/
│       │   ├── pages/
│       │   └── components/
│       └── public/
├── deployment/                 # Cloud deployment scripts
│   ├── deploy_all.sh           # Deploy backend + frontend
│   ├── backend/
│   │   └── deploy_gcloud.sh    # Cloud Run deployment
│   └── frontend/
│       └── deploy_firebase.sh  # Firebase Hosting
├── device_data/                # Hardware specifications (JSON)
│   ├── nvidia_h100_sxm_80gb.json
│   ├── amd_mi300x.json
│   └── ... (13 device profiles)
├── Dockerfile                  # Production container
├── pyproject.toml              # Package metadata
├── requirements.txt            # Python dependencies
├── model_config.json           # Example model configuration
└── README.md                   # This file
```


## 🚢 Cloud Deployment

This project is deployed on Google Cloud Platform using:
- **Backend**: Google Cloud Run (containerized FastAPI application)
- **Frontend**: Firebase Hosting (static React application)

### Automated Deployment

Deploy both backend and frontend in one command:

```bash
cd deployment
./deploy_all.sh
```

This script will:
1. Prompt for your GCP Project ID (if not in `.env`)
2. Prompt for your OpenAI API Key (if not in `.env`)
3. Deploy backend to Cloud Run
4. Capture the backend URL automatically
5. Deploy frontend to Firebase with correct backend URL
6. Save configuration to `.env` for future deployments

See [deployment/README.md](deployment/README.md) for detailed deployment instructions.

### Manual Deployment

**Backend to Cloud Run:**
```bash
cd deployment/backend
./deploy_gcloud.sh
```

**Frontend to Firebase:**
```bash
cd deployment/frontend
./deploy_firebase.sh
```

### Docker

The application can be containerized and run locally:

```bash
# Build Docker image
docker build -t chooseyourhardware .

# Run container
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your-key-here \
  -e PORT=8080 \
  chooseyourhardware

# Access at http://localhost:8080
```

The Dockerfile uses Python 3.11-slim and includes health checks for production readiness.

## 🧪 Technical Details

### Model Analysis Methodology

**Classical ML:**
- **KNN**: Distance computations (`O(n × d × k)`) + sorting operations
- **K-Means**: Centroid distance calculations + assignment iterations  
- **Decision Trees**: Tree traversal cost + feature comparison operations
- **Ensembles**: Per-tree cost × number of trees (Random Forest, Gradient Boosted Trees)

**Neural Networks:**
- Layer-wise analysis: Parameters, FLOPs, and activations per layer
- Memory tracking: Peak activation memory, parameter memory
- Arithmetic intensity: FLOPs / memory bytes accessed

**Transformers:**
- **Attention**: `O(seq_len² × d_model)` complexity for self-attention
- **Feed-forward**: `O(seq_len × d_model × d_ff)` for linear layers
- Multi-head attention computation accounting
- Layer normalization overhead

### Hardware Analysis Features

- **Normalization**: Convert various device specification formats to unified schema
- **Inference**: Derive missing fields from available specifications
- **Multi-precision Support**: Track FP32, FP16, BF16, INT8 capabilities
- **Memory Modeling**: Separate VRAM (GPU) vs RAM (CPU/shared) modeling
- **Latency Characteristics**: DRAM latency and cache latency parameters

### Matching Strategy

The matching algorithm follows these steps:

1. **Dtype Selection**: Choose precision based on model requirements and hardware support
2. **Memory Feasibility**: Verify working set (parameters + activations) fits in device memory
3. **Bottleneck Identification**:
   - **Compute-bound**: Latency ≈ FLOPs / compute_throughput
   - **Memory-bound**: Latency ≈ memory_bytes / memory_bandwidth
4. **Constraint Filtering**: Eliminate devices exceeding budget, power, or compatibility requirements
5. **Ranking**: Select device with lowest estimated latency among feasible options

**⚠️ Important**: Latency estimates are analytical predictions based on roofline models and theoretical analysis. They have **not been validated** against real hardware measurements. For production use, validate predictions against actual hardware performance.

##  Hardware Catalog

The system includes **13 hardware device profiles** covering modern AI accelerators:

- **NVIDIA GPUs**: H100 SXM 80GB, A100 PCIe 40GB, L4, RTX 5090, RTX 5080  
- **NVIDIA Jetson SoCs**: AGX Orin, AGX Orin Nano, AGX Orin NX  
- **AMD GPUs**: MI300X, Radeon RX 9090 XT, RX 9070 XT  
- **Google TPUs**: TPU v5e  
- **Intel Accelerators**: Gaudi3  

Device specifications are stored as JSON files in `device_data/` and include:
- Compute performance (FLOPS for FP32, FP16, BF16, INT8)
- Memory capacity and bandwidth
- Power consumption
- Pricing information (where available)
- Latency characteristics (DRAM, cache)

## 📚 Documentation

- **[deployment/README.md](deployment/README.md)** - Complete deployment guide for Cloud Run and Firebase
- **API Documentation** - Interactive Swagger UI at `/docs` endpoint
- **Example Configurations** - See `model_config.json` for model specification examples

## 🎓 Academic Context

This project was developed as part of **EECE 490** at the American University of Beirut (AUB).

**Project Objectives:**
- Analytical modeling of ML workload characteristics
- Hardware selection algorithms for edge and cloud deployment
- Cloud infrastructure deployment (Google Cloud Run + Firebase)
- Integration of LLMs for metadata extraction

**Key Learning Outcomes:**
- FastAPI backend development and REST API design
- React frontend with TypeScript and modern UI libraries
- Docker containerization and cloud deployment
- Analytical performance modeling and roofline analysis
- LLM integration for structured data extraction

**Limitations & Future Work:**
- Latency predictions are theoretical and require validation against real hardware
- Limited hardware catalog (13 devices, can be expanded)
- No automated testing or CI/CD pipeline
- Metadata extraction accuracy not quantitatively evaluated

## 🔮 Future Enhancements

### High Priority

**1. Validation & Testing** ⚠️
- Compare predicted vs actual latency on real hardware
- Implement comprehensive test suite (unit, integration, end-to-end)
- Add CI/CD pipeline with automated testing
- Track test coverage with pytest-cov

**2. Dependency Management**
- Pin exact versions in `requirements.txt` (currently uses `>=` ranges)
- Regular security audits
- Consider Poetry for better dependency resolution

### Feature Enhancements

**3. Model Support**
- Additional architectures: RNNs, GANs, diffusion models
- Direct framework integration (PyTorch, TensorFlow model loading)
- Advanced quantization: 4-bit, 2-bit schemes
- Sparsity accounting in FLOPs calculations

**4. Hardware Catalog Expansion**
- Cloud instances: AWS EC2, Azure VMs, GCP Compute Engine
- More edge devices: Qualcomm, MediaTek accelerators
- Server CPUs: Intel Xeon, AMD EPYC
- Real-time pricing from cloud provider APIs

**5. Advanced Matching**
- Multi-objective optimization (Pareto front analysis)
- Workload profiling with throughput requirements
- Dynamic/spot instance pricing consideration
- Environmental impact (CO2 emissions) calculations

**6. Production Readiness**
- Result caching (Redis)
- API authentication and rate limiting
- Monitoring: Prometheus metrics, Grafana dashboards
- Error tracking with Sentry
- Structured logging and distributed tracing

**7. User Experience**
- Interactive performance/cost comparison charts
- Batch model analysis
- Report export (PDF, CSV)
- Model repository for saving configurations

## 🔗 Links

- **GitHub Repository**: https://github.com/Salman-719/ChooseYourHardware
- **Live Frontend**: https://easyware.web.app
- **Live API**: https://chooseyourhardware-rhen2vww6a-uc.a.run.app
- **API Documentation**: https://chooseyourhardware-rhen2vww6a-uc.a.run.app/docs

## 📄 License

MIT License

---

**⚠️ Disclaimer**: This is an academic research project developed for EECE 490 at AUB. Latency predictions are analytical estimates and have not been validated against real hardware. Always validate recommendations with actual performance testing before production deployment.
