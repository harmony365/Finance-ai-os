#!/usr/bin/env bash
set -euo pipefail
printf '\n== Finance Core health ==\n'
curl -fsS http://127.0.0.1:8088/health | python3 -m json.tool
printf '\n== AR summary ==\n'
curl -fsS http://127.0.0.1:8088/api/ar-summary | python3 -m json.tool
printf '\n== DSO ==\n'
curl -fsS http://127.0.0.1:8088/api/dso | python3 -m json.tool
printf '\n== MCP health ==\n'
curl -fsS http://127.0.0.1:8090/health | python3 -m json.tool
printf '\n== MCP endpoint headers ==\n'
curl -sS -o /dev/null -D- http://127.0.0.1:8090/mcp | head -15 || true
