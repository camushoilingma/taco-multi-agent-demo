#!/bin/bash
# Download BOTH AWQ-quantized models for the multi-agent qGPU demo
# Optimized for V100 32GB — INT4 quantization fits both models easily
# Total download: ~12 GB (8B AWQ + 7B AWQ)

set -euo pipefail

MODEL_DIR="${1:-/data/models}"

echo "============================================"
echo "Downloading AWQ models for qGPU multi-agent demo"
echo "Target GPU: NVIDIA V100 32GB"
echo "Target: $MODEL_DIR"
echo "============================================"

pip3 install --break-system-packages huggingface_hub 2>/dev/null || \
pip3 install huggingface_hub

mkdir -p "$MODEL_DIR"

echo ""
echo "[1/2] Downloading Qwen3-VL-8B-Instruct-AWQ-4bit (~5 GB)..."
echo "      Used by: Router + Product Advisor (qGPU Slice 1)"
huggingface-cli download Qwen/Qwen3-VL-8B-Instruct-AWQ-4bit \
    --local-dir "$MODEL_DIR/qwen3-vl-8b-awq" \
    --local-dir-use-symlinks False

echo ""
echo "[2/2] Downloading Qwen2.5-VL-7B-Instruct-AWQ (~7 GB)..."
echo "      Used by: Order Tracker + Returns (qGPU Slice 2)"
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct-AWQ \
    --local-dir "$MODEL_DIR/qwen2.5-vl-7b-awq" \
    --local-dir-use-symlinks False

echo ""
echo "============================================"
echo "Download complete!"
echo ""
echo "Model 1: $MODEL_DIR/qwen3-vl-8b-awq ($(du -sh "$MODEL_DIR/qwen3-vl-8b-awq" | cut -f1))"
echo "Model 2: $MODEL_DIR/qwen2.5-vl-7b-awq ($(du -sh "$MODEL_DIR/qwen2.5-vl-7b-awq" | cut -f1))"
echo ""
echo "GPU: NVIDIA V100 32GB (AWQ INT4 — both models fit in ~9GB total)"
echo ""
echo "Run with docker-compose:"
echo "  docker-compose up"
echo ""
echo "Or manually with vLLM:"
echo "  python -m vllm.entrypoints.openai.api_server --model $MODEL_DIR/qwen3-vl-8b-awq --dtype half --quantization awq --port 8081 --gpu-memory-utilization 0.45 &"
echo "  python -m vllm.entrypoints.openai.api_server --model $MODEL_DIR/qwen2.5-vl-7b-awq --dtype half --quantization awq --port 8082 --gpu-memory-utilization 0.45 &"
echo "============================================"
