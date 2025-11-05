#!/usr/bin/env bash
set -e

# =================================================================
# Ashiorid AI Manager - Bootstrap Script
# =================================================================
# This script initializes the entire Ashiorid AI Manager project
# Run with: ./scripts/bootstrap.sh

echo "🌍 Welcome to Ashiorid AI Manager Bootstrap!"
echo "This script will set up the entire development environment"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check prerequisites
print_header "Checking Prerequisites"

MISSING_DEPS=()

if ! command -v docker &> /dev/null; then
    MISSING_DEPS+=("docker")
fi

if ! command -v python3 &> /dev/null; then
    MISSING_DEPS+=("python3")
fi

if ! command -v git &> /dev/null; then
    MISSING_DEPS+=("git")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    print_error "Missing required dependencies: ${MISSING_DEPS[*]}"
    echo "Please install them and run this script again"
    exit 1
fi

print_success "All prerequisites are installed"

# Check environment file
print_header "Checking Environment Configuration"

if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    print_success "Created .env file"
    echo ""
    print_warning "⚠️  IMPORTANT: Edit .env and add your API keys!"
    echo "  • ANTHROPIC_API_KEY"
    echo "  • OPENAI_API_KEY"
    echo ""
    read -p "Press Enter when you've updated .env (or continue with defaults)..."
else
    print_success ".env file exists"
fi

# Source environment
set -a
source .env
set +a

# Install K3s
print_header "K3s Setup"

if command -v k3s &> /dev/null; then
    print_success "K3s is already installed"
else
    print_warning "K3s not found"
    read -p "Install K3s? (requires sudo) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        chmod +x scripts/setup_k3s.sh
        sudo scripts/setup_k3s.sh
    else
        print_warning "Skipping K3s installation"
    fi
fi

# Set up Ollama
print_header "Ollama Setup"

if command -v ollama &> /dev/null; then
    print_success "Ollama is already installed"
else
    print_warning "Ollama not found"
    read -p "Install Ollama and download models? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        chmod +x scripts/setup_ollama.sh
        scripts/setup_ollama.sh
    else
        print_warning "Skipping Ollama installation"
    fi
fi

# Install Python dependencies
print_header "Python Environment Setup"

echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Created virtual environment"
fi

source venv/bin/activate

echo "Installing shared dependencies..."
pip install -q --upgrade pip
pip install -q pyyaml pydantic httpx fastapi uvicorn pytest pytest-cov pytest-asyncio

print_success "Python dependencies installed"

# Deploy Kubernetes infrastructure
print_header "Kubernetes Infrastructure Deployment"

if command -v kubectl &> /dev/null; then
    echo "Deploying base infrastructure..."

    # Create namespace
    kubectl create namespace ashiorid --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true

    # Apply base infrastructure
    if [ -d "k8s/base" ]; then
        kubectl apply -k k8s/base/ || print_warning "Some infrastructure components may not be ready yet"
        print_success "Base infrastructure deployed"
    else
        print_warning "k8s/base directory not found, skipping infrastructure deployment"
    fi

    # Apply monitoring
    if [ -d "k8s/monitoring" ]; then
        kubectl apply -k k8s/monitoring/ || print_warning "Monitoring components may not be ready yet"
        print_success "Monitoring stack deployed"
    fi

    echo ""
    echo "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod --all -n ashiorid --timeout=300s || print_warning "Some pods may still be starting"

else
    print_warning "kubectl not found, skipping Kubernetes deployment"
fi

# Install Tilt (optional)
print_header "Development Tools"

if ! command -v tilt &> /dev/null; then
    read -p "Install Tilt for hot-reload development? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -fsSL https://raw.githubusercontent.com/tilt-dev/tilt/master/scripts/install.sh | bash
        print_success "Tilt installed"
    fi
else
    print_success "Tilt is already installed"
fi

# Create directories for persistent data
print_header "Creating Data Directories"

mkdir -p logs backups data

print_success "Data directories created"

# Final summary
print_header "🎉 Bootstrap Complete!"

echo "✅ Environment is ready for development!"
echo ""
echo "📋 What's been set up:"
echo "  • K3s cluster (if installed)"
echo "  • Ollama with required models (if installed)"
echo "  • Python virtual environment"
echo "  • Kubernetes infrastructure (if kubectl available)"
echo "  • Monitoring stack (Prometheus + Grafana)"
echo ""
echo "🚀 Next steps:"
echo ""
echo "  1. Activate Python environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Start development with Tilt:"
echo "     tilt up"
echo ""
echo "  3. Or run individual services:"
echo "     cd llm-proxy-service"
echo "     uvicorn src.main:app --reload --port 8001"
echo ""
echo "  4. Monitor with CLI dashboard:"
echo "     python cli-dashboard/dashboard.py"
echo ""
echo "  5. Check K8s resources:"
echo "     kubectl get all -n ashiorid"
echo ""
echo "📚 Documentation:"
echo "  • Architecture: docs/architecture.md"
echo "  • Development: docs/development-guide.md"
echo "  • Deployment: docs/deployment-guide.md"
echo ""
echo -e "${GREEN}Happy building! 🌍⚔️🤖${NC}"
echo ""
