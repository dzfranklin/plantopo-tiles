#!/usr/bin/env bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Starting plantopo-tiles test suite"
echo "=========================================="

# Start prod-test service in background
echo -e "\n${YELLOW}Starting prod test server...${NC}"
docker-compose up --build -d prod-test

# Give it a moment to start
sleep 2

# Function to cleanup
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    docker-compose down prod-test test
}
trap cleanup EXIT

# Run integration tests
echo -e "\n${YELLOW}Running integration tests...${NC}"
TEST_EXIT_CODE=0
docker-compose run --rm test || TEST_EXIT_CODE=$?

# Fetch all logs (not streaming - captures full history reliably)
echo -e "\n${YELLOW}Checking logs for warnings and errors...${NC}"
WARNINGS_FOUND=0

FILTERED_WARNINGS=$(docker-compose logs prod-test 2>&1 | grep -iE "WARNING|ERROR" | grep -v "Application has demo page enabled" || true)

if [ -n "$FILTERED_WARNINGS" ]; then
    echo -e "${RED}✗ Warnings/errors found in logs:${NC}"
    echo "$FILTERED_WARNINGS" | while read -r line; do
        echo -e "  ${RED}$line${NC}"
    done
    WARNINGS_FOUND=1
else
    echo -e "${GREEN}✓ No warnings or errors found in logs${NC}"
fi

# Final result
echo -e "\n=========================================="
if [ $TEST_EXIT_CODE -eq 0 ] && [ $WARNINGS_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo "=========================================="
    exit 0
else
    if [ $TEST_EXIT_CODE -ne 0 ]; then
        echo -e "${RED}✗ Integration tests failed${NC}"
    fi
    if [ $WARNINGS_FOUND -eq 1 ]; then
        echo -e "${RED}✗ Configuration warnings/errors detected${NC}"
    fi
    echo "=========================================="
    exit 1
fi
