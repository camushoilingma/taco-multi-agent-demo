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
                        Single L20/L40 GPU
                         48GB via qGPU
```

Two vision-language models share one GPU. Each agent hits the model best suited for its task. The debug panel shows which model and qGPU slice handles each step.

## Quick Start

### No GPU (mock mode)
```bash
docker-compose -f docker-compose.dev.yaml up
# http://localhost:3000
```

### With GPU (vLLM, no TACO needed)
```bash
bash scripts/download_models.sh    # Downloads both models (~15 GB total)
docker-compose up                  # Starts 2 vLLM servers + app
# http://localhost:3000
```

### With TACO-LLM + qGPU (Tencent Cloud)
```bash
docker-compose -f docker-compose.taco.yaml up
```

## Models

| qGPU Slice | Model | Size | Role | Vision |
|------------|-------|------|------|--------|
| Slice 1 | Qwen3-VL-8B | 8B | Router + Product Advisor | Yes |
| Slice 2 | Qwen2.5-VL-7B | 7B | Order Tracker + Returns | Yes |

Both are vision-language models — customers can upload photos of damaged products, order screenshots, or products to identify.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| MODEL1_BASE_URL | http://localhost:8081/v1 | Qwen3-VL-8B endpoint |
| MODEL2_BASE_URL | http://localhost:8082/v1 | Qwen2.5-VL-7B endpoint |
| MOCK_LLM | false | Scripted responses (no GPU) |
| DEBUG_MODE | true | Stream debug events to frontend |

## Tech Stack

- **Models**: Qwen3-VL-8B + Qwen2.5-VL-7B (vision-language)
- **Inference**: TACO-LLM / vLLM (OpenAI-compatible API)
- **GPU**: NVIDIA L20 or L40 (48GB) with qGPU slicing
- **Backend**: Python, FastAPI, WebSocket
- **Frontend**: React, Tailwind CSS
- **Cloud**: Tencent Cloud
