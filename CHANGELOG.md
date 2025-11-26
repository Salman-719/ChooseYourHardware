# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-26

### Major Refactoring - Production-Grade Architecture

This release represents a complete architectural refactoring to production-grade standards while preserving all original functionality.

### Added

#### Package Structure
- Modern `src/` layout following PEP 518/517
- Layered architecture: config → utils → analyzers → api → cli
- Comprehensive type hints using Python 3.9+ syntax

#### Configuration Layer
- `config/constants.py`: Centralized constants (DTYPE_BITS, HARDWARE_KINDS, conversions)
- `config/settings.py`: Pydantic-based settings with environment variable support
- `.env` file support for configuration

#### Exception Hierarchy
- `exceptions/base.py`: Custom base exception (`ChooseYourHardwareException`)
- `exceptions/model_exceptions.py`: Model-specific exceptions
- `exceptions/hardware_exceptions.py`: Hardware-specific exceptions

#### Utilities
- `utils/validators.py`: Type checking and validation functions
- `utils/converters.py`: Unit conversion utilities
- `utils/logging.py`: Centralized logging configuration

#### CLI Interfaces
- `analyze-model`: Command-line tool for model analysis
- `analyze-hardware`: Command-line tool for hardware analysis
- Entry points configured in `pyproject.toml`

#### REST API
- FastAPI-based REST API with OpenAPI/Swagger documentation
- `POST /api/v1/models/analyze`: Model analysis endpoint
- `POST /api/v1/hardware/analyze`: Hardware analysis endpoint
- `GET /health`: Health check endpoint
- Pydantic request/response models for validation
- CORS middleware support

#### Package Management
- `pyproject.toml`: Modern Python packaging configuration
- Split requirements files (base, ai, dev)
- Makefile with common development tasks
- Console script entry points

#### Documentation
- Comprehensive README with installation and usage examples
- API documentation with endpoint descriptions
- Migration guide for existing code

### Changed

#### Analyzers Restructured
- Model analyzers reorganized:
  - `analyzers/model/classical/`: KNN, K-Means, Trees
  - `analyzers/model/neural/`: Layers (CNNs), Transformers, LLMs
  - `analyzers/model/core.py`: Orchestration logic
- Hardware analyzers reorganized:
  - `analyzers/hardware/devices/`: CPU, GPU, TPU, accelerator, cluster analyzers
  - `analyzers/hardware/core.py`: Hardware spec orchestration
  - `analyzers/hardware/utils.py`: Hardware-specific utilities

#### Import Paths
- Old: `from model_analyzer.core import analyze_model`
- New: `from choose_your_hardware import analyze_model`

### Removed
- Old `model_analyzer/` directory (migrated to new structure)
- Old `hardware_analyzer/` directory (migrated to new structure)
- Temporary refactoring scripts

### Preserved
- ✅ 100% of original analysis logic
- ✅ All model analysis calculations (FLOPs, memory, activations)
- ✅ All hardware throughput computations
- ✅ Classical ML algorithms (KNN, K-Means, Trees)
- ✅ Neural network analysis (CNNs, Transformers, LLMs)
- ✅ Multi-precision support (FP32, FP16, BF16, INT8)

### Technical Details

#### Architecture Patterns
- Layered architecture with clear separation of concerns
- Dependency injection via settings singleton
- Single Responsibility Principle throughout
- DRY (Don't Repeat Yourself) via shared utilities

#### Code Quality
- Type safety with modern type hints
- Proper exception hierarchy and error propagation
- Structured logging with contextual information
- Input validation at API boundaries using Pydantic

#### Developer Experience
- Simple installation: `pip install -e .`
- CLI tools for common tasks
- Interactive API documentation via Swagger UI
- Makefile for development commands

### Migration Guide

#### For Python Code

```python
# Before
from model_analyzer.core import analyze_model
from hardware_analyzer.core import analyze_hardware_spec

# After
from choose_your_hardware import analyze_model, analyze_hardware_spec
```

#### For Command Line

```bash
# Before
python -m model_analyzer input.json
python -m hardware_analyzer input.json

# After
analyze-model input.json
analyze-hardware input.json
```

#### For API Usage

New REST API available:
```bash
# Start server
python -m choose_your_hardware.api.main

# Or use uvicorn directly
uvicorn choose_your_hardware.api.main:app --reload

# Access docs at http://localhost:8000/docs
```

### Statistics
- 64 files changed
- 3,619 insertions, 224 deletions
- 5 structured commits
- All tests passing

---

## [0.x.x] - Previous Versions

Previous versions used flat module structure with separate `model_analyzer/` and `hardware_analyzer/` packages.
