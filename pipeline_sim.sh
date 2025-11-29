#!/usr/bin/env bash
# Simulate the metadata-extractor -> model-analyzer pipeline.
# Real mode: calls the API extractor and analyzer (requires OPENAI_API_KEY and network).
# Offline mode: uses a prefilled metadata sample to show analyzer integration without LLM calls.

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000/api/v1}"
SESSION_ID="${SESSION_ID:-demo-session}"
MODEL_TYPE="${MODEL_TYPE:-cnn}"
MODE="${MODE:-auto}"        # auto | real | offline
START_API="${START_API:-1}" # start uvicorn automatically in real mode
PORT="${PORT:-8000}"

have_openai_key() { [[ -n "${OPENAI_API_KEY:-}" ]]; }

start_api() {
  if [[ "${START_API}" -ne 1 ]]; then
    echo "INFO: START_API=0, assuming API already running at ${API_URL}" >&2
    return
  fi
  echo "INFO: starting API server on port ${PORT}..." >&2
  export PYTHONPATH="${PYTHONPATH:-$(pwd)/src}"
  uvicorn api.main:app --host 0.0.0.0 --port "${PORT}" >/tmp/cyh_api.log 2>&1 &
  API_PID=$!
  trap '[[ -n "${API_PID:-}" ]] && kill "${API_PID}" >/dev/null 2>&1 || true' EXIT
  # Wait briefly for server to come up
  for _ in {1..10}; do
    if curl -sSf "http://localhost:${PORT}/health" >/dev/null 2>&1; then
      echo "INFO: API is up" >&2
      return
    fi
    sleep 0.5
  done
  echo "ERROR: API did not start. Check /tmp/cyh_api.log" >&2
  exit 1
}

real_mode() {
  command -v curl >/dev/null || { echo "ERROR: curl is required." >&2; exit 1; }
  command -v jq >/dev/null || { echo "ERROR: jq is required to parse responses." >&2; exit 1; }

  if ! have_openai_key; then
    echo "ERROR: OPENAI_API_KEY is required for real mode. Set it or use MODE=offline." >&2
    exit 1
  fi

  start_api

  echo "INFO: Turn 1 - initial extractor call"
  payload1=$(jq -n --arg mt "${MODEL_TYPE}" --arg sid "${SESSION_ID}" \
    '{model_type:$mt, session_id:$sid, reset:true}')
  resp1=$(curl -sSf -X POST "${API_URL}/metadata/extract-and-analyze" \
    -H "Content-Type: application/json" \
    -d "${payload1}")
  echo "Response 1: ${resp1}"

  next_question=$(echo "${resp1}" | jq -r '.next_question // empty')
  is_complete=$(echo "${resp1}" | jq -r '.is_complete')
  if [[ "${is_complete}" == "true" ]]; then
    echo "INFO: Extraction already complete; analysis attached above."
    return
  fi
  echo "INFO: Next question from extractor: ${next_question}"

  echo "INFO: Turn 2 - simulate user reply and call again"
  user_reply="batch size is 4, input shape [3,224,224], precision fp32, conv1 params 9408, output [null,64,112,112]"
  payload2=$(jq -n --arg mt "${MODEL_TYPE}" --arg sid "${SESSION_ID}" \
    --arg lq "${next_question}" --arg ui "${user_reply}" \
    '{model_type:$mt, session_id:$sid, last_question:$lq, user_input:$ui}')
  resp2=$(curl -sSf -X POST "${API_URL}/metadata/extract-and-analyze" \
    -H "Content-Type: application/json" \
    -d "${payload2}")
  echo "Response 2: ${resp2}"

  is_complete2=$(echo "${resp2}" | jq -r '.is_complete')
  if [[ "${is_complete2}" == "true" ]]; then
    echo "INFO: Extraction complete; analysis included above."
    return
  fi

  echo "INFO: Turn 3 - provide remaining fields and call again"
  next_question2=$(echo "${resp2}" | jq -r '.next_question')
  user_reply2="target latency 0.1s, total params 9408, trainable 9408, non trainable 0, framework pytorch, model type cnn"
  payload3=$(jq -n --arg mt "${MODEL_TYPE}" --arg sid "${SESSION_ID}" \
    --arg lq "${next_question2}" --arg ui "${user_reply2}" \
    '{model_type:$mt, session_id:$sid, last_question:$lq, user_input:$ui}')
  resp3=$(curl -sSf -X POST "${API_URL}/metadata/extract-and-analyze" \
    -H "Content-Type: application/json" \
    -d "${payload3}")
  echo "Response 3: ${resp3}"

  is_complete3=$(echo "${resp3}" | jq -r '.is_complete')
  if [[ "${is_complete3}" == "true" ]]; then
    echo "INFO: Extraction complete; analysis included above."
  else
    echo "INFO: Still incomplete; ask user: $(echo "${resp3}" | jq -r '.next_question')"
  fi
}

offline_mode() {
  echo "INFO: Offline mode - using static metadata and analyzer locally"
  python - <<'PY'
import json
from analyzers.model.core import analyze_model

metadata = {
    "usage_constraints": {"batch_size": 2},
    "model_level": {"precision": "fp16", "input_shape": [3, 224, 224]},
    "layer_summary": [
        {"name": "conv1", "type": "Conv2d", "output_shape": [None, 32, 112, 112], "params": 864},
        {"name": "relu1", "type": "ReLU", "output_shape": [None, 32, 112, 112], "params": 0},
        {"name": "flatten", "type": "Flatten", "output_shape": [None, 401408], "params": 0},
        {"name": "fc", "type": "Dense", "output_shape": [None, 10], "params": 8028170}
    ]
}
print(json.dumps(json.loads(analyze_model(json.dumps(metadata))), indent=2))
PY
}

case "${MODE}" in
  real)
    real_mode
    ;;
  offline)
    offline_mode
    ;;
  auto)
    if have_openai_key; then
      real_mode
    else
      offline_mode
    fi
    ;;
  *)
    echo "ERROR: Unknown MODE=${MODE}. Use auto|real|offline." >&2
    exit 1
    ;;
esac
