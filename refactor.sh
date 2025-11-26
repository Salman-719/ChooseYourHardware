#!/bin/bash
# Full refactoring implementation script
# Execute this script step by step to complete the refactoring

set -e  # Exit on error

PROJECT_ROOT="/home/ali/Desktop/Desktop/AUB/semester 7/EECE 490/proj/ChooseYourHardware"
cd "$PROJECT_ROOT"

echo "=== Step 1: Copy neural network analyzers ==="
cp model_analyzer/nn.py src/choose_your_hardware/analyzers/model/neural/layers.py
cp model_analyzer/transformers.py src/choose_your_hardware/analyzers/model/neural/transformers.py
cp model_analyzer/llm.py src/choose_your_hardware/analyzers/model/neural/llm.py

echo "=== Step 2: Copy hardware analyzers ==="
cp hardware_analyzer/analyzers.py src/choose_your_hardware/analyzers/hardware/devices/all_devices.py
cp hardware_analyzer/core.py src/choose_your_hardware/analyzers/hardware/core.py
cp hardware_analyzer/utils.py src/choose_your_hardware/analyzers/hardware/utils.py

echo "=== Step 3: Copy model analyzer core ==="
cp model_analyzer/core.py src/choose_your_hardware/analyzers/model/core.py

echo "=== Step 4: Create __init__.py files ==="
# Classical analyzers
cat > src/choose_your_hardware/analyzers/model/classical/__init__.py << 'EOF'
"""Classical ML model analyzers."""

from .kmeans import analyze_kmeans
from .knn import analyze_knn
from .trees import analyze_ensemble, analyze_tree

__all__ = ["analyze_knn", "analyze_kmeans", "analyze_tree", "analyze_ensemble"]
EOF

# Neural analyzers
cat > src/choose_your_hardware/analyzers/model/neural/__init__.py << 'EOF'
"""Neural network model analyzers."""

from .layers import analyze_neural_summary
from .llm import analyze_llm_decoder
from .transformers import analyze_transformer

__all__ = ["analyze_neural_summary", "analyze_transformer", "analyze_llm_decoder"]
EOF

# Model analyzers root
cat > src/choose_your_hardware/analyzers/model/__init__.py << 'EOF'
"""Model analyzers package."""

from .classical import analyze_ensemble, analyze_kmeans, analyze_knn, analyze_tree
from .core import analyze_model
from .neural import analyze_llm_decoder, analyze_neural_summary, analyze_transformer

__all__ = [
    "analyze_model",
    "analyze_knn",
    "analyze_kmeans",
    "analyze_tree",
    "analyze_ensemble",
    "analyze_neural_summary",
    "analyze_transformer",
    "analyze_llm_decoder",
]
EOF

# Hardware devices
cat > src/choose_your_hardware/analyzers/hardware/devices/__init__.py << 'EOF'
"""Hardware device analyzers."""

__all__ = []
EOF

# Hardware root
cat > src/choose_your_hardware/analyzers/hardware/__init__.py << 'EOF'
"""Hardware analyzers package."""

from .core import analyze_hardware_spec, analyze_hardware_spec_json

__all__ = ["analyze_hardware_spec", "analyze_hardware_spec_json"]
EOF

# Analyzers root
cat > src/choose_your_hardware/analyzers/__init__.py << 'EOF'
"""Analyzers package."""

from .hardware import analyze_hardware_spec, analyze_hardware_spec_json
from .model import analyze_model

__all__ = ["analyze_model", "analyze_hardware_spec", "analyze_hardware_spec_json"]
EOF

# Main package
cat > src/choose_your_hardware/__init__.py << 'EOF'
"""ChooseYourHardware - ML hardware selection and cost analysis tool."""

from .analyzers import analyze_hardware_spec, analyze_model

__version__ = "1.0.0"

__all__ = ["analyze_model", "analyze_hardware_spec", "__version__"]
EOF

echo "=== Step 5: Create requirements files ==="
mkdir -p requirements

cat > requirements/base.txt << 'EOF'
# Core dependencies
pydantic>=2.12.0,<3.0.0
pydantic-core>=2.41.0
pydantic-settings>=2.0.0
fastapi>=0.104.0,<1.0.0
uvicorn[standard]>=0.24.0,<1.0.0
python-dotenv>=1.0.0,<2.0.0
httpx>=0.25.0,<1.0.0
EOF

cat > requirements/ai.txt << 'EOF'
-r base.txt
# AI/ML dependencies
openai>=1.0.0,<3.0.0
EOF

cat > requirements/dev.txt << 'EOF'
-r base.txt
-r ai.txt
# Development dependencies
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
black>=23.0.0
ruff>=0.1.0
mypy>=1.5.0
EOF

# Update main requirements.txt
cat > requirements.txt << 'EOF'
# Production requirements
-r requirements/ai.txt
EOF

echo "=== Step 6: Create pyproject.toml ==="
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "choose-your-hardware"
version = "1.0.0"
description = "AI/ML hardware selection and cost analysis tool"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
authors = [
    {name = "AUB Team", email = "team@aub.edu.lb"}
]
keywords = ["machine-learning", "hardware", "cost-analysis", "optimization"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "pydantic>=2.12.0,<3.0.0",
    "pydantic-settings>=2.0.0",
    "fastapi>=0.104.0,<1.0.0",
    "uvicorn[standard]>=0.24.0,<1.0.0",
    "python-dotenv>=1.0.0,<2.0.0",
    "httpx>=0.25.0,<1.0.0",
    "openai>=1.0.0,<3.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]

[project.scripts]
analyze-model = "choose_your_hardware.cli.model_cli:main"
analyze-hardware = "choose_your_hardware.cli.hardware_cli:main"

[project.urls]
Homepage = "https://github.com/Salman-719/ChooseYourHardware"
Repository = "https://github.com/Salman-719/ChooseYourHardware"

[tool.setuptools]
package-dir = {"" = "src"}
packages = ["choose_your_hardware"]

[tool.setuptools.package-data]
choose_your_hardware = ["py.typed"]

[tool.black]
line-length = 120
target-version = ['py39']

[tool.ruff]
line-length = 120
target-version = "py39"
select = ["E", "W", "F", "I", "B", "C4", "UP"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
check_untyped_defs = true
no_implicit_optional = true

[[tool.mypy.overrides]]
module = "openai.*"
ignore_missing_imports = true

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q"
testpaths = ["tests"]
pythonpath = ["src"]
EOF

echo "=== Step 7: Create .env.example ==="
cat > .env.example << 'EOF'
# OpenAI Configuration
OPENAI_API_KEY=your-api-key-here
OPENAI_LLM_MODEL=gpt-4o-mini

# API Configuration  
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text

# Hardware Analysis Defaults
DEFAULT_UTILIZATION_FP32=0.5
DEFAULT_UTILIZATION_FP16=0.5
DEFAULT_UTILIZATION_BF16=0.5
DEFAULT_UTILIZATION_INT8=0.5
EOF

echo "=== Step 8: Create Makefile ==="
cat > Makefile << 'EOF'
.PHONY: help install dev clean test lint format

help:
	@echo "Available commands:"
	@echo "  install    - Install production dependencies"
	@echo "  dev        - Install development dependencies"
	@echo "  clean      - Clean cache files"
	@echo "  test       - Run tests"
	@echo "  lint       - Run linters"
	@echo "  format     - Format code"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

test:
	pytest tests/ -v

lint:
	ruff check src/
	mypy src/ || true

format:
	black src/
	ruff check --fix src/

.DEFAULT_GOAL := help
EOF

echo "=== Refactoring script created! ==="
echo "Review and execute this script step by step."
