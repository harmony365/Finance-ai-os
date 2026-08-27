# OpenClaw integration

1. Put `finance-mcp` and the `openclaw` container on the same Docker network (`scripts/connect-runtimes.sh`).
2. Load this runtime's `mcp.json` and `skills/finance-os/SKILL.md` using your OpenClaw plugin/skill deployment method.
3. MCP URL from the shared Docker network: `http://finance-mcp:8090/mcp`.
4. Keep Finance AI OS in `SHADOW` and `READ_ONLY=true` for the pilot.
5. Validate by asking OpenClaw: “Dame el AR, DSO, aging y top 5 vencidos; no ejecutes ninguna acción.”
