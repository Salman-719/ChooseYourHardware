# Quick Start: Immediate Improvements (No Restructuring)

This guide provides **immediate, actionable improvements** you can apply right now without major restructuring.

---

## 🚀 Quick Wins (1-2 Hours)

### 1. Clean Up requirements.txt

**Current issues:**
- Duplicates (`python-dotenv` appears twice)
- No version pinning
- Mixed with unused dependencies

**Action: Replace requirements.txt**

```txt
# Core dependencies
pydantic>=2.12.0,<3.0.0
pydantic-core>=2.41.0
fastapi>=0.104.0,<1.0.0
uvicorn[standard]>=0.24.0,<1.0.0
python-dotenv>=1.0.0,<2.0.0

# AI/ML
openai>=1.0.0,<2.0.0

# HTTP client
httpx>=0.25.0,<1.0.0

# Development (comment out for production)
# pytest>=7.4.0
# black>=23.0.0
# ruff>=0.1.0
```

---

### 2. Add .env.example

**Action: Create .env.example file**

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-api-key-here
OPENAI_LLM_MODEL=gpt-4o-mini

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Logging
LOG_LEVEL=INFO

# Hardware Analysis Defaults
DEFAULT_UTILIZATION_FP32=0.5
DEFAULT_UTILIZATION_FP16=0.5
DEFAULT_UTILIZATION_BF16=0.5
DEFAULT_UTILIZATION_INT8=0.5
```

---

### 3. Fix metadata_extractor/app/config.py

**Current issues:**
- Prompts loaded at module level (fails if files missing)
- No validation
- Input prompt for API key breaks non-interactive environments

**Action: Refactor config.py**

```python
"""Configuration management for metadata extractor."""

import os
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent
        self.PROMPTS_DIR = self.BASE_DIR / "prompts"
        
        # OpenAI Configuration
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.OPENAI_LLM_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
        
        # Validate API key
        if not self.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not found. Please set it in .env file or environment variables."
            )
        
        # Prompt paths
        self.ASKER_PROMPT_PATH = self.PROMPTS_DIR / "metadata_extractor_asker.txt"
        self.UPDATER_PROMPT_PATH = self.PROMPTS_DIR / "metadata_extractor_updater.txt"
        self.MODEL_FIELDS_PATH = self.PROMPTS_DIR / "model_fields.json"
        self.LAYER_TYPES_PATH = self.PROMPTS_DIR / "layer_types.json"
    
    def load_prompt(self, prompt_path: Path) -> str:
        """Load prompt file with error handling."""
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text()
    
    def load_json(self, json_path: Path) -> dict:
        """Load JSON file with error handling."""
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        with open(json_path) as f:
            return json.load(f)
    
    @property
    def asker_prompt(self) -> str:
        """Lazy load asker prompt."""
        return self.load_prompt(self.ASKER_PROMPT_PATH)
    
    @property
    def updater_prompt(self) -> str:
        """Lazy load updater prompt."""
        return self.load_prompt(self.UPDATER_PROMPT_PATH)
    
    @property
    def model_fields(self) -> dict:
        """Lazy load model fields."""
        return self.load_json(self.MODEL_FIELDS_PATH)
    
    @property
    def layer_types(self) -> dict:
        """Lazy load layer types."""
        return {"cnn": self.load_json(self.LAYER_TYPES_PATH)}


# Singleton instance
config = Config()
```

**Update services/extractor.py to use new config:**
```python
# OLD
from ..config import ASKER_PROMPT, MODEL_FIELDS

# NEW
from ..config import config

# Usage
asker_prompt = config.asker_prompt
model_fields = config.model_fields
```

---

### 4. Add Proper Logging

**Action: Create utils/logger.py in each module**

**model_analyzer/logger.py:**
```python
"""Logging configuration for model analyzer."""

import logging
import sys


def get_logger(name: str = "model_analyzer") -> logging.Logger:
    """Get configured logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if no handlers exist
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # Format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger
```

**Usage in code:**
```python
# At top of file
from .logger import get_logger

logger = get_logger(__name__)

# Replace prints
# OLD
print(f"Model validation failed: {exc}")

# NEW
logger.error(f"Model validation failed: {exc}", exc_info=True)
```

---

### 5. Standardize Error Messages

**Action: Add error codes and better messages**

**model_analyzer/utils.py:**
```python
class ValidationError(ValueError):
    """Raised when inputs are missing or inconsistent."""
    
    def __init__(self, message: str, field: str = None, value: any = None):
        self.field = field
        self.value = value
        
        # Build detailed message
        detailed_message = f"Validation Error: {message}"
        if field:
            detailed_message += f" (field: '{field}')"
        if value is not None:
            detailed_message += f" (value: {value})"
        
        super().__init__(detailed_message)


# Usage
raise ValidationError(
    "dtype_bits must be a positive multiple of 8",
    field="dtype_bits",
    value=dtype_bits
)
```

---

### 6. Add API Health Check

**Action: Add to metadata_extractor/app/main.py**

```python
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from .routers.extractor_router import router as extractor_router
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ChooseYourHardware - Metadata Extractor API",
    version="1.0.0",
    description="AI-powered model metadata extraction service",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(extractor_router, prefix="/api/v1", tags=["extraction"])


@app.get("/", tags=["health"])
def root():
    """Root endpoint."""
    return {
        "service": "ChooseYourHardware Metadata Extractor",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health", status_code=status.HTTP_200_OK, tags=["health"])
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "metadata-extractor"
    }


@app.on_event("startup")
async def startup_event():
    """Log startup."""
    logger.info("Metadata Extractor API started")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown."""
    logger.info("Metadata Extractor API shutting down")
```

---

### 7. Add __all__ to __init__.py files

**Action: Make public API explicit**

**model_analyzer/__init__.py:**
```python
"""Model analyzer package - analyze computational requirements of ML models."""

from .core import analyze_model
from .utils import ValidationError

__version__ = "1.0.0"
__all__ = ["analyze_model", "ValidationError"]
```

**hardware_analyzer/__init__.py:**
```python
"""Hardware analyzer package - normalize and analyze hardware specifications."""

from .core import analyze_hardware_spec, analyze_hardware_spec_json
from .utils import ValidationError

__version__ = "1.0.0"
__all__ = ["analyze_hardware_spec", "analyze_hardware_spec_json", "ValidationError"]
```

---

### 8. Add Input Validation Examples

**Action: Add example validation in core.py files**

**model_analyzer/core.py - Add at top of analyze_model:**
```python
def analyze_model(model_json: str) -> str:
    """Public API: analyze a model configuration JSON string.
    
    Args:
        model_json: JSON string containing model specification
    
    Returns:
        JSON string with analysis results containing:
        - param_count: Total trainable parameters
        - param_memory_bytes: Memory required for parameters
        - activation_memory_bytes: Peak activation memory
        - flops_per_inference: FLOPs per forward pass
    
    Raises:
        ValidationError: If model_json is invalid or missing required fields
    
    Example:
        >>> config = {"model_type": "knn", ...}
        >>> result = analyze_model(json.dumps(config))
        >>> print(json.loads(result)["param_count"])
    """
    # Validate input type
    if not isinstance(model_json, str):
        raise ValidationError(
            f"model_json must be a string, got {type(model_json).__name__}",
            field="model_json",
            value=type(model_json).__name__
        )
    
    # Validate not empty
    if not model_json.strip():
        raise ValidationError(
            "model_json cannot be empty",
            field="model_json"
        )
    
    # Original code continues...
    raw = load_json(model_json)
    result = _dispatch(raw)
    import json
    return json.dumps(result, indent=2, sort_keys=True)
```

---

### 9. Improve CLI Help Messages

**Action: Update __main__.py files**

**model_analyzer/__main__.py:**
```python
"""Command-line interface for model analyzer."""

import sys
import json
from pathlib import Path
from .core import analyze_model
from .utils import ValidationError


def main() -> int:
    """Main CLI entry point.
    
    Usage:
        python -m model_analyzer <config.json>
        python -m model_analyzer --help
    
    Returns:
        0 on success, 1 on error
    """
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print("Model Analyzer CLI")
        print()
        print("Usage:")
        print("  python -m model_analyzer <config.json>")
        print("  python -m model_analyzer --help")
        print()
        print("Arguments:")
        print("  config.json    Path to model configuration JSON file")
        print()
        print("Example:")
        print("  python -m model_analyzer examples/model_analyzer_input.json")
        return 0 if len(sys.argv) > 1 else 1
    
    config_path = Path(sys.argv[1])
    
    if not config_path.exists():
        print(f"Error: File not found: {config_path}", file=sys.stderr)
        return 1
    
    try:
        model_json = config_path.read_text()
        result = analyze_model(model_json)
        print(result)
        return 0
    except ValidationError as exc:
        print(f"Validation Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected Error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

---

### 10. Add Makefile for Common Commands

**Action: Create Makefile in root**

```makefile
.PHONY: help install dev clean test lint format run-api run-examples

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

dev:  ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest black ruff mypy

clean:  ## Clean up cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

test:  ## Run tests (when available)
	@echo "Tests not yet implemented. Add tests in tests/ directory."

lint:  ## Run linters
	@echo "Running ruff..."
	ruff check . || true
	@echo "Running mypy..."
	mypy model_analyzer hardware_analyzer metadata_extractor || true

format:  ## Format code with black
	black model_analyzer hardware_analyzer metadata_extractor examples

run-api:  ## Run metadata extractor API
	cd metadata_extractor && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-model-example:  ## Run model analyzer example
	python -m model_analyzer examples/model_analyzer_input.json

run-hardware-example:  ## Run hardware analyzer example
	python -m hardware_analyzer examples/hardware_spec.json

check-env:  ## Check if .env file exists
	@test -f .env || (echo "Warning: .env file not found. Copy .env.example to .env" && exit 1)
	@echo ".env file found ✓"
```

**Usage:**
```bash
make help
make install
make run-api
make lint
```

---

## 📋 Implementation Checklist

Apply these improvements in order:

- [ ] 1. Update requirements.txt (2 min)
- [ ] 2. Create .env.example (2 min)
- [ ] 3. Fix metadata_extractor/app/config.py (10 min)
- [ ] 4. Add logging utilities (15 min)
- [ ] 5. Improve error messages (10 min)
- [ ] 6. Add API health checks (5 min)
- [ ] 7. Update __init__.py files (5 min)
- [ ] 8. Add input validation (10 min)
- [ ] 9. Improve CLI help (10 min)
- [ ] 10. Create Makefile (5 min)

**Total Time: ~1.5 hours**

---

## 🎯 Expected Results

### Before
```
❌ requirements.txt has duplicates
❌ No .env.example for setup
❌ Config loads prompts at import (breaks deployment)
❌ No logging (only print statements)
❌ Generic error messages
❌ No health checks
❌ CLI shows no help
```

### After
```
✅ Clean, pinned dependencies
✅ Easy environment setup
✅ Robust configuration loading
✅ Structured logging throughout
✅ Helpful error messages with context
✅ Health check endpoints for monitoring
✅ Helpful CLI with --help
✅ Makefile for common tasks
```

---

These improvements require **NO restructuring** and can be applied immediately to make the codebase more production-ready!
