#!/usr/bin/env bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

LOG_FILE=$(mktemp)
trap "rm -f $LOG_FILE" EXIT

echo "=========================================="
echo "Starting plantopo-tiles test suite"
echo "=========================================="

# Start dev-test service in background and capture logs
echo -e "\n${YELLOW}Starting test server on port 3011...${NC}"
docker-compose up --build -d dev-test

# Give it a moment to start
sleep 2

# Start capturing logs in background
docker-compose logs -f dev-test > "$LOG_FILE" 2>&1 &
LOGS_PID=$!

# Function to cleanup
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    kill $LOGS_PID 2>/dev/null || true
    docker-compose down dev-test test
}
trap cleanup EXIT

# Run integration tests
echo -e "\n${YELLOW}Running integration tests...${NC}"
TEST_EXIT_CODE=0
docker-compose run --rm test || TEST_EXIT_CODE=$?

# Wait a moment for logs to flush
sleep 2
kill $LOGS_PID 2>/dev/null || true

# Check logs for warnings (excluding demo page warning)
echo -e "\n${YELLOW}Checking logs for warnings...${NC}"
WARNINGS_FOUND=0

FILTERED_WARNINGS=$(grep "WARNING" "$LOG_FILE" | grep -v "Application has demo page enabled" || true)

if [ -n "$FILTERED_WARNINGS" ]; then
    echo -e "${RED}✗ Warnings found in logs:${NC}"
    echo "$FILTERED_WARNINGS" | while read -r line; do
        echo -e "  ${RED}$line${NC}"
    done
    WARNINGS_FOUND=1
else
    echo -e "${GREEN}✓ No warnings found in logs${NC}"
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
        echo -e "${RED}✗ Configuration warnings detected${NC}"
    fi
    echo "=========================================="
    exit 1
fi
