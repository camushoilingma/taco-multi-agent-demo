# Tencent Cloud GPU Instance for Multi-Agent E-Commerce Demo
# Instance: GN10Xp.2XLARGE40 — 1x NVIDIA V100 32GB, 10 vCPU, 40GB RAM
# Region: Singapore (ap-singapore), Zone 3
#
# Usage:
#   cp terraform.tfvars.example terraform.tfvars  # fill in your values
#   terraform init
#   terraform plan
#   terraform apply
#
# After apply, SSH in and run:
#   ssh ubuntu@<output.public_ip>
#   cd /data && git clone <repo> && cd taco-multi-agent-demo
#   export HF_TOKEN=... && docker compose up -d

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
    # Allow all outbound
    "ACCEPT#0.0.0.0/0#ALL#ALL",
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

  # Auto-install GPU driver, Docker, mount data disk, clone repo
  user_data = base64encode(<<-SCRIPT
    #!/bin/bash
    set -euo pipefail
    exec > /var/log/user-data.log 2>&1

    echo "=== Starting setup $(date) ==="

    # Wait for GPU driver installation to complete
    echo "Waiting for NVIDIA driver..."
    for i in $(seq 1 60); do
      if nvidia-smi &>/dev/null; then
        echo "NVIDIA driver ready"
        break
      fi
      echo "Waiting... ($i/60)"
      sleep 10
    done

    # Install Docker
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker ubuntu

    # Install NVIDIA Container Toolkit
    echo "Installing NVIDIA Container Toolkit..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
      gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update && apt-get install -y nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker

    # Mount data disk
    echo "Mounting data disk..."
    if [ -b /dev/vdb ]; then
      mkfs.ext4 -F /dev/vdb
      mkdir -p /data
      mount /dev/vdb /data
      echo '/dev/vdb /data ext4 defaults 0 0' >> /etc/fstab
      chown ubuntu:ubuntu /data
    fi

    # Clone repo
    echo "Cloning demo repo..."
    su - ubuntu -c "cd /data && git clone https://github.com/camushoilingma/taco-multi-agent-demo.git" || true

    echo "=== Setup complete $(date) ==="
    echo "SSH in and run:"
    echo "  cd /data/taco-multi-agent-demo"
    echo "  export HF_TOKEN=hf_..."
    echo "  docker compose up -d"
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
