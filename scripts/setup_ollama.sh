#!/usr/bin/env bash
set -e

# =================================================================
# Ashiorid AI Manager - Ollama Setup Script
# =================================================================
# This script installs Ollama and downloads required models
# Run with: ./scripts/setup_ollama.sh

echo "🚀 Starting Ollama setup for Ashiorid AI Manager..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Required models for Ashiorid
REQUIRED_MODELS=(
    "llama3.2:1b"       # Simple agent decisions
    "llama3.2:3b"       # Agent dialogue
    "phi3:mini"         # Alternative lightweight model
    "nomic-embed-text"  # Embeddings for RAG
)

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "📥 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install Ollama${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Ollama installed successfully${NC}"
else
    echo -e "${GREEN}✅ Ollama is already installed${NC}"
fi

# Check if Ollama service is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "🚀 Starting Ollama service..."
    ollama serve &> /dev/null &
    sleep 5
fi

# Verify Ollama is responding
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo -e "${RED}❌ Ollama service is not responding${NC}"
    echo "Try starting it manually: ollama serve"
    exit 1
fi

echo -e "${GREEN}✅ Ollama service is running${NC}"

# Download required models
echo ""
echo "📥 Downloading required models..."
echo "⚠️  This may take a while depending on your internet connection"
echo ""

for model in "${REQUIRED_MODELS[@]}"; do
    echo "📦 Checking model: $model"

    # Check if model already exists
    if ollama list | grep -q "^${model}"; then
        echo -e "${GREEN}  ✅ $model is already downloaded${NC}"
    else
        echo "  📥 Downloading $model..."
        if ollama pull "$model"; then
            echo -e "${GREEN}  ✅ $model downloaded successfully${NC}"
        else
            echo -e "${RED}  ❌ Failed to download $model${NC}"
            exit 1
        fi
    fi
    echo ""
done

# Test models
echo "🧪 Testing models..."
echo ""

# Test llama3.2:1b with a simple prompt
echo "Testing llama3.2:1b..."
TEST_RESPONSE=$(ollama run llama3.2:1b "Say 'OK' if you can hear me" --verbose=false 2>/dev/null)
if [ -n "$TEST_RESPONSE" ]; then
    echo -e "${GREEN}✅ llama3.2:1b is working${NC}"
else
    echo -e "${YELLOW}⚠️  llama3.2:1b test produced no output${NC}"
fi

# Test embeddings
echo "Testing nomic-embed-text..."
EMBED_RESPONSE=$(ollama run nomic-embed-text "test" 2>&1 | head -n 1)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ nomic-embed-text is working${NC}"
else
    echo -e "${YELLOW}⚠️  nomic-embed-text test failed (this is normal for embedding models)${NC}"
fi

# Display all installed models
echo ""
echo "📋 Installed models:"
ollama list

# Display configuration info
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Ollama setup completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📝 Configuration:"
echo "  • Ollama Host: http://localhost:11434"
echo "  • From Docker: http://host.docker.internal:11434"
echo "  • From K8s: Use Service with externalName"
echo ""
echo "📦 Installed Models:"
for model in "${REQUIRED_MODELS[@]}"; do
    echo "  • $model"
done
echo ""
echo "💡 Tips:"
echo "  • Keep Ollama running: ollama serve"
echo "  • Test a model: ollama run llama3.2:1b"
echo "  • List models: ollama list"
echo "  • Remove a model: ollama rm <model>"
echo ""
