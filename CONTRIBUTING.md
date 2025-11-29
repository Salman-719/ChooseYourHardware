# Contributing to ChooseYourHardware

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.9 or higher
- Git
- Virtual environment tool (venv, conda, etc.)
- OpenAI API key (for metadata extractor features)
- Node.js 18+ (for frontend development)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Salman-719/ChooseYourHardware.git
   cd ChooseYourHardware
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   make dev
   # Or manually:
   pip install -e ".[dev]"
   ```

4. **Set up environment variables (optional)**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY if using metadata extractor
   ```

## Development Workflow

### Code Organization

The project follows a layered architecture:

```
src/
├── config/              # Configuration and constants
├── utils/              # Shared utilities (validators, converters, logging)
├── analyzers/          # Core analysis engines
│   ├── model/          # Model analyzers (classical, neural)
│   └── hardware/       # Hardware analyzers
├── matchers/           # Latency estimation and hardware matching
├── metadata_extractor/ # LLM-powered metadata extraction
├── api/                # FastAPI REST API
└── cli/                # Command-line interfaces
```

### Coding Standards

#### Type Hints
- Use modern type hints with `from __future__ import annotations`
- Annotate all function parameters and return types
- Use `dict[str, Any]` instead of `Dict[str, Any]` (Python 3.9+)

#### Imports
- Group imports: standard library → third-party → local
- Use absolute imports from package root
- Avoid circular imports

#### Docstrings
- Use Google-style docstrings
- Document all public functions and classes
- Include Args, Returns, and Raises sections

Example:
```python
def analyze_model(model_json: str) -> str:
    """Analyze an ML model configuration.

    Args:
        model_json: JSON string containing model configuration

    Returns:
        JSON string with analysis results

    Raises:
        ModelValidationError: If model configuration is invalid
    """
```

#### Error Handling
- Use custom exceptions from `exceptions/` module
- Provide context in error messages
- Don't catch generic `Exception` unless necessary

### Code Quality Tools

#### Format Code
```bash
make format
# Or manually:
black src/ tests/
isort src/ tests/
```

#### Lint Code
```bash
make lint
# Or manually:
ruff check src/ tests/
mypy src/
```

#### Run Tests
```bash
make test
# Or manually:
pytest tests/ -v --cov=choose_your_hardware
```

## Making Changes

### Branch Naming
- Feature: `feature/<description>`
- Bug fix: `fix/<description>`
- Documentation: `docs/<description>`
- Refactoring: `refactor/<description>`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Build/tooling changes

Examples:
```
feat: add support for transformer models
fix: correct FLOPS calculation for convolution layers
docs: update API endpoint documentation
refactor: extract validation logic to utils
test: add unit tests for hardware analyzer
chore: update dependencies in requirements
```

### Pull Request Process

1. **Create a branch** from `main`
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes**
   - Write code following standards
   - Add/update tests
   - Update documentation

3. **Test your changes**
   ```bash
   make test
   make lint
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add my feature"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```
   Then create a pull request on GitHub

6. **PR Requirements**
   - All tests passing
   - Code coverage maintained or improved
   - Documentation updated
   - Conventional commit format
   - No merge conflicts

## Adding New Features

### New Model Analyzer
1. Create file in `src/choose_your_hardware/analyzers/model/classical/` or `neural/`
2. Implement analyzer function
3. Export from `__init__.py`
4. Add to dispatcher in `core.py`
5. Add tests in `tests/analyzers/model/`
6. Update documentation

### New Hardware Type
1. Add analyzer function in `src/choose_your_hardware/analyzers/hardware/devices/`
2. Update `HARDWARE_KINDS` in `config/constants.py`
3. Add to dispatcher in `core.py`
4. Add tests
5. Update documentation

### New API Endpoint
1. Create endpoint in `src/api/v1/endpoints/`
2. Define Pydantic request/response models
3. Register router in `api/main.py`
4. Add integration tests
5. Update OpenAPI documentation

### New Matcher Feature
1. Update logic in `src/matchers/core.py`
2. Add new scenario types to `config/constants.py` if needed
3. Add unit tests in `tests/matchers/`
4. Update MATH_AND_IO_SPECIFICATION.md

### Metadata Extractor Prompts
1. Update prompts in `src/metadata_extractor/prompts/`
2. Test with various model types
3. Add test scenarios to `test_scenarios.json`
4. Run `test_simple.sh` to validate

## Testing

### Test Structure
```
tests/
├── analyzers/
│   ├── model/
│   └── hardware/
├── matchers/
├── metadata_extractor/
├── api/
├── cli/
└── utils/
```

### Running Tests
```bash
# All tests
make test

# Specific test file
pytest tests/analyzers/model/test_neural.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# API integration tests (requires API running)
./test_simple.sh

# Full pipeline simulation
./simulate_full_pipeline.sh
```

### Writing Tests
- Use pytest fixtures for common setup
- Test both success and error cases
- Use parametrized tests for multiple inputs
- Mock external dependencies

Example:
```python
import pytest
from choose_your_hardware import analyze_model
from choose_your_hardware.exceptions import ModelValidationError

def test_analyze_model_success():
    model_json = '{"model_type": "knn", ...}'
    result = analyze_model(model_json)
    assert "flops_per_inference" in result

def test_analyze_model_invalid_json():
    with pytest.raises(ModelValidationError):
        analyze_model("invalid json")
```

## Documentation

### Updating Documentation
- Update README.md for user-facing changes
- Update CHANGELOG.md following Keep a Changelog format
- Add docstrings to new code
- Update API documentation if adding endpoints

### Building Documentation (Future)
```bash
# When documentation build is added
make docs
```

## Questions or Issues?

- Check existing issues on GitHub
- Ask questions in discussions
- Reach out to maintainers

Thank you for contributing to ChooseYourHardware! 🚀
