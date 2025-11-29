#!/bin/bash
# Simple and transparent metadata extractor test

set -e

API_URL="${API_URL:-http://localhost:8000}"
SESSION_ID="test-$(date +%s)"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "================================"
echo "Metadata Extractor Test"
echo "================================"
echo ""

# Check API
echo "Checking API..."
if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: API not running at $API_URL${NC}"
    echo "Start it with: python -m api.main"
    exit 1
fi
echo -e "${GREEN}✓ API is running${NC}"
echo ""

# Test 1
echo "========================================="
echo "TEST 1: Initial Request"
echo "========================================="
echo ""
echo "Request:"
cat << 'EOF'
{
  "model_type": "cnn"
}
EOF
echo ""

echo "Response:"
curl -s -X POST "$API_URL/api/v1/metadata/extract" \
  -H "Content-Type: application/json" \
  -d '{"model_type": "cnn", "session_id": "'$SESSION_ID'"}' | python3 -m json.tool
echo ""
echo ""

# Test 2
echo "========================================="
echo "TEST 2: Provide Batch Size and Shape"
echo "========================================="
echo ""
echo "User says: 'batch size is 4, input shape [3,224,224], fp32'"
echo ""

echo "Response:"
curl -s -X POST "$API_URL/api/v1/metadata/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "model_type": "cnn",
    "session_id": "'$SESSION_ID'",
    "user_input": "batch size is 4, input shape [3,224,224], fp32"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 3
echo "========================================="
echo "TEST 3: Provide Layer Summary"
echo "========================================="
echo ""
echo "User provides model.summary() output"
echo ""

echo "Response:"
curl -s -X POST "$API_URL/api/v1/metadata/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "model_type": "cnn",
    "session_id": "'$SESSION_ID'",
    "user_input": "conv1 Conv2d [null,64,112,112] 9408\nbn1 BatchNorm2d [null,64,112,112] 128"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 4: Complete the extraction
echo "========================================="
echo "TEST 4: Provide Remaining Fields"
echo "========================================="
echo ""
echo "User provides: framework, total_params, target_latency, model_type"
echo ""

echo "Response:"
curl -s -X POST "$API_URL/api/v1/metadata/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "model_type": "cnn",
    "session_id": "'$SESSION_ID'",
    "user_input": "framework is PyTorch, total_params is 25557032, trainable_params is 25557032, non_trainable_params is 0, target_latency is 0.1 seconds, model_type is cnn"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 5: Reset
echo "========================================="
echo "TEST 5: Reset Session"
echo "========================================="
echo ""

echo "Response:"
curl -s -X POST "$API_URL/api/v1/metadata/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "model_type": "cnn",
    "session_id": "'$SESSION_ID'",
    "reset": true
  }' | python3 -m json.tool
echo ""
echo ""

echo "========================================="
echo "Tests Complete!"
echo "========================================="
echo ""
echo "Summary of what happened:"
echo "  Test 1: System asks for ALL required fields"
echo "  Test 2: We provide batch_size, input_shape, precision"
echo "  Test 3: We provide layer_summary (2 layers parsed)"
echo "  Test 4: We provide remaining fields → Should be COMPLETE!"
echo "  Test 5: Reset clears everything"
echo ""
