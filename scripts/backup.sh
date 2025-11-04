#!/bin/bash
set -e

# =================================================================
# Ashiorid AI Manager - Backup Script
# =================================================================
# This script backs up all critical data from the Ashiorid system
# Run with: ./scripts/backup.sh

echo "💾 Starting Ashiorid AI Manager backup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ashiorid_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# K8s namespace
NAMESPACE="ashiorid"

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

# Create backup directory
mkdir -p "${BACKUP_PATH}"

print_header "Backup Configuration"
echo "Backup location: ${BACKUP_PATH}"
echo "Timestamp: ${TIMESTAMP}"
echo "Namespace: ${NAMESPACE}"
echo ""

# Backup PostgreSQL
print_header "Backing up PostgreSQL"

if kubectl get pods -n "${NAMESPACE}" | grep -q postgres; then
    POSTGRES_POD=$(kubectl get pods -n "${NAMESPACE}" -l app=postgres -o jsonpath='{.items[0].metadata.name}')

    echo "Dumping PostgreSQL database..."
    kubectl exec -n "${NAMESPACE}" "${POSTGRES_POD}" -- pg_dumpall -U ashiorid_user > "${BACKUP_PATH}/postgres_dump.sql"

    if [ -f "${BACKUP_PATH}/postgres_dump.sql" ]; then
        print_success "PostgreSQL backup completed ($(du -h "${BACKUP_PATH}/postgres_dump.sql" | cut -f1))"
    else
        print_error "PostgreSQL backup failed"
    fi
else
    print_warning "PostgreSQL pod not found, skipping..."
fi

# Backup Qdrant
print_header "Backing up Qdrant"

if kubectl get pods -n "${NAMESPACE}" | grep -q qdrant; then
    QDRANT_POD=$(kubectl get pods -n "${NAMESPACE}" -l app=qdrant -o jsonpath='{.items[0].metadata.name}')

    echo "Creating Qdrant snapshot..."
    # Create snapshot via API
    QDRANT_URL="http://localhost:6333"

    # Port-forward to Qdrant
    kubectl port-forward -n "${NAMESPACE}" "${QDRANT_POD}" 6333:6333 &
    PF_PID=$!
    sleep 3

    # Create snapshot for each collection
    COLLECTIONS=$(curl -s "${QDRANT_URL}/collections" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "")

    if [ -n "$COLLECTIONS" ]; then
        mkdir -p "${BACKUP_PATH}/qdrant"
        for collection in $COLLECTIONS; do
            echo "  Snapshotting collection: $collection"
            curl -s -X POST "${QDRANT_URL}/collections/${collection}/snapshots" > /dev/null || true
        done

        # Copy snapshots
        kubectl cp -n "${NAMESPACE}" "${QDRANT_POD}:/qdrant/storage/snapshots" "${BACKUP_PATH}/qdrant/" 2>/dev/null || print_warning "Could not copy Qdrant snapshots"

        print_success "Qdrant backup completed"
    else
        print_warning "No Qdrant collections found"
    fi

    # Kill port-forward
    kill $PF_PID 2>/dev/null || true
else
    print_warning "Qdrant pod not found, skipping..."
fi

# Backup Redis
print_header "Backing up Redis"

if kubectl get pods -n "${NAMESPACE}" | grep -q redis; then
    REDIS_POD=$(kubectl get pods -n "${NAMESPACE}" -l app=redis -o jsonpath='{.items[0].metadata.name}')

    echo "Triggering Redis SAVE..."
    kubectl exec -n "${NAMESPACE}" "${REDIS_POD}" -- redis-cli SAVE

    echo "Copying Redis dump..."
    kubectl cp -n "${NAMESPACE}" "${REDIS_POD}:/data/dump.rdb" "${BACKUP_PATH}/redis_dump.rdb" 2>/dev/null || print_warning "Could not copy Redis dump"

    if [ -f "${BACKUP_PATH}/redis_dump.rdb" ]; then
        print_success "Redis backup completed ($(du -h "${BACKUP_PATH}/redis_dump.rdb" | cut -f1))"
    else
        print_warning "Redis dump not found"
    fi
else
    print_warning "Redis pod not found, skipping..."
fi

# Backup Kubernetes configurations
print_header "Backing up Kubernetes Configurations"

mkdir -p "${BACKUP_PATH}/k8s"

echo "Exporting deployments..."
kubectl get deployments -n "${NAMESPACE}" -o yaml > "${BACKUP_PATH}/k8s/deployments.yaml" 2>/dev/null || true

echo "Exporting services..."
kubectl get services -n "${NAMESPACE}" -o yaml > "${BACKUP_PATH}/k8s/services.yaml" 2>/dev/null || true

echo "Exporting configmaps..."
kubectl get configmaps -n "${NAMESPACE}" -o yaml > "${BACKUP_PATH}/k8s/configmaps.yaml" 2>/dev/null || true

echo "Exporting secrets..."
kubectl get secrets -n "${NAMESPACE}" -o yaml > "${BACKUP_PATH}/k8s/secrets.yaml" 2>/dev/null || true

echo "Exporting persistent volume claims..."
kubectl get pvc -n "${NAMESPACE}" -o yaml > "${BACKUP_PATH}/k8s/pvcs.yaml" 2>/dev/null || true

print_success "Kubernetes configurations backed up"

# Backup logs
print_header "Backing up Logs"

if [ -d "logs" ]; then
    mkdir -p "${BACKUP_PATH}/logs"
    cp -r logs/* "${BACKUP_PATH}/logs/" 2>/dev/null || print_warning "No logs found"
    print_success "Logs backed up"
else
    print_warning "Logs directory not found"
fi

# Create metadata file
print_header "Creating Backup Metadata"

cat > "${BACKUP_PATH}/metadata.txt" <<EOF
Ashiorid AI Manager Backup
==========================
Timestamp: ${TIMESTAMP}
Date: $(date)
Hostname: $(hostname)
Namespace: ${NAMESPACE}

Backed up components:
- PostgreSQL database
- Qdrant vector database
- Redis cache
- Kubernetes configurations
- Application logs

Restore instructions:
1. Run scripts/restore.sh ${BACKUP_NAME}
2. Or manually restore individual components

EOF

print_success "Metadata created"

# Compress backup
print_header "Compressing Backup"

cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"

if [ -f "${BACKUP_NAME}.tar.gz" ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
    print_success "Backup compressed: ${BACKUP_SIZE}"

    # Remove uncompressed directory
    rm -rf "${BACKUP_NAME}"

    echo ""
    print_success "Backup saved to: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
else
    print_error "Compression failed"
    exit 1
fi

cd - > /dev/null

# Cleanup old backups (keep last 7 days)
print_header "Cleaning Up Old Backups"

find "${BACKUP_DIR}" -name "ashiorid_backup_*.tar.gz" -mtime +7 -delete
OLD_COUNT=$(find "${BACKUP_DIR}" -name "ashiorid_backup_*.tar.gz" | wc -l)

print_success "Kept ${OLD_COUNT} recent backups"

# Final summary
print_header "✅ Backup Complete!"

echo "Backup file: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "Size: ${BACKUP_SIZE}"
echo ""
echo "To restore this backup:"
echo "  ./scripts/restore.sh ${BACKUP_NAME}"
echo ""
echo "💡 Tip: Store backups offsite for disaster recovery!"
echo ""
