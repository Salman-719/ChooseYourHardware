#!/bin/bash
cd "$(dirname "$0")"

python3 ../train.py \
    --model_config_path ../asplos/data/predictor/configs/MLP_WAVE_BMM.json \
    --trainset_path ../asplos/data/dataset/train/bmm.csv \
    --save_path ./out/model \
    --log_dir ./out/logs \
    --epochs 1 \
