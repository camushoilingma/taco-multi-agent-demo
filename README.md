# Multi-Agent E-Commerce Customer Service

A multi-agent AI system that routes customer requests to specialized agents — order tracking, returns processing, and product recommendations — with a live debug panel showing the agent pipeline, model switching, and qGPU allocation in real-time.

**Key demo: multiple small models on one GPU via qGPU** — each agent uses a different model on its own GPU slice, showing Tencent Cloud's GPU efficiency story.

## Architecture

```
Customer -> Orchestrator -> Router (Qwen3-VL-8B, Slice 1)
                               |
                     classifies intent, then:
                               |
                +--------------+--------------+
                |              |              |
                v              v              v
          Order Tracker   Returns Agent  Product Advisor
          Qwen2.5-VL-7B  Qwen2.5-VL-7B  Qwen3-VL-8B
          Slice 2 :8082  Slice 2 :8082  Slice 1 :8081
                |              |              |
                +--------------+--------------+
                               |
                      Single V100 GPU
                     32GB via qGPU (AWQ INT4)
```

Two vision-language models share one GPU using AWQ INT4 quantization (~9GB total weights, leaving 23GB for KV cache). Each agent hits the model best suited for its task. The debug panel shows which model and qGPU slice handles each step.

## Quick Start

### No GPU (mock mode)
```bash
docker-compose -f docker-compose.dev.yaml up
# http://localhost:3000
```

### With GPU (vLLM on V100 32GB)
```bash
export HF_TOKEN=hf_your_token_here
docker-compose up                  # Downloads AWQ models + starts 2 vLLM servers
# http://localhost:3000
```

### With TACO-LLM + qGPU (Tencent Cloud)
```bash
bash download_models.sh /data/models   # Pre-download AWQ models
docker-compose -f docker-compose.taco.yaml up
```

## Models

| qGPU Slice | Model | Quantization | VRAM | Role | Vision |
|------------|-------|-------------|------|------|--------|
| Slice 1 | Qwen3-VL-8B | AWQ INT4 | ~5 GB | Router + Product Advisor | Yes |
| Slice 2 | Qwen2.5-VL-7B | AWQ INT4 | ~4 GB | Order Tracker + Returns | Yes |

Both are vision-language models — customers can upload photos of damaged products, order screenshots, or products to identify. AWQ quantization fits both on a single V100 32GB with plenty of headroom.

## GPU Compatibility

| GPU | VRAM | Quantization | Status |
|-----|------|-------------|--------|
| **NVIDIA V100** | 32 GB | AWQ INT4 (`--dtype half`) | Tested |
| NVIDIA L20/L40 | 48 GB | FP16 or AWQ | Supported (more headroom) |
| NVIDIA T4 | 16 GB | — | Too small for 2 models |

**V100 note**: V100 does not support bfloat16 — all configs use `--dtype half` (FP16).

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| MODEL1_BASE_URL | http://localhost:8081/v1 | Qwen3-VL-8B endpoint |
| MODEL2_BASE_URL | http://localhost:8082/v1 | Qwen2.5-VL-7B endpoint |
| MOCK_LLM | false | Scripted responses (no GPU) |
| DEBUG_MODE | true | Stream debug events to frontend |
| HF_TOKEN | — | HuggingFace token (for model download) |

## Tech Stack

- **Models**: Qwen3-VL-8B + Qwen2.5-VL-7B (vision-language, AWQ INT4)
- **Inference**: TACO-LLM / vLLM (OpenAI-compatible API)
- **GPU**: NVIDIA V100 32GB (GN10Xp on Tencent Cloud)
- **Backend**: Python, FastAPI, WebSocket
- **Frontend**: React, Tailwind CSS
- **Cloud**: Tencent Cloud
