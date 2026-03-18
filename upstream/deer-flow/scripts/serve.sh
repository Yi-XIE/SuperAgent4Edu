#!/usr/bin/env bash
#
# start.sh - Start all DeerFlow development services
#
# Must be run from the repo root directory.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export DEER_FLOW_HOME="${DEER_FLOW_HOME:-$REPO_ROOT/backend/.deer-flow}"

if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.env"
    set +a
fi

if [ -f "$REPO_ROOT/backend/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO_ROOT/backend/.env"
    set +a
fi

# ── Argument parsing ─────────────────────────────────────────────────────────

DEV_MODE=true
for arg in "$@"; do
    case "$arg" in
        --dev)  DEV_MODE=true ;;
        --prod) DEV_MODE=false ;;
        *) echo "Unknown argument: $arg"; echo "Usage: $0 [--dev|--prod]"; exit 1 ;;
    esac
done

if $DEV_MODE; then
    FRONTEND_CMD="pnpm run dev"
else
    FRONTEND_CMD="env BETTER_AUTH_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(16))') pnpm run preview"
fi

if command -v uv >/dev/null 2>&1; then
    UV_RUN_CMD=(uv run)
elif python3 -c "import uv" >/dev/null 2>&1; then
    UV_RUN_CMD=(python3 -m uv run)
else
    UV_RUN_CMD=()
fi

if command -v nginx >/dev/null 2>&1; then
    HAS_NGINX=true
else
    HAS_NGINX=false
fi

# ── Stop existing services ────────────────────────────────────────────────────

echo "Stopping existing services if any..."
pkill -f "langgraph dev" 2>/dev/null || true
pkill -f "uvicorn src.gateway.app:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
nginx -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" -s quit 2>/dev/null || true
sleep 1
pkill -9 nginx 2>/dev/null || true
killall -9 nginx 2>/dev/null || true
./scripts/cleanup-containers.sh deer-flow-sandbox 2>/dev/null || true
sleep 1

# ── Banner ────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo "  Starting DeerFlow Development Server"
echo "=========================================="
echo ""
if $DEV_MODE; then
    echo "  Mode: DEV  (hot-reload enabled)"
    echo "  Tip:  run \`make start\` in production mode"
else
    echo "  Mode: PROD (hot-reload disabled)"
    echo "  Tip:  run \`make dev\` to start in development mode"
fi
echo ""
echo "Services starting up..."
echo "  → Backend: LangGraph + Gateway"
echo "  → Frontend: Next.js"
if $HAS_NGINX; then
    echo "  → Nginx: Reverse Proxy"
else
    echo "  → Nginx: not installed, using direct frontend/backend mode"
fi
echo ""

# ── Config check ─────────────────────────────────────────────────────────────

if ! { \
        [ -n "$DEER_FLOW_CONFIG_PATH" ] && [ -f "$DEER_FLOW_CONFIG_PATH" ] || \
        [ -f backend/config.yaml ] || \
        [ -f config.yaml ]; \
    }; then
    echo "✗ No DeerFlow config file found."
    echo "  Checked these locations:"
    echo "    - $DEER_FLOW_CONFIG_PATH (when DEER_FLOW_CONFIG_PATH is set)"
    echo "    - backend/config.yaml"
    echo "    - ./config.yaml"
    echo ""
    echo "  Run 'make config' from the repo root to generate ./config.yaml, then set required model API keys in .env or your config file."
    exit 1
fi

echo "Syncing education demo assets..."
"$REPO_ROOT/scripts/sync-education-assets.sh"

# ── Cleanup trap ─────────────────────────────────────────────────────────────

cleanup() {
    trap - INT TERM
    echo ""
    echo "Shutting down services..."
    pkill -f "langgraph dev" 2>/dev/null || true
    pkill -f "uvicorn src.gateway.app:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "next start" 2>/dev/null || true
    # Kill nginx using the captured PID first (most reliable),
    # then fall back to pkill/killall for any stray nginx workers.
    if $HAS_NGINX; then
        if [ -n "${NGINX_PID:-}" ] && kill -0 "$NGINX_PID" 2>/dev/null; then
            kill -TERM "$NGINX_PID" 2>/dev/null || true
            sleep 1
            kill -9 "$NGINX_PID" 2>/dev/null || true
        fi
        pkill -9 nginx 2>/dev/null || true
        killall -9 nginx 2>/dev/null || true
    fi
    echo "Cleaning up sandbox containers..."
    ./scripts/cleanup-containers.sh deer-flow-sandbox 2>/dev/null || true
    echo "✓ All services stopped"
    exit 0
}
trap cleanup INT TERM

# ── Start services ────────────────────────────────────────────────────────────

mkdir -p logs

if $DEV_MODE; then
    LANGGRAPH_EXTRA_FLAGS=""
    GATEWAY_EXTRA_FLAGS="--reload --reload-include='*.yaml' --reload-include='.env'"
else
    LANGGRAPH_EXTRA_FLAGS="--no-reload"
    GATEWAY_EXTRA_FLAGS=""
fi

echo "Starting LangGraph server..."
if [ ${#UV_RUN_CMD[@]} -gt 0 ]; then
    (cd backend && NO_COLOR=1 "${UV_RUN_CMD[@]}" langgraph dev --no-browser --allow-blocking $LANGGRAPH_EXTRA_FLAGS > ../logs/langgraph.log 2>&1) &
elif [ -x backend/.venv/bin/langgraph ]; then
    (cd backend && NO_COLOR=1 .venv/bin/langgraph dev --no-browser --allow-blocking $LANGGRAPH_EXTRA_FLAGS > ../logs/langgraph.log 2>&1) &
else
    echo "✗ Cannot start LangGraph: neither uv nor backend/.venv/bin/langgraph is available."
    exit 1
fi
./scripts/wait-for-port.sh 2024 60 "LangGraph" || {
    echo "  See logs/langgraph.log for details"
    tail -20 logs/langgraph.log
    cleanup
}
echo "✓ LangGraph server started on localhost:2024"

echo "Starting Gateway API..."
if [ ${#UV_RUN_CMD[@]} -gt 0 ]; then
    (cd backend && "${UV_RUN_CMD[@]}" uvicorn src.gateway.app:app --host 0.0.0.0 --port 8001 $GATEWAY_EXTRA_FLAGS > ../logs/gateway.log 2>&1) &
elif [ -x backend/.venv/bin/uvicorn ]; then
    (cd backend && .venv/bin/uvicorn src.gateway.app:app --host 0.0.0.0 --port 8001 $GATEWAY_EXTRA_FLAGS > ../logs/gateway.log 2>&1) &
else
    echo "✗ Cannot start Gateway API: neither uv nor backend/.venv/bin/uvicorn is available."
    exit 1
fi
./scripts/wait-for-port.sh 8001 30 "Gateway API" || {
    echo "✗ Gateway API failed to start. Last log output:"
    tail -60 logs/gateway.log
    echo ""
    echo "Likely configuration errors:"
    grep -E "Failed to load configuration|Environment variable .* not found|config\.yaml.*not found" logs/gateway.log | tail -5 || true
    cleanup
}
echo "✓ Gateway API started on localhost:8001"

echo "Starting Frontend..."
(cd frontend && $FRONTEND_CMD > ../logs/frontend.log 2>&1) &
./scripts/wait-for-port.sh 3000 120 "Frontend" || {
    echo "  See logs/frontend.log for details"
    tail -20 logs/frontend.log
    cleanup
}
echo "✓ Frontend started on localhost:3000"

if $HAS_NGINX; then
    echo "Starting Nginx reverse proxy..."
    nginx -g 'daemon off;' -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" > logs/nginx.log 2>&1 &
    NGINX_PID=$!
    ./scripts/wait-for-port.sh 2026 10 "Nginx" || {
        echo "  See logs/nginx.log for details"
        tail -10 logs/nginx.log
        cleanup
    }
    echo "✓ Nginx started on localhost:2026"
fi

# ── Ready ─────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
if $DEV_MODE; then
    echo "  ✓ DeerFlow development server is running!"
else
    echo "  ✓ DeerFlow production server is running!"
fi
echo "=========================================="
echo ""
if $HAS_NGINX; then
    echo "  🌐 Application: http://localhost:2026"
    echo "  📡 API Gateway: http://localhost:2026/api/*"
    echo "  🤖 LangGraph:   http://localhost:2026/api/langgraph/*"
else
    echo "  🌐 Application: http://localhost:3000"
    echo "  📡 API Gateway: http://localhost:8001/api/*"
    echo "  🤖 LangGraph:   http://localhost:2024"
fi
echo ""
echo "  📋 Logs:"
echo "     - LangGraph: logs/langgraph.log"
echo "     - Gateway:   logs/gateway.log"
echo "     - Frontend:  logs/frontend.log"
if $HAS_NGINX; then
    echo "     - Nginx:     logs/nginx.log"
fi
echo ""
echo "Press Ctrl+C to stop all services"

wait
