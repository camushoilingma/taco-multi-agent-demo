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

## GPU Instance Setup (Tencent Cloud CVM)

Tested on **GN10Xp.2XLARGE40** (1x V100 32GB, 10 vCPU, 40GB RAM)

### 1. Provision the Instance

| Setting | Value |
|---------|-------|
| Instance Type | GN10Xp.2XLARGE40 |
| Image | Ubuntu Server 22.04 LTS 64bit (auto GPU driver) |
| System Disk | Enhanced SSD, 100 GiB |
| Data Disk | Enhanced SSD, 200 GiB |
| Public IP | Yes, bill by traffic, 100 Mbps |

Or use Terraform: `cd infra/terraform && terraform apply`

### 2. SSH In

```bash
chmod 600 ~/.ssh/your_key.pem
ssh -i ~/.ssh/your_key.pem ubuntu@<PUBLIC_IP>
```

### 3. Wait for GPU Driver

The auto-install script runs on first boot (~15-25 min). Once your prompt returns:

```bash
nvidia-smi   # verify V100 is detected
```

### 4. Install Docker + NVIDIA Container Toolkit

```bash
# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
newgrp docker
```

### 5. Mount the 200GB Data Disk

```bash
sudo mkfs.ext4 /dev/vdb
sudo mkdir -p /data
sudo mount /dev/vdb /data
echo '/dev/vdb /data ext4 defaults 0 0' | sudo tee -a /etc/fstab
sudo chown ubuntu:ubuntu /data
```

### 6. Clone and Run

```bash
cd /data
git clone https://github.com/camushoilingma/taco-multi-agent-demo.git
cd taco-multi-agent-demo
export HF_TOKEN=hf_your_token_here
docker compose up -d
```

The UI will be available at `http://<PUBLIC_IP>:3000`.

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
