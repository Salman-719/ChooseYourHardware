# ChooseYourHardware

**AI-powered hardware selection assistant for ML model deployment** - Analyze model requirements, evaluate hardware capabilities, and find the optimal device for your ML workload.

## 🎯 Overview

ChooseYourHardware is a functional prototype system that helps ML engineers and researchers select the best hardware for deploying machine learning models. It combines analytical modeling of ML workloads with intelligent hardware matching to provide latency estimates, bottleneck analysis, and cost-effective recommendations.

**Status**: v1.0.0 - MVP deployed and functional, validation against real hardware measurements pending.

**Live Demo:**
- Frontend: https://easyware.web.app
- Backend API: https://chooseyourhardware-rhen2vww6a-uc.a.run.app
- API Documentation: https://chooseyourhardware-rhen2vww6a-uc.a.run.app/docs

### Key Capabilities

- **Model Analysis**: Calculate FLOPs, memory requirements, and activation sizes for ML models
  - Classical ML: KNN, K-Means, Decision Trees, Random Forest, Gradient Boosted Trees
  - Neural Networks: CNNs, Transformers, LLMs (with KV cache and per-token decode analysis)
  - Multi-precision support: FP32, FP16, BF16, INT8

- **Hardware Analysis**: Normalize and evaluate device specifications
  - Device types: CPUs, GPUs, TPUs, accelerators, Jetson SoCs, clusters
  - Performance metrics: FLOPS, memory bandwidth, latency characteristics
  - Constraint validation: Power limits, cost budgets, edge device requirements

- **Intelligent Matching**: Scenario-aware latency estimation
  - Bottleneck detection: Compute-bound vs memory-bound vs latency-bound
  - Dtype feasibility: Automatic precision selection based on hardware support
  - Constraint filtering: Budget, power consumption, XLA compatibility

- **LLM-Powered Features**:
  - **Metadata Extractor**: Conversational interface to extract model specs from free-form descriptions
  - **Hardware Crawler**: Automated extraction of device specs from HTML catalogs

- **Multiple Interfaces**:
  - **Web UI**: Conversational chatbot for non-technical users
  - **REST API**: FastAPI-based service for integration
  - **CLI Tools**: Command-line interfaces for scripting and automation

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  Conversational UI • Hardware Constraints • Results Display     │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Cloud Run)                    │
├─────────────────────────────────────────────────────────────────┤
│  Model Analyzer          Hardware Analyzer        Matcher        │
│  ├─ Classical ML         ├─ Normalization        ├─ Latency     │
│  ├─ Neural Networks      ├─ FLOPS Calculation    ├─ Bottleneck  │
│  └─ LLMs (KV cache)      └─ Memory Analysis      └─ Filtering   │
│                                                                   │
│  Metadata Extractor              Hardware Crawler                │
│  ├─ LLM Conversation            ├─ HTML Parsing                 │
│  ├─ Field Templates             ├─ LLM Extraction               │
│  └─ Validation                  └─ SQLite Storage               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  OpenAI GPT    │
                    │  (gpt-4o-mini) │
                    └────────────────┘
```

### Component Overview

1. **Analyzers** (`src/analyzers/`)
   - **Model Analyzers**: Compute FLOPs, parameters, activations, and memory requirements
     - Classical: Deterministic templates for KNN, K-Means, decision trees
     - Neural: Layer-wise analysis for CNNs, Transformers, LLMs
   - **Hardware Analyzers**: Normalize device specs, infer missing fields, validate constraints

2. **Matchers** (`src/matchers/`)
   - Estimate inference latency based on scenario (single-pass, batch, decode)
   - Identify bottlenecks: compute, memory bandwidth, or memory latency
   - Filter devices by hard constraints (cost, power, XLA support)

3. **Metadata Extractor** (`src/metadata_extractor/`)
   - LLM-powered conversational interface for model specification
   - Two-step prompt flow: update state + ask follow-up questions
   - Template-based validation for classical models (avoids unnecessary LLM calls)

4. **Hardware Crawler** (`src/metadata_extractor/services/`)
   - Automated extraction of device specs from HTML catalogs
   - LLM-based parsing with JSON repair and validation
   - SQLite storage for hardware catalog

5. **API Endpoints** (`src/api/v1/endpoints/`)
   - `/models/analyze` - Analyze ML model requirements
   - `/hardware/analyze` - Normalize hardware specifications  
   - `/metadata/extract` - Interactive metadata extraction
   - `/matcher/best` - Find optimal device for a model

6. **Frontend** (`Frontend/northlane-partner-hub/`)
   - React + TypeScript + Vite
   - Tailwind CSS + shadcn/ui components
   - Conversational chatbot interface
   - Constraint collection (budget, power, edge device)
   - Real-time latency estimates and device recommendations

## 🚀 Quick Start

### Option 1: Use the Web Interface

Visit **https://easyware.web.app** and chat with the assistant about your model and constraints.

### Option 2: API (For Developers)

**Live API**: https://chooseyourhardware-rhen2vww6a-uc.a.run.app

```bash
# Analyze a transformer model
curl -X POST https://chooseyourhardware-rhen2vww6a-uc.a.run.app/api/v1/models/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "model_json": "{\"model_type\": \"transformer\", \"num_layers\": 12, \"d_model\": 768, \"num_heads\": 12, \"d_ff\": 3072, \"sequence_length\": 512, \"inference_config\": {\"batch_size\": 1}}"
  }'

# Find best hardware match
curl -X POST https://chooseyourhardware-rhen2vww6a-uc.a.run.app/api/v1/matcher/best \
  -H "Content-Type: application/json" \
  -d '{
    "model": {"model_type": "transformer", "num_layers": 12, "d_model": 768, "num_heads": 12, "d_ff": 3072, "sequence_length": 512, "inference_config": {"batch_size": 1}},
    "device_dir": "device_data"
  }'

# List available hardware devices
curl https://chooseyourhardware-rhen2vww6a-uc.a.run.app/api/v1/hardware/
```

### Option 3: Run Locally

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/Salman-719/ChooseYourHardware.git
cd ChooseYourHardware

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .


### Configuration

Create a `.env` file in the project root:

```bash
# Required for metadata extractor and hardware crawler
OPENAI_API_KEY=sk-your-key-here
OPENAI_LLM_MODEL=gpt-4o-mini

# API Configuration (optional)
ENV=development
API_PORT=8000
LOG_LEVEL=INFO
```

**Note**: The metadata extractor and hardware crawler require an OpenAI API key. Model and hardware analyzers work without it.

## Usage

### Command Line Interface

```bash
# Analyze model from JSON file
analyze-model model_config.json

# Analyze hardware specification
analyze-hardware device_spec.json
```


### REST API

Start the API server:

```bash
# Using Python module
python -m api.main

# Or using uvicorn directly
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

#### API Endpoints

- `GET /health` - Health check
- `GET /docs` - Interactive API documentation (Swagger UI)
- `POST /api/v1/models/analyze` - Analyze ML model requirements
- `POST /api/v1/hardware/analyze` - Analyze hardware specification
- `POST /api/v1/metadata/extract` - Interactive metadata extraction
- `POST /api/v1/matcher/best` - Find best hardware match
- `GET /api/v1/hardware/` - List available hardware devices
- `POST /api/v1/hardware/crawl` - Trigger hardware catalog crawl

See full API documentation at: `http://localhost:8000/docs`

## 📁 Project Structure

```
ChooseYourHardware/
├── src/
│   ├── analyzers/              # Analysis engines
│   │   ├── model/              # Model analyzers
│   │   │   ├── classical/      # KNN, K-Means, Trees
│   │   │   │   ├── kmeans.py
│   │   │   │   ├── knn.py
│   │   │   │   └── trees.py
│   │   │   └── neural/         # CNNs, Transformers, LLMs
│   │   │       ├── layers.py
│   │   │       ├── transformers.py
│   │   │       └── llm.py
│   │   └── hardware/           # Hardware analyzers
│   │       ├── core.py         # Normalization & validation
│   │       └── utils.py        # FLOPS calculation, inference
│   ├── matchers/               # Latency estimation
│   │   └── core.py             # Bottleneck analysis, filtering
│   ├── metadata_extractor/     # LLM-powered extraction
│   │   ├── service.py          # Main extractor service
│   │   ├── schemas.py          # Request/response models
│   │   ├── prompts/            # LLM prompt templates
│   │   └── services/           # Hardware crawler, storage
│   ├── api/                    # FastAPI application
│   │   ├── main.py             # API entry point
│   │   └── v1/endpoints/       # API endpoints
│   │       ├── models.py
│   │       ├── hardware.py
│   │       ├── metadata.py
│   │       └── matcher.py
│   ├── cli/                    # Command-line interfaces
│   │   ├── model_cli.py
│   │   └── hardware_cli.py
│   ├── config/                 # Configuration
│   │   ├── settings.py         # Pydantic settings
│   │   └── constants.py        # Scenario kinds, dtype mappings
│   └── utils/                  # Utilities
│       ├── logging.py
│       ├── validators.py
│       └── converters.py
├── Frontend/                   # Web interface
│   └── northlane-partner-hub/  # React + Vite application
│       ├── src/
│       │   ├── pages/          # Chatbot, landing page
│       │   └── components/     # UI components (shadcn)
│       └── public/
├── deployment/                 # Deployment automation
│   ├── deploy_all.sh           # Deploy backend + frontend
│   ├── backend/                # Cloud Run deployment
│   │   └── deploy_gcloud.sh
│   └── frontend/               # Firebase Hosting deployment
│       └── deploy_firebase.sh
├── device_data/                # Hardware catalog (JSON)
│   ├── nvidia_h100_sxm_80gb.json
│   ├── amd_mi300x.json
│   └── ...
├── tests/                      # Test suite
├── Dockerfile                  # Production container
├── pyproject.toml              # Package configuration
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```



## 🚢 Deployment

### Production Deployment (Automated)

Deploy both backend and frontend to Google Cloud:

```bash
cd deployment
./deploy_all.sh
```

See [deployment/README.md](deployment/README.md) for detailed instructions.

### Manual Deployment

**Backend** (Google Cloud Run):
```bash
cd deployment/backend
./deploy_gcloud.sh
```

**Frontend** (Firebase Hosting):
```bash
cd deployment/frontend  
./deploy_firebase.sh
```

### Docker

```bash
# Build production image
docker build -t chooseyourhardware .

# Run locally
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your-key \
  -e PORT=8080 \
  chooseyourhardware
```

## 📚 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guidelines and contribution workflow
- **[deployment/README.md](deployment/README.md)** - Deployment guide (Cloud Run + Firebase)
- **API Documentation** - Available at `/docs` when running the API server

## 🧪 Technical Details

### Model Analysis Methodology

**Classical ML**:
- KNN: Distance computations (`O(n × d × k)`) + sorting
- K-Means: Centroid distance + assignment iterations  
- Decision Trees: Tree traversal + feature comparisons
- Ensembles: Per-tree cost × number of trees

**Neural Networks**:
- Layer-wise analysis: Parameters, FLOPs, activations per layer
- Memory tracking: Peak activation bytes, parameter memory
- Arithmetic intensity: FLOPs / memory bytes (compute vs bandwidth bound)

**Transformers/LLMs**:
- Attention: `O(seq_len² × d_model)` complexity
- Feed-forward: `O(seq_len × d_model × d_ff)`
- KV cache: Memory for cached keys/values during autoregressive generation
- Separate prefill and per-token decode costs

### Hardware Analysis Features

- **Normalization**: Convert various spec formats to unified schema
- **Inference**: Derive missing fields (e.g., FP32 FLOPS from SM count + clock)
- **Multi-precision**: Track FP32, FP16, BF16, INT8 capabilities separately
- **Memory modeling**: Separate VRAM (GPU) vs RAM (CPU/shared) bandwidth and capacity
- **Latency characteristics**: DRAM latency, cache latency for memory-bound analysis

### Matching Strategy

1. **Dtype selection**: Choose precision based on model requirements and hardware support
2. **Memory feasibility**: Check if working set (params + activations + KV cache) fits in device memory
3. **Bottleneck identification**:
   - **Compute-bound**: Latency = FLOPs / throughput
   - **Memory bandwidth-bound**: Latency = memory streamed / bandwidth
   - **Memory latency-bound**: Add overhead for cache/DRAM accesses
4. **Constraint filtering**: Eliminate devices exceeding budget, power, or incompatible with XLA
5. **Ranking**: Select device with lowest estimated latency

**Note**: Latency estimates are analytical predictions. Real-world validation against measured performance is recommended for production use.

## 📄 License

MIT License

## 🔗 Links

- **Repository**: https://github.com/Salman-719/ChooseYourHardware
- **Live Demo**: https://easyware.web.app
- **API**: https://chooseyourhardware-rhen2vww6a-uc.a.run.app
- **API Docs**: https://chooseyourhardware-rhen2vww6a-uc.a.run.app/docs

---

## 📊 Hardware Catalog

The system includes **13 device profiles** covering modern AI accelerators:

**NVIDIA GPUs**: H100 SXM 80GB, A100 PCIe 40GB, L4, RTX 5090, RTX 5080  
**NVIDIA Jetson**: AGX Orin, AGX Orin Nano, AGX Orin NX  
**AMD GPUs**: MI300X, Radeon RX 9090 XT, RX 9070 XT  
**Google TPUs**: TPU v5e  
**Intel Accelerators**: Gaudi3  

All device specs are stored as JSON in `device_data/` and include: FLOPS (FP32/FP16/BF16/INT8), memory capacity/bandwidth, power consumption, pricing, and latency characteristics.


## Future Improvements

### Recommended Enhancements

1. **Validation & Testing** ⚠️ **Critical Priority**
   - Add quantitative validation: Compare predicted vs measured latency across real devices
   - Implement automated test suite with unit tests for analyzers, matchers, and API endpoints
   - Add integration tests for end-to-end pipeline flows
   - Create test fixtures with known model-hardware pairs and expected results

2. **LLM Metadata Extraction**
   - Track extraction precision/recall metrics (what percentage of fields extracted correctly)
   - Implement error analysis: categorize extraction failures by model type
   - Add validation step: verify extracted metadata produces valid analyzer output
   - Support more model architectures (RNNs, GANs, diffusion models)

3. **Observability & Monitoring**
   - Add structured logging for production debugging
   - Implement metrics collection (request latency, error rates, cache hit rates)
   - Set up distributed tracing for multi-service requests
   - Create dashboards for system health and performance

4. **Hardware Catalog**
   - Expand device coverage (more CPUs, mobile chips, custom ASICs)
   - Add historical pricing data for cost-trend analysis
   - Implement automatic catalog updates via scheduled crawler
   - Support multi-cloud providers (AWS instances, Azure VMs, GCP machine types)

5. **User Experience**
   - Add visualization: Charts comparing devices on latency/cost/power dimensions
   - Show bottleneck breakdowns graphically (what % is compute vs memory vs latency)
   - Support batch analysis: Compare multiple models across hardware catalog
   - Add export functionality: Generate reports (PDF/CSV) with recommendations

6. **Documentation**
   - Populate examples/ directory with sample model configurations
   - Create quickstart tutorial with step-by-step example
   - Document API authentication and rate limiting (if added)
   - Add CHANGELOG.md for version tracking

7. **Performance**
   - Cache analyzer results for identical model configurations
   - Optimize hardware crawler: Parallel fetching, smart rate limiting
   - Add batch processing endpoint for multiple models
   - Implement result pagination for large device catalogs

8. **Deployment & Operations**
   - Pin dependency versions in `requirements.txt` for reproducibility (`==` instead of `>=`)
   - Add health checks with detailed component status (database, OpenAI API, cache)
   - Implement graceful degradation (work without OpenAI API if metadata extraction not needed)
   - Set up CI/CD pipeline for automated testing and deployment
   - Add staging environment for pre-production testing
   - Implement structured logging and distributed tracing

9. **Code Quality**
   - Remove debug print statements from production code
   - Add comprehensive inline documentation for complex algorithms
   - Create architecture decision records (ADRs)

---

## 🎓 Academic Context

This project was developed as part of EECE 490 at the American University of Beirut (AUB), demonstrating:
- Analytical modeling of ML workloads
- Intelligent hardware selection algorithms
- Production deployment on cloud infrastructure
- Integration of LLMs for metadata extraction

**Key Innovations**:
- Scenario-aware latency estimation (prefill/decode, batch, streaming)
- Multi-precision bottleneck analysis (compute/memory/latency-bound)
- Conversational interface for non-technical users
- Automated hardware catalog updates via LLM-powered crawling

These improvements would elevate the project from a strong MVP to a production-grade, enterprise-ready system.
