"""ChooseYourHardware - ML hardware selection and cost analysis tool."""

from analyzers.hardware.core import analyze_hardware_spec
from analyzers.model.core import analyze_model

__version__ = "1.0.0"

__all__ = ["analyze_model", "analyze_hardware_spec", "__version__"]
