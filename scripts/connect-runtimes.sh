#!/usr/bin/env bash
set -euo pipefail
MCP_CONTAINER="${MCP_CONTAINER:-$(docker ps --filter 'name=finance-mcp' --format '{{.Names}}' | head -1)}"
: "${MCP_CONTAINER:?Finance MCP container not found}"
NETWORK="${FINANCE_NETWORK:-$(docker inspect "$MCP_CONTAINER" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{"\n"}}{{end}}' | head -1)}"
: "${NETWORK:?Finance network not found}"
for runtime in openclaw hermes; do
  if docker inspect "$runtime" >/dev/null 2>&1; then
    docker network connect "$NETWORK" "$runtime" 2>/dev/null || true
    echo "connected $runtime -> $NETWORK"
    docker exec "$runtime" sh -lc "(wget -qO- http://finance-mcp:8090/health || curl -fsS http://finance-mcp:8090/health || true)" || true
  else
    echo "skip: container $runtime not found"
  fi
done
echo "MCP URL inside shared network: http://finance-mcp:8090/mcp"
