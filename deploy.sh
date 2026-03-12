#!/bin/bash
# YTIP Deployment Script — EC2 Mumbai
# Usage: ./deploy.sh [--skip-seed]

set -euo pipefail

# Configuration
EC2_HOST="13.206.50.251"
EC2_USER="ec2-user"
SSH_KEY="$HOME/.ssh/fie-key.pem"
REMOTE_DIR="/home/ec2-user/ytip"
CONTAINER_NAME="ytip-backend"
IMAGE_NAME="ytip-backend:latest"
ENV_FILE="/home/ec2-user/ytip.env"
PORT=8001
SKIP_SEED=false

if [[ "${1:-}" == "--skip-seed" ]]; then
    SKIP_SEED=true
fi

SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=40 $EC2_USER@$EC2_HOST"
SCP_CMD="scp -i $SSH_KEY -o StrictHostKeyChecking=no"

echo "=== YTIP Deployment ==="

# Step 1: Copy backend code to EC2
echo "[1/6] Copying backend code to EC2..."
$SSH_CMD "mkdir -p $REMOTE_DIR"
$SCP_CMD -r backend/ "$EC2_USER@$EC2_HOST:$REMOTE_DIR/backend/"
$SCP_CMD -r database/ "$EC2_USER@$EC2_HOST:$REMOTE_DIR/database/"
echo "  Done."

# Step 2: Check env file exists on EC2
echo "[2/6] Verifying env file..."
$SSH_CMD "test -f $ENV_FILE" || {
    echo "  ERROR: $ENV_FILE not found on EC2."
    echo "  Create it first with DATABASE_URL, ANTHROPIC_API_KEY, etc."
    exit 1
}
echo "  Done."

# Step 3: Build Docker image on EC2
echo "[3/6] Building Docker image on EC2..."
$SSH_CMD "cd $REMOTE_DIR/backend && docker build -t $IMAGE_NAME ."
echo "  Done."

# Step 4: Stop old container (if running)
echo "[4/6] Stopping old container..."
$SSH_CMD "docker stop $CONTAINER_NAME 2>/dev/null && docker rm $CONTAINER_NAME 2>/dev/null || true"
echo "  Done."

# Step 5: Start new container
echo "[5/6] Starting new container on port $PORT..."
$SSH_CMD "docker run -d \
    --name $CONTAINER_NAME \
    --env-file $ENV_FILE \
    -p $PORT:$PORT \
    --restart unless-stopped \
    --memory 256m \
    $IMAGE_NAME"
echo "  Done."

# Step 5b: Run seed data (optional)
if [[ "$SKIP_SEED" == "false" ]]; then
    echo "[5b] Running seed_data.py..."
    $SCP_CMD backend/seed_data.py "$EC2_USER@$EC2_HOST:$REMOTE_DIR/seed_data.py"
    $SSH_CMD "docker exec $CONTAINER_NAME pip install --no-cache-dir -q faker 2>/dev/null || true"
    $SSH_CMD "docker cp $REMOTE_DIR/seed_data.py $CONTAINER_NAME:/app/seed_data.py && \
              docker exec $CONTAINER_NAME python seed_data.py"
    echo "  Done."
fi

# Step 6: Verify health
echo "[6/6] Verifying health endpoint..."
sleep 3
HEALTH=$(curl -sf "http://$EC2_HOST:$PORT/api/health" 2>/dev/null || echo "FAILED")
if echo "$HEALTH" | grep -q "ok"; then
    echo "  Health check passed: $HEALTH"
else
    echo "  Health check FAILED. Checking container logs..."
    $SSH_CMD "docker logs --tail 30 $CONTAINER_NAME"
    exit 1
fi

echo ""
echo "=== Deployment Complete ==="
echo "  Backend: http://$EC2_HOST:$PORT"
echo "  Health:  http://$EC2_HOST:$PORT/api/health"
echo ""
echo "  Verify other services:"
echo "    FIE2:      curl http://$EC2_HOST:8000/health"
echo "    MF-Engine: curl http://$EC2_HOST:8080/health"
