#!/bin/bash
set -e

# =================================================================
# Ashiorid AI Manager - K3s Setup Script for WSL2
# =================================================================
# This script installs and configures K3s on WSL2
# Run with: sudo ./scripts/setup_k3s.sh

echo "🚀 Starting K3s installation for Ashiorid AI Manager..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Check if running on WSL
if ! grep -qi microsoft /proc/version; then
    echo -e "${YELLOW}⚠️  Warning: This script is designed for WSL2${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ Running on WSL${NC}"

# Update system
echo "📦 Updating system packages..."
apt-get update -qq

# Install required dependencies
echo "📦 Installing dependencies..."
apt-get install -y -qq curl wget iptables

# Check if K3s is already installed
if command -v k3s &> /dev/null; then
    echo -e "${YELLOW}⚠️  K3s is already installed${NC}"
    read -p "Reinstall? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Uninstalling existing K3s..."
        /usr/local/bin/k3s-uninstall.sh || true
    else
        echo "Keeping existing installation"
        exit 0
    fi
fi

# Install K3s
echo "📥 Downloading and installing K3s..."
curl -sfL https://get.k3s.io | sh -s - \
    --write-kubeconfig-mode 644 \
    --disable traefik \
    --disable servicelb \
    --disable metrics-server

# Wait for K3s to be ready
echo "⏳ Waiting for K3s to be ready..."
sleep 10

# Check K3s status
if systemctl is-active --quiet k3s; then
    echo -e "${GREEN}✅ K3s is running${NC}"
else
    echo -e "${RED}❌ K3s failed to start${NC}"
    systemctl status k3s
    exit 1
fi

# Set up kubeconfig for non-root user
if [ -n "$SUDO_USER" ]; then
    REAL_USER=$SUDO_USER
    REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

    echo "🔧 Setting up kubectl config for user: $REAL_USER"

    # Create .kube directory
    mkdir -p "$REAL_HOME/.kube"

    # Copy kubeconfig
    cp /etc/rancher/k3s/k3s.yaml "$REAL_HOME/.kube/config"

    # Set proper ownership
    chown -R "$REAL_USER:$REAL_USER" "$REAL_HOME/.kube"
    chmod 600 "$REAL_HOME/.kube/config"

    echo -e "${GREEN}✅ kubectl configured for $REAL_USER${NC}"
fi

# Install kubectl if not present
if ! command -v kubectl &> /dev/null; then
    echo "📥 Installing kubectl..."
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    mv kubectl /usr/local/bin/
fi

# Verify installation
echo "🔍 Verifying K3s installation..."
kubectl version --client --short
kubectl get nodes

# Install Helm
if ! command -v helm &> /dev/null; then
    echo "📥 Installing Helm..."
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

# Create ashiorid namespace
echo "🏗️  Creating ashiorid namespace..."
kubectl create namespace ashiorid --dry-run=client -o yaml | kubectl apply -f -

# Label namespace
kubectl label namespace ashiorid name=ashiorid --overwrite

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ K3s installation completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📝 Next steps:"
echo "  1. Export KUBECONFIG (add to ~/.bashrc):"
echo "     export KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
echo "  2. Verify installation:"
echo "     kubectl get nodes"
echo "  3. Deploy infrastructure:"
echo "     kubectl apply -k k8s/base/"
echo ""
echo -e "${YELLOW}💡 Tip: You can now use kubectl and helm commands${NC}"
echo ""
