"""Exact computations for neural networks using layer summaries."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from ....exceptions import ModelValidationError as ValidationError
from ....utils import (
    dtype_bits_from_string,
    require_bool,
    require_dict,
    require_int,
    shape_elements,
)


def analyze_neural_summary(nn_root: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a neural network described via usage/model_level/layer_summary."""
    usage = require_dict(nn_root.get("usage_constraints"), "usage_constraints")
    batch_size = require_int(usage, "batch_size", positive=True)

    model_level = require_dict(nn_root.get("model_level"), "model_level")
    precision = model_level.get("precision")
    if precision is None or not isinstance(precision, str):
        raise ValidationError("model_level.precision must be a string (e.g., 'fp32').")
    dtype_bits = dtype_bits_from_string(precision)
    dtype_bytes = dtype_bits // 8

    input_shape = model_level.get("input_shape")
    if not (isinstance(input_shape, list) and all(isinstance(x, int) and x > 0 for x in input_shape)):
        raise ValidationError("model_level.input_shape must be a list of positive integers (excluding batch).")
    layer_summary = nn_root.get("layer_summary")
    if not isinstance(layer_summary, list) or not layer_summary:
        raise ValidationError("layer_summary must be a non-empty list.")

    total_params_declared = model_level.get("total_params")
    if total_params_declared is not None and (not isinstance(total_params_declared, int) or total_params_declared < 0):
        raise ValidationError("model_level.total_params must be a non-negative integer when provided.")

    param_count = 0
    activation_elements = 0
    activation_peak = 0
    flops_total = 0

    current_shape = [batch_size] + input_shape  # channels-first layout implied by sample.
    layer_details: List[Dict[str, Any]] = []

    for idx, layer in enumerate(layer_summary):
        if not isinstance(layer, dict):
            raise ValidationError(f"layer_summary[{idx}] must be an object.")
        layer_type_raw = layer.get("type")
        if not isinstance(layer_type_raw, str):
            raise ValidationError(f"layer_summary[{idx}].type must be a string.")
        layer_type = layer_type_raw.lower()
        params = layer.get("params")
        if not isinstance(params, int) or params < 0:
            raise ValidationError(f"layer_summary[{idx}].params must be a non-negative integer.")
        out_shape = _normalize_output_shape(layer.get("output_shape"), batch_size, idx)

        elems_out = shape_elements(out_shape, allow_none_leading=True)
        # Compute per-layer activation memory from provided output shape.
        activation_elements += elems_out
        activation_peak = max(activation_peak, elems_out)

        if layer_type in {"conv2d", "conv1d", "conv3d"}:
            flops, inferred_params = _conv_flops_and_params(layer, layer_type, current_shape, out_shape)
        elif layer_type in {"dense", "fullyconnected", "linear"}:
            flops, inferred_params = _dense_flops_and_params(layer, current_shape, out_shape)
        elif layer_type in {"batchnormalization", "batchnorm", "batchnorm2d", "batchnorm1d", "batchnorm3d"}:
            flops, inferred_params = _batchnorm_flops_and_params(layer, current_shape, out_shape)
        elif layer_type in {"activation", "relu", "gelu", "sigmoid", "tanh", "softmax", "elu", "selu", "swish"}:
            flops, inferred_params = _activation_flops_and_params(current_shape, out_shape)
        elif layer_type == "flatten":
            flops, inferred_params = 0, 0
        else:
            raise ValidationError(f"Unsupported layer type '{layer_type_raw}' at index {idx}.")

        if inferred_params != params:
            raise ValidationError(
                f"Layer {layer.get('name', idx)} param mismatch: declared {params}, inferred {inferred_params}."
            )

        param_count += params
        flops_total += flops

        layer_details.append(
            {
                "name": layer.get("name", f"layer_{idx}"),
                "type": layer_type_raw,
                "input_shape": current_shape,
                "output_shape": out_shape,
                "params": params,
                "param_bytes": params * dtype_bytes,
                "flops": flops,
                "activation_elements": elems_out,
                "activation_bytes": elems_out * dtype_bytes,
                "flops_per_byte": flops / (params * dtype_bytes + elems_out * dtype_bytes)
                if (params or elems_out) else 0.0,
            }
        )
        current_shape = out_shape

    if total_params_declared is not None and total_params_declared != param_count:
        raise ValidationError(
            f"Declared total_params {total_params_declared} does not match summed params {param_count}."
        )

    activation_peak_bytes = activation_peak * dtype_bytes
    activation_sum_bytes = activation_elements * dtype_bytes

    return {
        "model_type": model_level.get("model_type", "neural_network"),
        "dtype_bits": dtype_bits,
        "param_count": param_count,
        "param_memory_bytes": param_count * dtype_bytes,
        "activation_peak_bytes": activation_peak_bytes,
        "activation_sum_bytes": activation_sum_bytes,
        # For compatibility, keep activation_memory_bytes aligned to peak.
        "activation_memory_bytes": activation_peak_bytes,
        "flops_per_inference": flops_total,
        "extra": {
            "activation_elements_sum": activation_elements,
            "activation_peak_elements": activation_peak,
            "activation_peak_bytes": activation_peak_bytes,
            "layers": layer_details,
        },
        "inference_scenario": {
            "batch_size": batch_size,
            "sequence_length": None,
            "precision_bits": dtype_bits,
        },
    }


# --------------------------------------------------------------------------- #
# Layer helpers
# --------------------------------------------------------------------------- #


def _normalize_output_shape(shape_val: Any, batch_size: int, idx: int) -> List[int | None]:
    if isinstance(shape_val, str):
        raise ValidationError(f"layer_summary[{idx}].output_shape must be a list, not string.")
    if not (isinstance(shape_val, list) or isinstance(shape_val, tuple)):
        raise ValidationError(f"layer_summary[{idx}].output_shape must be a list.")
    shape: List[int | None] = []
    for j, dim in enumerate(shape_val):
        if dim is None:
            shape.append(None if j == 0 else dim)
        elif isinstance(dim, int):
            if dim <= 0:
                raise ValidationError(f"Dimension {j} in output_shape must be positive.")
            shape.append(dim)
        else:
            raise ValidationError(f"Dimension {j} in output_shape must be int or null.")
    if shape and shape[0] is None:
        shape[0] = batch_size
    return shape


def _conv_flops_and_params(
    layer: Dict[str, Any], layer_type: str, in_shape: Sequence[int | None], out_shape: Sequence[int | None]
) -> Tuple[int, int]:
    if len(in_shape) != len(out_shape):
        raise ValidationError("Conv layer input/output rank mismatch.")
    if layer_type == "conv1d" and len(out_shape) != 3:
        raise ValidationError("Conv1D output_shape must have rank 3.")
    if layer_type == "conv2d" and len(out_shape) != 4:
        raise ValidationError("Conv2D output_shape must have rank 4.")
    if layer_type == "conv3d" and len(out_shape) != 5:
        raise ValidationError("Conv3D output_shape must have rank 5.")

    c_in = _require_channel(in_shape, "input")
    c_out = _require_channel(out_shape, "output")
    spatial_out = out_shape[2:] if len(out_shape) > 2 else out_shape[1:]
    elems_out = shape_elements(out_shape, allow_none_leading=True)

    groups = layer.get("groups", 1)
    if not isinstance(groups, int) or groups <= 0:
        raise ValidationError("Conv layer 'groups' must be a positive integer.")
    if c_in % groups != 0:
        raise ValidationError("Conv layer groups must divide input channels.")

    use_bias = layer.get("use_bias")
    if use_bias is not None and not isinstance(use_bias, bool):
        raise ValidationError("Conv layer 'use_bias' must be boolean when provided.")

    params = layer.get("params")
    assert isinstance(params, int)
    denom = c_out * (c_in // groups)

    candidates: List[Tuple[bool, int]] = []
    for bias_flag in (False, True) if use_bias is None else (use_bias,):
        numerator = params - (c_out if bias_flag else 0)
        if numerator <= 0:
            continue
        if numerator % denom == 0:
            kh_kw = numerator // denom
            candidates.append((bias_flag, kh_kw))

    if not candidates:
        raise ValidationError("Conv layer params do not match any valid (bias/groups/kernel) combination.")
    if len(candidates) > 1:
        raise ValidationError("Conv layer parameters ambiguous; specify 'use_bias' or 'groups'.")

    bias_flag, kh_kw = candidates[0]
    flops_per_out = 2 * (c_in // groups) * kh_kw + (1 if bias_flag else 0)
    flops = elems_out * flops_per_out
    inferred_params = c_out * (c_in // groups) * kh_kw + (c_out if bias_flag else 0)
    return flops, inferred_params


def _dense_flops_and_params(
    layer: Dict[str, Any], in_shape: Sequence[int | None], out_shape: Sequence[int | None]
) -> Tuple[int, int]:
    in_features = shape_elements(in_shape, allow_none_leading=True)
    if not out_shape or not isinstance(out_shape[-1], int):
        raise ValidationError("Dense layer output_shape must end with an integer units dimension.")
    units = out_shape[-1]
    params = layer.get("params")
    assert isinstance(params, int)
    use_bias = layer.get("use_bias")
    if use_bias is not None and not isinstance(use_bias, bool):
        raise ValidationError("Dense layer 'use_bias' must be boolean when provided.")

    candidates: List[Tuple[bool, int]] = []
    for bias_flag in (False, True) if use_bias is None else (use_bias,):
        expected = in_features * units + (units if bias_flag else 0)
        if expected == params:
            candidates.append((bias_flag, expected))
    if not candidates:
        raise ValidationError("Dense layer params do not match inferred input/output sizes.")
    if len(candidates) > 1:
        raise ValidationError("Dense layer parameters ambiguous; specify 'use_bias'.")
    bias_flag, inferred_params = candidates[0]

    batch = in_shape[0]
    if not isinstance(batch, int):
        raise ValidationError("Dense layer batch dimension must be concrete after previous layers.")
    flops = 2 * batch * in_features * units + (batch * units if bias_flag else 0)
    return flops, inferred_params


def _batchnorm_flops_and_params(
    layer: Dict[str, Any], in_shape: Sequence[int | None], out_shape: Sequence[int | None]
) -> Tuple[int, int]:
    if len(in_shape) != len(out_shape):
        raise ValidationError("BatchNorm input/output rank mismatch.")
    c = _require_channel(out_shape, "output")
    params = layer.get("params")
    assert isinstance(params, int)
    # Inference BatchNorm typically has gamma and beta; running stats are not floating parameters for inference.
    if params not in {c, 2 * c, 4 * c}:
        raise ValidationError("BatchNorm params must be proportional to channel count.")
    elems_out = shape_elements(out_shape, allow_none_leading=True)
    flops = elems_out * 4  # (x-mean) + scale + shift
    return flops, params


def _activation_flops_and_params(in_shape: Sequence[int | None], out_shape: Sequence[int | None]) -> Tuple[int, int]:
    if len(in_shape) != len(out_shape):
        raise ValidationError("Activation input/output rank mismatch.")
    elems_out = shape_elements(out_shape, allow_none_leading=True)
    return elems_out, 0


def _require_channel(shape: Sequence[int | None], label: str) -> int:
    if len(shape) < 2:
        raise ValidationError(f"{label} shape must have a channel dimension.")
    c = shape[1]
    if not isinstance(c, int) or c <= 0:
        raise ValidationError(f"{label} channel dimension must be a positive integer.")
    return c
