# Production-Level Refactoring Plan for ChooseYourHardware

This document outlines a comprehensive refactoring strategy to organize existing code into an industrialized, modern API-aligned structure **without changing core logic**.

---

## 📋 Current State Analysis

### Strengths ✅
- Clear module separation (model_analyzer, hardware_analyzer, metadata_extractor)
- Functional core logic with proper calculations
- Type hints using `from __future__ import annotations`
- Clean validation error handling

### Issues to Address ⚠️

1. **Code Organization**
   - Mixed concerns (validation, calculation, formatting in same files)
   - Large files (nn.py: 273 lines, analyzers.py: 428 lines)
   - No clear API versioning
   - Inconsistent error handling patterns

2. **API Structure**
   - metadata_extractor uses FastAPI, but others use CLI only
   - No REST API for model_analyzer and hardware_analyzer
   - Missing API documentation
   - No request/response schemas standardization

3. **Configuration Management**
   - Hardcoded values scattered in code
   - No centralized config management
   - Environment variables not properly managed

4. **Dependencies**
   - requirements.txt has duplicates and version conflicts
   - No clear separation of dev/prod dependencies

---

## 🎯 Refactoring Strategy

### Phase 1: Project Structure Reorganization

```
ChooseYourHardware/
├── src/                              # Source code (best practice)
│   ├── choose_your_hardware/         # Main package
│   │   ├── __init__.py
│   │   ├── config/                   # Centralized configuration
│   │   │   ├── __init__.py
│   │   │   ├── settings.py           # Pydantic settings
│   │   │   └── constants.py          # Constants
│   │   │
│   │   ├── models/                   # Data models (Pydantic)
│   │   │   ├── __init__.py
│   │   │   ├── model_specs.py        # Model specification schemas
│   │   │   ├── hardware_specs.py     # Hardware specification schemas
│   │   │   └── analysis_results.py   # Result schemas
│   │   │
│   │   ├── analyzers/                # Core analysis logic
│   │   │   ├── __init__.py
│   │   │   ├── model/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py           # Base analyzer class
│   │   │   │   ├── classical/        # Classical ML analyzers
│   │   │   │   │   ├── knn.py
│   │   │   │   │   ├── kmeans.py
│   │   │   │   │   └── trees.py
│   │   │   │   ├── neural/           # Neural network analyzers
│   │   │   │   │   ├── layers.py     # Layer analysis
│   │   │   │   │   ├── transformers.py
│   │   │   │   │   └── llm.py
│   │   │   │   └── core.py           # Main orchestrator
│   │   │   │
│   │   │   └── hardware/
│   │   │       ├── __init__.py
│   │   │       ├── base.py           # Base hardware analyzer
│   │   │       ├── devices/          # Per-device analyzers
│   │   │       │   ├── cpu.py
│   │   │       │   ├── gpu.py
│   │   │       │   ├── accelerator.py
│   │   │       │   ├── edge.py       # Jetson/SoC
│   │   │       │   └── cluster.py
│   │   │       └── core.py
│   │   │
│   │   ├── api/                      # REST API (FastAPI)
│   │   │   ├── __init__.py
│   │   │   ├── v1/                   # API versioning
│   │   │   │   ├── __init__.py
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── models.py     # Model analysis endpoints
│   │   │   │   │   ├── hardware.py   # Hardware analysis endpoints
│   │   │   │   │   └── metadata.py   # Metadata extraction endpoints
│   │   │   │   ├── schemas/          # API request/response schemas
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── requests.py
│   │   │   │   │   └── responses.py
│   │   │   │   └── router.py         # Main router
│   │   │   ├── dependencies.py       # FastAPI dependencies
│   │   │   ├── middleware.py         # Custom middleware
│   │   │   └── main.py               # FastAPI app instance
│   │   │
│   │   ├── services/                 # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── model_service.py
│   │   │   ├── hardware_service.py
│   │   │   └── metadata_service.py
│   │   │
│   │   ├── utils/                    # Shared utilities
│   │   │   ├── __init__.py
│   │   │   ├── validators.py
│   │   │   ├── converters.py         # Unit conversions
│   │   │   ├── calculations.py       # Math helpers
│   │   │   └── logging.py            # Logging configuration
│   │   │
│   │   └── exceptions/               # Custom exceptions
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── model_exceptions.py
│   │       └── hardware_exceptions.py
│   │
│   └── cli/                          # CLI interfaces
│       ├── __init__.py
│       ├── model_cli.py
│       └── hardware_cli.py
│
├── tests/                            # Tests mirror src structure
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── docs/                             # Documentation
│   ├── api/
│   ├── guides/
│   └── examples/
│
├── scripts/                          # Utility scripts
│   ├── setup_dev.sh
│   └── run_examples.sh
│
├── examples/                         # Usage examples
│   ├── configs/
│   │   ├── model_specs/
│   │   └── hardware_specs/
│   └── notebooks/
│
├── pyproject.toml                    # Modern Python packaging
├── setup.py                          # Backward compatibility
├── requirements/                     # Split requirements
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── .env.example                      # Environment variables template
├── Makefile                          # Common commands
└── README.md
```

---

## 📝 Detailed Refactoring Tasks

### 1. **File Reorganization (No Logic Changes)**

#### Move model_analyzer → src/choose_your_hardware/analyzers/model/

**Benefits:**
- Clearer namespace
- Better IDE support
- Standard Python package structure

**Migration Map:**
```
model_analyzer/core.py        → analyzers/model/core.py
model_analyzer/knn.py          → analyzers/model/classical/knn.py
model_analyzer/kmeans.py       → analyzers/model/classical/kmeans.py
model_analyzer/trees.py        → analyzers/model/classical/trees.py
model_analyzer/nn.py           → analyzers/model/neural/layers.py
model_analyzer/transformers.py → analyzers/model/neural/transformers.py
model_analyzer/llm.py          → analyzers/model/neural/llm.py
model_analyzer/utils.py        → utils/validators.py (split)
model_analyzer/__main__.py     → cli/model_cli.py
```

#### Split Large Files

**nn.py (273 lines) → Split into:**
```python
# analyzers/model/neural/layers.py
- Layer analysis functions
- Conv layer helpers
- Dense layer helpers
- BatchNorm helpers

# analyzers/model/neural/base.py
- Base neural network analyzer class
- Common neural network utilities

# analyzers/model/neural/cnn.py
- CNN-specific analysis
```

**analyzers.py (428 lines) → Split into:**
```python
# analyzers/hardware/devices/cpu.py
- analyze_cpu_node()

# analyzers/hardware/devices/gpu.py
- analyze_gpu()
- _gpu_peak_from_sms()

# analyzers/hardware/devices/accelerator.py
- analyze_accelerator()

# analyzers/hardware/devices/edge.py
- analyze_jetson()

# analyzers/hardware/devices/cluster.py
- analyze_multi_gpu_node()
- analyze_cluster()

# analyzers/hardware/utils.py
- merge_dtype_support()
- sum_flops_dict()
- sum_ops_dict()
```

---

### 2. **Configuration Management**

#### Create Centralized Settings (src/choose_your_hardware/config/settings.py)

```python
"""Centralized configuration using Pydantic settings."""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    api_title: str = "ChooseYourHardware API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    
    # Hardware Defaults
    default_utilization_fp32: float = 0.5
    default_utilization_fp16: float = 0.5
    default_utilization_bf16: float = 0.5
    default_utilization_int8: float = 0.5
    
    # Paths
    prompts_dir: Path = Path(__file__).parent.parent / "api" / "prompts"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # or "text"
    
    # CORS
    cors_origins: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
settings = Settings()
```

#### Create Constants File (config/constants.py)

```python
"""Application constants."""

# Data type mappings
DTYPE_BITS = {
    "fp32": 32,
    "float32": 32,
    "fp16": 16,
    "float16": 16,
    "bf16": 16,
    "bfloat16": 16,
    "int8": 8,
    "int4": 4,
}

# Hardware kinds
HARDWARE_KINDS = {
    "cpu_node",
    "gpu",
    "tpu",
    "accelerator",
    "jetson",
    "soc",
    "multi_gpu_node",
    "cluster",
}

# Model types
MODEL_TYPES = {
    "knn",
    "kmeans",
    "tree",
    "random_forest",
    "gradient_boosted_trees",
    "neural_network",
    "transformer",
    "llm_decoder",
}

# Unit conversions
GB_TO_BYTES = 1e9
TFLOPS_TO_FLOPS = 1e12
TOPS_TO_OPS = 1e12
```

---

### 3. **API Unification**

#### Create Unified FastAPI Application

**Structure:**
```python
# api/v1/endpoints/models.py
@router.post("/models/analyze", response_model=ModelAnalysisResponse)
async def analyze_model(request: ModelAnalysisRequest):
    """Analyze model computational requirements."""
    pass

# api/v1/endpoints/hardware.py
@router.post("/hardware/analyze", response_model=HardwareAnalysisResponse)
async def analyze_hardware(request: HardwareAnalysisRequest):
    """Analyze hardware specifications."""
    pass

# api/v1/endpoints/metadata.py
@router.post("/metadata/extract", response_model=MetadataExtractionResponse)
async def extract_metadata(request: MetadataExtractionRequest):
    """Extract model metadata from natural language."""
    pass
```

**Benefits:**
- Consistent API interface
- Single deployment point
- Shared middleware and authentication
- Better documentation via OpenAPI

---

### 4. **Error Handling Standardization**

#### Create Exception Hierarchy

```python
# exceptions/base.py
class ChooseYourHardwareException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

# exceptions/model_exceptions.py
class ModelValidationError(ChooseYourHardwareException):
    """Raised when model specification is invalid."""
    pass

class ModelAnalysisError(ChooseYourHardwareException):
    """Raised when model analysis fails."""
    pass

# exceptions/hardware_exceptions.py
class HardwareValidationError(ChooseYourHardwareException):
    """Raised when hardware specification is invalid."""
    pass
```

**Refactor existing code:**
```python
# OLD (model_analyzer/utils.py)
class ValidationError(ValueError):
    """Raised when inputs are missing or inconsistent."""

# NEW (exceptions/model_exceptions.py)
class ModelValidationError(ChooseYourHardwareException):
    """Raised when model specification is invalid."""
    
    def __init__(self, message: str, field: str = None):
        super().__init__(message, details={"field": field})
```

---

### 5. **Data Models with Pydantic**

#### Create Type-Safe Schemas

```python
# models/model_specs.py
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional


class InferenceConfig(BaseModel):
    """Inference configuration."""
    batch_size: int = Field(gt=0, description="Batch size for inference")
    sequence_length: Optional[int] = Field(None, gt=0)


class KNNConfig(BaseModel):
    """K-Nearest Neighbors configuration."""
    num_train_samples: int = Field(gt=0)
    num_features: int = Field(gt=0)
    k: int = Field(gt=0)
    distance_metric: Literal["euclidean", "manhattan"]
    include_sqrt: bool
    selection_algorithm: Literal["none", "full_sort"]


class ModelSpec(BaseModel):
    """Base model specification."""
    model_type: str
    dtype_bits: Optional[int] = Field(None, ge=8, multiple_of=8)
    precision: Optional[str] = None
    inference_config: InferenceConfig
    
    @field_validator('dtype_bits', 'precision')
    def validate_precision(cls, v, info):
        if not v and not info.data.get('precision'):
            raise ValueError("Either dtype_bits or precision must be provided")
        return v
```

**Benefits:**
- Automatic validation
- Better IDE autocomplete
- Self-documenting code
- Easy serialization/deserialization
- OpenAPI schema generation

---

### 6. **Service Layer Pattern**

#### Separate Business Logic from API

```python
# services/model_service.py
from ..models.model_specs import ModelSpec
from ..models.analysis_results import ModelAnalysisResult
from ..analyzers.model.core import ModelAnalyzer


class ModelAnalysisService:
    """Service for model analysis operations."""
    
    def __init__(self):
        self.analyzer = ModelAnalyzer()
    
    async def analyze(self, spec: ModelSpec) -> ModelAnalysisResult:
        """Analyze model computational requirements.
        
        This is a pure service method - no HTTP/API logic here.
        """
        # Existing analyze_model logic
        result = self.analyzer.analyze(spec)
        return ModelAnalysisResult(**result)
    
    async def batch_analyze(
        self, 
        specs: list[ModelSpec]
    ) -> list[ModelAnalysisResult]:
        """Analyze multiple models."""
        return [await self.analyze(spec) for spec in specs]
```

**API Layer uses Service:**
```python
# api/v1/endpoints/models.py
from ....services.model_service import ModelAnalysisService

service = ModelAnalysisService()

@router.post("/models/analyze")
async def analyze_model(request: ModelAnalysisRequest):
    return await service.analyze(request.spec)
```

---

### 7. **Logging Standardization**

#### Create Structured Logging

```python
# utils/logging.py
import logging
import json
from pythonjsonlogger import jsonlogger


def setup_logging(level: str = "INFO", format_type: str = "json"):
    """Configure application logging."""
    
    logger = logging.getLogger()
    logger.setLevel(level)
    
    handler = logging.StreamHandler()
    
    if format_type == "json":
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
```

**Usage in code:**
```python
# OLD
print(f"Model validation failed: {exc}")

# NEW
import logging
logger = logging.getLogger(__name__)
logger.error("Model validation failed", exc_info=True, extra={
    "model_type": model_type,
    "error_type": type(exc).__name__
})
```

---

### 8. **Dependency Management**

#### Split Requirements

**requirements/base.txt:**
```
pydantic>=2.0.0,<3.0.0
pydantic-settings>=2.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
python-dotenv>=1.0.0
httpx>=0.25.0
```

**requirements/dev.txt:**
```
-r base.txt
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
black>=23.0.0
ruff>=0.1.0
mypy>=1.5.0
```

**requirements/ai.txt:**
```
-r base.txt
openai>=1.0.0
```

---

### 9. **Code Quality Improvements (No Logic Changes)**

#### Add Type Hints Consistently

```python
# OLD
def analyze_knn(config, dtype_bits, dtype_bytes, batch_size):
    ...

# NEW
def analyze_knn(
    config: dict[str, Any],
    dtype_bits: int,
    dtype_bytes: int,
    batch_size: int
) -> dict[str, Any]:
    ...
```

#### Add Docstrings (Google Style)

```python
def analyze_transformer(
    config: dict[str, Any],
    dtype_bits: int,
    dtype_bytes: int,
    batch_size: int,
    seq_length: int
) -> dict[str, Any]:
    """Analyze transformer model computational requirements.
    
    Args:
        config: Transformer configuration dictionary
        dtype_bits: Data type bit width (8, 16, or 32)
        dtype_bytes: Data type size in bytes
        batch_size: Inference batch size
        seq_length: Input sequence length
    
    Returns:
        Dictionary containing:
            - model_type: "transformer"
            - dtype_bits: Input dtype bits
            - param_count: Total parameters
            - param_memory_bytes: Memory for parameters
            - activation_peak_bytes: Peak activation memory
            - flops_per_inference: FLOPs per forward pass
            - extra: Additional layer-wise details
    
    Raises:
        ValidationError: If configuration is invalid
    
    Example:
        >>> config = {
        ...     "transformer_config": {
        ...         "num_layers": 12,
        ...         "hidden_size": 768,
        ...         ...
        ...     }
        ... }
        >>> result = analyze_transformer(config, 16, 2, 32, 512)
    """
    ...
```

---

## 🔄 Migration Steps

### Step 1: Backup and Branch
```bash
git checkout -b refactor/industrialize
git add -A
git commit -m "checkpoint: before refactoring"
```

### Step 2: Create New Structure
```bash
mkdir -p src/choose_your_hardware/{config,models,analyzers,api,services,utils,exceptions}
mkdir -p src/choose_your_hardware/analyzers/{model,hardware}
mkdir -p src/choose_your_hardware/api/v1/{endpoints,schemas}
```

### Step 3: Move Files Incrementally
```bash
# Move model analyzer
git mv model_analyzer/knn.py src/choose_your_hardware/analyzers/model/classical/
# Update imports incrementally
```

### Step 4: Update Imports Gradually
- Use automated tools: `sed`, `refurb`, or IDE refactoring
- Test after each batch of changes

### Step 5: Add Configuration Layer
- Create settings.py
- Replace hardcoded values
- Update .env.example

### Step 6: Add Pydantic Models
- Create schema files
- Gradually replace dict with Pydantic models
- Keep backward compatibility

### Step 7: Create Unified API
- Implement FastAPI routers
- Add service layer
- Migrate metadata_extractor API

### Step 8: Documentation
- Add comprehensive docstrings
- Generate API docs
- Update README

---

## 🎯 Expected Outcomes

### Before
```
- 3 separate packages with different patterns
- CLI-only for 2/3 modules
- Mixed validation patterns
- Hardcoded configuration
- Large monolithic files
```

### After
```
✅ Single unified package with clear structure
✅ REST API for all modules
✅ Consistent error handling
✅ Centralized configuration
✅ Modular, maintainable code
✅ Type-safe with Pydantic
✅ Service layer for business logic
✅ Easy to test and extend
```

---

## 📊 Priority Matrix

| Task | Impact | Effort | Priority |
|------|--------|--------|----------|
| File reorganization | High | Medium | 🔴 P0 |
| Configuration management | High | Low | 🔴 P0 |
| Error handling standardization | High | Low | 🔴 P0 |
| Pydantic models | High | Medium | 🟡 P1 |
| Unified API | Medium | High | 🟡 P1 |
| Service layer | Medium | Medium | 🟡 P1 |
| Split requirements | Low | Low | 🟢 P2 |
| Documentation | Medium | Medium | 🟢 P2 |

---

## ⚠️ Important Notes

1. **No Logic Changes**: All refactoring maintains existing algorithms and calculations
2. **Backward Compatibility**: Keep old imports working during transition
3. **Incremental Migration**: Do not refactor everything at once
4. **Test Coverage**: Add tests before moving code
5. **Version Control**: Commit frequently during refactoring

---

This plan transforms the codebase into an industrial-grade, modern API-aligned structure while preserving all existing functionality.
