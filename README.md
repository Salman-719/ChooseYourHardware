# ChooseYourHardware

Production-grade ML model and hardware analysis framework for resource requirement estimation and hardware selection.

## Features

- **Model Analysis**: Compute resource requirements for ML models
  - Classical ML: KNN, K-Means, Decision Trees, Ensembles
  - Neural Networks: CNNs, Transformers, LLMs
  - Calculate FLOPs, memory, and activation requirements
  
- **Hardware Analysis**: Normalize and analyze hardware specifications
  - Support for CPUs, GPUs, TPUs, accelerators, clusters
  - Compute throughput metrics (FLOPS, bandwidth)
  - Multi-precision support (FP32, FP16, BF16, INT8)

- **RESTful API**: FastAPI-based REST API for service integration
- **CLI Tools**: Command-line interfaces for analysis tasks
- **Type Safety**: Full Pydantic validation and type hints

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

# Or install with development dependencies
pip install -e ".[dev]"
```

### Using Make

```bash
make install      # Install base package
make dev          # Install with dev dependencies
```

## Usage

### Command Line Interface

#### Analyze Model

```bash
# From file
analyze-model examples/model_analyzer_input.json

# From stdin
cat examples/model_analyzer_input.json | analyze-model
```

#### Analyze Hardware

```bash
# Basic usage
analyze-hardware examples/hardware_spec.json

# With output file
analyze-hardware examples/hardware_spec.json -o results.json
```

### Python API

```python
from choose_your_hardware import analyze_model, analyze_hardware_spec
import json

# Analyze model
with open('examples/model_analyzer_input.json') as f:
    model_json = f.read()
result = analyze_model(model_json)
print(json.loads(result))

# Analyze hardware
with open('examples/hardware_spec.json') as f:
    hardware_spec = json.load(f)
result = analyze_hardware_spec(hardware_spec)
print(result)
```

### REST API

Start the API server:

```bash
# Using Python
python -m choose_your_hardware.api.main

# Or using uvicorn directly
uvicorn choose_your_hardware.api.main:app --reload
```

The API will be available at `http://localhost:8000`

#### API Endpoints

- `GET /health` - Health check
- `POST /api/v1/models/analyze` - Analyze ML model
- `POST /api/v1/hardware/analyze` - Analyze hardware spec

API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### Example API Request

```bash
curl -X POST "http://localhost:8000/api/v1/models/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "model_json": "{\"model_type\": \"neural_network\", \"dtype_bits\": 32, \"inference_config\": {\"batch_size\": 8}}"
  }'
```

## Project Structure

```
ChooseYourHardware/
├── src/choose_your_hardware/      # Main package
│   ├── analyzers/                 # Analysis engines
│   │   ├── model/                 # Model analyzers
│   │   │   ├── classical/         # KNN, K-Means, Trees
│   │   │   └── neural/            # CNNs, Transformers, LLMs
│   │   └── hardware/              # Hardware analyzers
│   ├── api/                       # FastAPI application
│   │   ├── main.py                # API entry point
│   │   └── v1/endpoints/          # API endpoints
│   ├── cli/                       # Command-line interfaces
│   ├── config/                    # Configuration management
│   ├── exceptions/                # Custom exceptions
│   └── utils/                     # Utilities
├── examples/                      # Example configurations
├── pyproject.toml                 # Package configuration
├── Makefile                       # Common commands
└── README.md                      # This file
```

## Development

### Setup Development Environment

```bash
make dev          # Install dev dependencies
make format       # Format code with black
make lint         # Run linters
make test         # Run tests
```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=choose_your_hardware
```

## Configuration

Configuration can be provided via environment variables or `.env` file:

```bash
# API Configuration
ENV=development
API_PORT=8000

# OpenAI (for metadata extractor)
OPENAI_API_KEY=your-key-here
OPENAI_LLM_MODEL=gpt-4o-mini

# Logging
LOG_LEVEL=INFO
```

## Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guidelines and contribution workflow
- **API Documentation** - Available at `/docs` when running the API server

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Development setup
- Code standards and style
- Testing requirements
- Pull request process

## License

MIT License (or specify your license)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes and releases.
