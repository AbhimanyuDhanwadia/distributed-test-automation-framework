#!/bin/bash

################################################################################
# DTAF Orchestrator Script
# 
# This script automates the deployment and verification of the Distributed
# Test Automation Framework (DTAF) cluster.
#
# Usage: ./run.sh
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}"
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  ____  _____  _    _____ "
echo " |  _ \|_   _|/ \  |  ___|"
echo " | | | | | | / _ \ | |_   "
echo " | |_| | | |/ ___ \|  _|  "
echo " |____/  |_/_/   \_\_|    "
echo ""
echo " Distributed Test Automation Framework"
echo " Orchestrator v1.0"
echo "════════════════════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Step 1: Check if Docker is running
echo -e "${YELLOW}[1/5] Checking Docker status...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Error: Docker is not running!${NC}"
    echo -e "${YELLOW}Please start Docker Desktop and try again.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Step 2: Clean previous state
echo -e "${YELLOW}[2/5] Cleaning previous deployment...${NC}"
docker-compose down -v 2>/dev/null || true
echo -e "${GREEN}✓ Previous state cleaned${NC}"
echo ""

# Step 3: Build and start services
echo -e "${YELLOW}[3/5] Building and starting DTAF cluster...${NC}"
echo -e "${BLUE}This may take a few minutes on first run...${NC}"

# Try with BuildKit first, fallback to legacy builder if it fails
if ! docker-compose up --build -d 2>/dev/null; then
    echo -e "${YELLOW}⚠ BuildKit failed, trying legacy builder...${NC}"
    DOCKER_BUILDKIT=0 docker-compose up --build -d
fi

echo -e "${GREEN}✓ Cluster started${NC}"
echo ""

# Step 4: Wait for services to be healthy
echo -e "${YELLOW}[4/5] Waiting for services to be ready...${NC}"
sleep 5

# Check Redis health
for i in {1..10}; do
    if docker exec dtaf-redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis is healthy${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}✗ Redis failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Check Controller health
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Controller is healthy${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}✗ Controller failed to start${NC}"
        docker-compose logs controller
        exit 1
    fi
    sleep 1
done

# Wait for workers to register
sleep 3
echo ""

# Step 5: Display cluster status
echo -e "${YELLOW}[5/5] Cluster Status${NC}"
echo "────────────────────────────────────────────────────────────────────────────────"
docker-compose ps
echo "────────────────────────────────────────────────────────────────────────────────"
echo ""

# Get metrics
METRICS=$(curl -s http://localhost:8000/metrics)
WORKERS=$(echo $METRICS | grep -o '"workers":[0-9]*' | grep -o '[0-9]*')
PENDING=$(echo $METRICS | grep -o '"pending":[0-9]*' | grep -o '[0-9]*')

echo -e "${GREEN}✓ Cluster Metrics:${NC}"
echo "  • Active Workers: $WORKERS"
echo "  • Pending Tasks: $PENDING"
echo ""

# Success banner
echo -e "${GREEN}"
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  ✓ DTAF Cluster Successfully Deployed!"
echo "════════════════════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Print verification instructions
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo -e "${YELLOW}1. Verify the cluster:${NC}"
echo "   docker run --rm --network dtaf_dtaf-network \\"
echo "     -v \"\$(pwd)/client_test.py:/app/client_test.py\" \\"
echo "     dtaf-app python /app/client_test.py controller redis"
echo ""
echo -e "${YELLOW}2. Submit a test job:${NC}"
echo "   curl -X POST http://localhost:8000/submit \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"test_paths\": [\"tests/dummy_test.py\"]}'"
echo ""
echo -e "${YELLOW}3. Check metrics:${NC}"
echo "   curl http://localhost:8000/metrics"
echo ""
echo -e "${YELLOW}4. View logs:${NC}"
echo "   docker-compose logs -f controller"
echo "   docker-compose logs -f worker"
echo ""
echo -e "${YELLOW}5. Stop the cluster:${NC}"
echo "   docker-compose down"
echo ""
echo -e "${GREEN}Happy Testing! 🚀${NC}"
