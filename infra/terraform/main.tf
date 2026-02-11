# Tencent Cloud GPU Instance for Multi-Agent E-Commerce Demo
# Instance: GN10Xp.2XLARGE40 — 1x NVIDIA V100 32GB, 10 vCPU, 40GB RAM
# Region: Singapore (ap-singapore), Zone 3
#
# This is a FULLY AUTOMATED setup. After `terraform apply`, the instance
# will self-provision: wait for GPU driver, install Docker + NVIDIA Container
# Toolkit, mount the data disk, and clone the repo. The only manual step is
# setting HF_TOKEN and running docker-compose.
#
# Usage:
#   cp terraform.tfvars.example terraform.tfvars  # fill in your values
#   terraform init
#   terraform plan
#   terraform apply
#
# After apply (~20-30 min for full bootstrap):
#   ssh ubuntu@<output.public_ip>
#   tail -f /var/log/user-data.log        # monitor bootstrap progress
#   cd /data/taco-multi-agent-demo
#   export HF_TOKEN=hf_...
#   docker-compose up -d                  # first run: ~25-40 min (pulls images + models)

terraform {
  required_providers {
    tencentcloud = {
      source  = "tencentcloudstack/tencentcloud"
      version = ">= 1.81.0"
    }
  }
  required_version = ">= 1.0"
}

provider "tencentcloud" {
  secret_id  = var.secret_id
  secret_key = var.secret_key
  region     = var.region
}

# ──────────────────────── Variables ────────────────────────

variable "secret_id" {
  description = "Tencent Cloud API Secret ID"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Tencent Cloud API Secret Key"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "Tencent Cloud region"
  type        = string
  default     = "ap-singapore"
}

variable "availability_zone" {
  description = "Availability zone"
  type        = string
  default     = "ap-singapore-3"
}

variable "ssh_key_id" {
  description = "Existing SSH key pair ID (from CVM > SSH Key Pairs)"
  type        = string
}

variable "project_name" {
  description = "Name tag for all resources"
  type        = string
  default     = "taco-demo"
}

variable "hf_token" {
  description = "HuggingFace token for model downloads (optional — can set later via env var)"
  type        = string
  default     = ""
  sensitive   = true
}

# ──────────────────────── Security Group ────────────────────────

resource "tencentcloud_security_group" "demo" {
  name        = "${var.project_name}-sg"
  description = "Security group for multi-agent demo"
}

resource "tencentcloud_security_group_lite_rule" "demo" {
  security_group_id = tencentcloud_security_group.demo.id

  ingress = [
    # SSH
    "ACCEPT#0.0.0.0/0#22#TCP",
    # Frontend UI
    "ACCEPT#0.0.0.0/0#3000#TCP",
    # Backend API / WebSocket
    "ACCEPT#0.0.0.0/0#8000#TCP",
    # ICMP (ping)
    "ACCEPT#0.0.0.0/0#ALL#ICMP",
  ]

  egress = [
    # HTTPS outbound (Docker Hub, HuggingFace, GitHub, NVIDIA toolkit)
    # apt uses Tencent internal mirrors via private network, so port 80 not needed
    "ACCEPT#0.0.0.0/0#443#TCP",
  ]
}

# ──────────────────────── Data Sources ────────────────────────

# Ubuntu 22.04 LTS with GPU driver pre-installed
data "tencentcloud_images" "ubuntu" {
  image_type = ["PUBLIC_IMAGE"]
  os_name    = "Ubuntu Server 22.04 LTS 64bit"
}

# ──────────────────────── GPU Instance ────────────────────────

resource "tencentcloud_instance" "gpu" {
  instance_name              = "${var.project_name}-gpu"
  availability_zone          = var.availability_zone
  image_id                   = data.tencentcloud_images.ubuntu.images[0].image_id
  instance_type              = "GN10Xp.2XLARGE40"
  instance_charge_type       = "POSTPAID_BY_HOUR"
  internet_charge_type       = "TRAFFIC_POSTPAID_BY_HOUR"
  internet_max_bandwidth_out = 100
  allocate_public_ip         = true

  system_disk_type = "CLOUD_SSD"
  system_disk_size = 100

  # 200GB data disk for models + Docker
  data_disks {
    data_disk_type = "CLOUD_SSD"
    data_disk_size = 200
  }

  key_ids = [var.ssh_key_id]

  orderly_security_groups = [
    tencentcloud_security_group.demo.id,
  ]

  # Fully automated bootstrap: GPU driver wait, Docker, NVIDIA toolkit,
  # data disk mount, repo clone, and optionally start the demo
  user_data = base64encode(<<-SCRIPT
    #!/bin/bash
    set -euo pipefail
    exec > /var/log/user-data.log 2>&1

    echo "=== Starting bootstrap $(date) ==="

    # ── Step 1: Wait for GPU driver (auto-installed by Tencent image) ──
    echo "[1/6] Waiting for NVIDIA driver..."
    for i in $(seq 1 90); do
      if nvidia-smi &>/dev/null; then
        echo "NVIDIA driver ready after $((i * 10))s"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
        break
      fi
      if [ "$i" -eq 90 ]; then
        echo "ERROR: NVIDIA driver not detected after 15 minutes"
        exit 1
      fi
      sleep 10
    done

    # ── Step 2: Mount data disk ──
    echo "[2/6] Mounting data disk..."
    if [ -b /dev/vdb ]; then
      mkfs.ext4 -F /dev/vdb
      mkdir -p /data
      mount /dev/vdb /data
      echo '/dev/vdb /data ext4 defaults 0 0' >> /etc/fstab
      chown ubuntu:ubuntu /data
      echo "Data disk mounted at /data ($(lsblk -n -o SIZE /dev/vdb))"
    else
      echo "WARNING: /dev/vdb not found, skipping data disk mount"
      mkdir -p /data && chown ubuntu:ubuntu /data
    fi

    # ── Step 3: Install Docker via apt (get.docker.com times out on Tencent) ──
    echo "[3/6] Installing Docker..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq docker.io docker-compose
    usermod -aG docker ubuntu
    echo "Docker version: $(docker --version)"

    # ── Step 4: Install NVIDIA Container Toolkit ──
    echo "[4/6] Installing NVIDIA Container Toolkit..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
      gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update -qq && apt-get install -y -qq nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker

    # Verify GPU is accessible from Docker
    if docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi &>/dev/null; then
      echo "Docker GPU access verified"
    else
      echo "WARNING: Docker GPU access test failed (may work after image pull)"
    fi

    # ── Step 5: Clone repo ──
    echo "[5/6] Cloning demo repo..."
    su - ubuntu -c "cd /data && git clone https://github.com/camushoilingma/taco-multi-agent-demo.git" || true

    # ── Step 6: Auto-start if HF_TOKEN is provided ──
    HF_TOKEN="${var.hf_token}"
    if [ -n "$HF_TOKEN" ]; then
      echo "[6/6] Starting demo (HF_TOKEN provided)..."
      cd /data/taco-multi-agent-demo
      echo "HF_TOKEN=$HF_TOKEN" > .env
      su - ubuntu -c "cd /data/taco-multi-agent-demo && docker-compose up -d"
      echo "Demo starting — containers pulling images and models (~25-40 min)"
    else
      echo "[6/6] Skipping auto-start (no HF_TOKEN provided)"
      echo "To start manually:"
      echo "  ssh ubuntu@<PUBLIC_IP>"
      echo "  cd /data/taco-multi-agent-demo"
      echo "  export HF_TOKEN=hf_..."
      echo "  docker-compose up -d"
    fi

    echo ""
    echo "=== Bootstrap complete $(date) ==="
    echo "Monitor: tail -f /var/log/user-data.log"
    SCRIPT
  )

  tags = {
    createdby = "terraform"
    project   = var.project_name
  }
}

# ──────────────────────── Outputs ────────────────────────

output "public_ip" {
  description = "Public IP of the GPU instance"
  value       = tencentcloud_instance.gpu.public_ip
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh ubuntu@${tencentcloud_instance.gpu.public_ip}"
}

output "frontend_url" {
  description = "Frontend URL (after docker compose up)"
  value       = "http://${tencentcloud_instance.gpu.public_ip}:3000"
}

output "instance_id" {
  description = "CVM instance ID"
  value       = tencentcloud_instance.gpu.id
}
