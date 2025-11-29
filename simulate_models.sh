#!/usr/bin/env bash
# Simulate metadata-extractor -> analyzer for various model types.
# Requires API running at $API_URL (default http://localhost:8000/api/v1).

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000/api/v1}"
SESSION_ID="sim-$(date +%s)"
MODEL_TYPES=(knn kmeans tree random_forest gradient_boosted_trees cnn transformer_encoder llm)

build_payload() {
  local model_type=$1
  case "$model_type" in
    knn)
      jq -n --arg mt "$model_type" --arg sid "$SESSION_ID-$model_type" '
        {model_type:$mt, session_id:$sid, reset:true,
         current_state:{
           model_type:"knn",
           precision:"fp32",
           inference_config:{batch_size:4},
           knn_config:{
             num_train_samples:1000,
             num_features:128,
             k:8,
             distance_metric:"euclidean",
             include_sqrt:true,
             selection_algorithm:"full_sort"
           }
         }}'
      ;;
    kmeans)
      jq -n --arg mt "$model_type" --arg sid "$SESSION_ID-$model_type" '
        {model_type:$mt, session_id:$sid, reset:true,
         current_state:{
           model_type:"kmeans",
           precision:"fp32",
           inference_config:{batch_size:4},
           kmeans_config:{
             num_points:10000,
             num_features:64,
             num_clusters:16,
             cluster_sizes:[625,625,625,625,625,625,625,625,625,625,625,625,625,625,625,625],
             distance_metric:"euclidean",
             include_sqrt:true,
             num_iterations:10
           }
         }}'
      ;;
    tree)
      jq -n --arg mt "$model_type" --arg sid "$SESSION_ID-$model_type" '
        {model_type:$mt, session_id:$sid, reset:true,
         current_state:{
           model_type:"tree",
           precision:"fp32",
           inference_config:{batch_size:4},
           tree_config:{
             num_internal_nodes:255,
             num_leaves:256,
             output_dim:1,
             average_path_length:16,
             input_dim:128
           }
         }}'
      ;;
    random_forest)
      jq -n --arg mt "$model_type" --arg sid "$SESSION_ID-$model_type" '
        {model_type:$mt, session_id:$sid, reset:true,
         current_state:{
           model_type:"random_forest",
           precision:"fp32",
           inference_config:{batch_size:4},
           ensemble_config:{
             num_trees:100,
             tree_config:{
               num_internal_nodes:255,
               num_leaves:256,
               output_dim:1,
               average_path_length:16,
               input_dim:128
             }
           }
         }}'
      ;;
    gradient_boosted_trees)
      jq -n --arg mt "$model_type" --arg sid "$SESSION_ID-$model_type" '
        {model_type:$mt, session_id:$sid, reset:true,
         current_state:{
           model_type:"gradient_boosted_trees",
           precision:"fp32",
           inference_config:{batch_size:4},
           ensemble_config:{
             num_trees:200,
             tree_config:{
               num_internal_nodes:255,
               num_leaves:256,
               output_dim:1,
               average_path_length:16,
               input_dim:128
             }
           }
         }}'
      ;;
    cnn)
      jq -n --arg mt "$model_type" --arg sid "$SESSION_ID-$model_type" '
        {model_type:$mt, session_id:$sid, reset:true,
         current_state:{
           usage_constraints:{batch_size:4, target_latency_s:0.1},
           model_level:{
             input_shape:[3,224,224],
             precision:"fp32",
             total_params:9408,
             trainable_params:9408,
             non_trainable_params:0,
             framework:"pytorch",
             model_type:"cnn"
           },
           layer_summary:[
             {"name":"conv1","type":"Conv2d","output_shape":[null,64,112,112],"params":9408}
           ]
         }}'
      ;;
    transformer_encoder)
      jq -n --arg mt "$model_type" --arg sid "$SESSION_ID-$model_type" '
        {model_type:$mt, session_id:$sid, reset:true,
         current_state:{
           usage_constraints:{batch_size:2, target_latency_s:0.2},
           model_level:{
             input_shape:[512,768],
             sequence_length:512,
             precision:"fp32",
             total_params:110000000,
             model_type:"transformer_encoder",
             hidden_dim:768,
             num_heads:12,
             num_layers:12,
             ffn_size:3072,
             max_sequence_length:512,
             use_bias:true,
             use_layernorm:true,
             vocab_size:30522,
             include_embeddings:true,
             include_positional_embeddings:true
           },
           layer_summary:[
             {"name":"self_attn_qkv","type":"Dense","output_shape":[null,512,768],"params":17783808},
             {"name":"mlp_fc","type":"Dense","output_shape":[null,512,3072],"params":236011008}
           ]
         }}'
      ;;
    llm)
      jq -n --arg mt "$model_type" --arg sid "$SESSION_ID-$model_type" '
        {model_type:$mt, session_id:$sid, reset:true,
         current_state:{
           usage_constraints:{batch_size:1, target_latency_s:0.5},
           model_level:{
             precision:"fp16",
             context_length:2048,
             total_params:7000000000,
             model_type:"llm",
             hidden_dim:4096,
             num_heads:32,
             num_layers:32,
             ffn_size:16384,
             max_sequence_length:2048,
             use_bias:false,
             use_layernorm:true,
             vocab_size:50000,
             include_embeddings:true,
             include_positional_embeddings:true,
             include_kv_cache:true
           },
           layer_summary:[]
         }}'
      ;;
    *)
      echo "Unknown model type $model_type" >&2
      return 1
      ;;
  esac
}

call_extract_and_analyze() {
  local model_type=$1
  echo "\n=== $model_type ==="
  local payload
  payload=$(build_payload "$model_type")
  case "$model_type" in
    knn|kmeans|tree|random_forest|gradient_boosted_trees)
      curl -sSf -X POST "$API_URL/metadata/extract-and-analyze" \
        -H "Content-Type: application/json" \
        -d "$payload" | jq .
      ;;
    *)
      curl -sSf -X POST "$API_URL/metadata/extract-and-analyze" \
        -H "Content-Type: application/json" \
        -d "$payload" | jq .
      ;;
  esac
}

for mt in "${MODEL_TYPES[@]}"; do
  call_extract_and_analyze "$mt"
done
