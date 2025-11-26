#!/usr/bin/env python3
"""Update imports in migrated files."""

import re
from pathlib import Path

PROJECT_ROOT = Path("/home/ali/Desktop/Desktop/AUB/semester 7/EECE 490/proj/ChooseYourHardware")
SRC_DIR = PROJECT_ROOT / "src" / "choose_your_hardware"

# Import mapping: old -> new
IMPORT_MAPPINGS = {
    # Model analyzer utils
    r"from \.utils import": "from ....utils import",
    r"from \.\.utils import": "from ...utils import",
    
    # Exceptions
    r"from \.utils import ValidationError": "from ....exceptions import ModelValidationError as ValidationError",
    r"from \.\.utils import ValidationError": "from ...exceptions import ModelValidationError as ValidationError",
    
    # For hardware analyzer
    r"from \.utils import ValidationError": "from ...exceptions import HardwareValidationError as ValidationError",
    
    # Transformers imports
    r"from \.transformers import": "from .transformers import",
}

def update_file_imports(file_path: Path):
    """Update imports in a file."""
    print(f"Updating {file_path.relative_to(PROJECT_ROOT)}")
    
    content = file_path.read_text()
    original_content = content
    
    # Determine context (model or hardware)
    if "model" in str(file_path):
        # Model analyzer files
        content = re.sub(
            r"from \.utils import ValidationError",
            "from ....exceptions import ModelValidationError as ValidationError",
            content
        )
        content = re.sub(
            r"from \.utils import",
            "from ....utils import",
            content
        )
        content = re.sub(
            r"from \.transformers import",
            "from .transformers import",
            content
        )
    elif "hardware" in str(file_path):
        # Hardware analyzer files
        content = re.sub(
            r"from \.utils import ValidationError",
            "from ...exceptions import HardwareValidationError as ValidationError",
            content
        )
        content = re.sub(
            r"from \.utils import",
            "from ...utils import",
            content
        )
    
    # Write back if changed
    if content != original_content:
        file_path.write_text(content)
        print(f"  ✓ Updated imports")
    else:
        print(f"  - No changes needed")

def main():
    """Main function."""
    print("=== Updating imports in migrated files ===\n")
    
    # Update model analyzer files
    model_dir = SRC_DIR / "analyzers" / "model"
    for py_file in model_dir.rglob("*.py"):
        if py_file.name != "__init__.py":
            update_file_imports(py_file)
    
    # Update hardware analyzer files  
    hardware_dir = SRC_DIR / "analyzers" / "hardware"
    for py_file in hardware_dir.rglob("*.py"):
        if py_file.name != "__init__.py":
            update_file_imports(py_file)
    
    print("\n=== Import updates complete! ===")

if __name__ == "__main__":
    main()
