#!/bin/bash
# Download BOTH models for the multi-agent qGPU demo
# Total download: ~15 GB (8B + 7B models)

set -euo pipefail

MODEL_DIR="${1:-/data/models}"

echo "============================================"
echo "Downloading models for qGPU multi-agent demo"
echo "Target: $MODEL_DIR"
echo "============================================"

pip3 install --break-system-packages huggingface_hub 2>/dev/null || \
pip3 install huggingface_hub

mkdir -p "$MODEL_DIR"

echo ""
echo "[1/2] Downloading Qwen3-VL-8B-Instruct (~8 GB)..."
echo "      Used by: Router + Product Advisor (qGPU Slice 1)"
huggingface-cli download Qwen/Qwen3-VL-8B-Instruct \
    --local-dir "$MODEL_DIR/qwen3-vl-8b" \
    --local-dir-use-symlinks False

echo ""
echo "[2/2] Downloading Qwen2.5-VL-7B-Instruct (~7 GB)..."
echo "      Used by: Order Tracker + Returns (qGPU Slice 2)"
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct \
    --local-dir "$MODEL_DIR/qwen2.5-vl-7b" \
    --local-dir-use-symlinks False

echo ""
echo "============================================"
echo "Download complete!"
echo ""
echo "Model 1: $MODEL_DIR/qwen3-vl-8b ($(du -sh "$MODEL_DIR/qwen3-vl-8b" | cut -f1))"
echo "Model 2: $MODEL_DIR/qwen2.5-vl-7b ($(du -sh "$MODEL_DIR/qwen2.5-vl-7b" | cut -f1))"
echo ""
echo "Start with vLLM (two servers, one GPU):"
echo "  python -m vllm.entrypoints.openai.api_server --model $MODEL_DIR/qwen3-vl-8b --port 8081 --gpu-memory-utilization 0.45 &"
echo "  python -m vllm.entrypoints.openai.api_server --model $MODEL_DIR/qwen2.5-vl-7b --port 8082 --gpu-memory-utilization 0.45 &"
echo "============================================"
