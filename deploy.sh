#!/bin/bash
set -e

# Configuration
IMAGE_NAME="plantopo-tiles"
APP_DIR="/home/app/plantopo-tiles"
CONTAINER_FILE="infra/plantopo-tiles.container"
SERVICE_NAME="plantopo-tiles.service"
PORT=3010
ENV_FILE="$HOME/.config/plantopo-tiles/env"

# Set up environment for systemd user services
# Required when using 'sudo su app' instead of proper login
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"

echo "=== Plantopo Tiles Deployment ==="
echo "Working directory: $APP_DIR"

# Check if lingering is enabled
if ! loginctl show-user "$(whoami)" -p Linger | grep -q "Linger=yes"; then
    echo "ERROR: User lingering is not enabled for $(whoami)"
    echo "Run this as a sudoer user: sudo loginctl enable-linger $(whoami)"
    exit 1
fi

# Check env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: Environment file not found: $ENV_FILE"
    echo "Create it with the required environment variables:"
    echo "  OS_API_KEY=..."
    echo "  TILES_MY_PERSONALB_ACCESS_KEY_ID=..."
    echo "  TILES_MY_PERSONALB_SECRET_ACCESS_KEY=..."
    exit 1
fi

# Navigate to app directory
cd "$APP_DIR"

# Pull latest code
echo "Pulling latest code..."
git pull

# Build the image
echo "Building container image..."
podman build -t "$IMAGE_NAME:latest" .

# Copy container file to systemd user directory
echo "Installing systemd service..."
mkdir -p ~/.config/containers/systemd
cp "$CONTAINER_FILE" ~/.config/containers/systemd/

# Reload systemd to regenerate service from .container file
echo "Reloading systemd daemon..."
systemctl --user daemon-reload

# Stop existing service if running
echo "Stopping existing service..."
systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true

# Start the service
echo "Starting service..."
systemctl --user start "$SERVICE_NAME"

# Health check
echo "Waiting for service to become healthy..."
healthy=false
for i in $(seq 1 30); do
    if curl -sf "http://localhost:$PORT" >/dev/null 2>&1; then
        healthy=true
        break
    fi
    sleep 1
done

if [ "$healthy" = true ]; then
    echo "Service is healthy (responded on port $PORT)"
else
    echo "WARNING: Service did not respond on port $PORT within 30s"
    echo "Check logs with: journalctl --user -u $SERVICE_NAME -f"
fi

# Show status
echo ""
echo "=== Deployment Complete ==="
systemctl --user status "$SERVICE_NAME" --no-pager
