import os, httpx
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

mcp = FastMCP("Finance AI OS")
CORE = os.getenv("FINANCE_CORE_URL", "http://finance-core:8088")


def get(path, params=None):
    with httpx.Client(timeout=30) as c:
        r = c.get(CORE + path, params=params)
        r.raise_for_status()
        return r.json()


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request):
    try:
        core = get("/health")
        return JSONResponse({"ok": True, "service": "finance-mcp", "version": "2.5.0", "core": core})
    except Exception as e:
        return JSONResponse({"ok": False, "service": "finance-mcp", "error": str(e)[:250]}, status_code=503)


@mcp.tool()
def get_ar_summary():
    """Resumen real de cuentas por cobrar desde Odoo. Solo lectura."""
    return get("/api/ar-summary")


@mcp.tool()
def get_dso():
    """DSO determinista calculado con AR abierto y ventas facturadas de los últimos 365 días."""
    return get("/api/dso")


@mcp.tool()
def get_aging():
    """Aging real de AR: corriente, 1-30, 31-60, 61-90 y 90+ días."""
    return get("/api/aging")


@mcp.tool()
def get_top_overdue_customers(limit: int = 10):
    """Clientes con mayor saldo vencido. No ejecuta acciones."""
    return get("/api/top-overdue", {"limit": limit})


@mcp.tool()
def get_cash_risk():
    """Riesgo de caja basado en antigüedad de AR, concentración y pool de cobro priorizable."""
    return get("/api/cash-risk")


@mcp.tool()
def explain_dso_change(previous_dso: float | None = None):
    """Explica los drivers del DSO y, si se aporta previous_dso, calcula el delta."""
    params = {} if previous_dso is None else {"previous_dso": previous_dso}
    return get("/api/dso-explain", params)


@mcp.tool()
def finance_alerts():
    """Alertas financieras priorizadas derivadas de Odoo. SHADOW: no ejecuta acciones."""
    return get("/api/alerts")


@mcp.tool()
def finance_customer_profile():
    """Perfil del piloto, ERP y modo de operación."""
    return get("/api/customer")


@mcp.tool()
def finance_roi(annual_credit_sales: float, dso_reduction_days: float = 4, hours_week_saved: float = 12, hourly_cost: float = 35):
    """Indicador de working capital y productividad potencial. No es beneficio contable."""
    return get("/api/roi", {
        "annual_credit_sales": annual_credit_sales,
        "dso_reduction_days": dso_reduction_days,
        "hours_week_saved": hours_week_saved,
        "hourly_cost": hourly_cost,
    })


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8090")))
