import os, xmlrpc.client
from datetime import date, datetime, timedelta
from collections import defaultdict
from functools import lru_cache
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

app = FastAPI(title="Finance AI OS CUSTOMER #001", version="2.5.0")

ODOO_URL = os.getenv("ODOO_URL", "http://odoo:8069").rstrip("/")
ODOO_DB = os.getenv("ODOO_DB", "finance_demo")
ODOO_USER = os.getenv("ODOO_USER", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "")
AS_OF = os.getenv("FINANCE_AS_OF", "")


def today():
    return date.fromisoformat(AS_OF) if AS_OF else date.today()


def d(v):
    if not v:
        return None
    if isinstance(v, date):
        return v
    return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()


def money(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0


class Odoo:
    def __init__(self):
        self.common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common", allow_none=True)
        self.models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object", allow_none=True)
        self.uid = None

    def auth(self):
        if not self.uid:
            self.uid = self.common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if not self.uid:
            raise RuntimeError("Odoo authentication failed")
        return self.uid

    def call(self, model, method, args=None, kwargs=None):
        uid = self.auth()
        return self.models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, method, args or [], kwargs or {})

    def fields(self, model):
        return self.call(model, "fields_get", [], {"attributes": ["type", "string"]})


odoo = Odoo()


def company_info():
    rows = odoo.call("res.company", "search_read", [[]], {"fields": ["name", "currency_id"], "limit": 1})
    if not rows:
        return {"name": "Unknown", "currency": "EUR"}
    cur = rows[0].get("currency_id") or [0, "EUR"]
    return {"name": rows[0]["name"], "currency": cur[1] if isinstance(cur, list) else "EUR"}


def invoice_fields():
    available = odoo.fields("account.move")
    desired = [
        "id", "name", "partner_id", "invoice_date", "invoice_date_due", "amount_total",
        "amount_residual", "payment_state", "state", "currency_id", "ref", "move_type",
    ]
    return [x for x in desired if x in available]


def invoices_365():
    as_of = today()
    since = as_of - timedelta(days=365)
    domain = [
        ["move_type", "=", "out_invoice"], ["state", "=", "posted"],
        ["invoice_date", ">=", since.isoformat()], ["invoice_date", "<=", as_of.isoformat()],
    ]
    return odoo.call("account.move", "search_read", [domain], {"fields": invoice_fields(), "limit": 5000, "order": "invoice_date asc"})


def live_snapshot():
    as_of = today()
    inv = invoices_365()
    open_inv = [x for x in inv if money(x.get("amount_residual")) > 0.005]
    ar = sum(money(x.get("amount_residual")) for x in open_inv)
    sales_365 = sum(money(x.get("amount_total")) for x in inv)
    dso = round(ar / sales_365 * 365, 1) if sales_365 else 0.0

    aging = {"current": 0.0, "1_30": 0.0, "31_60": 0.0, "61_90": 0.0, "90_plus": 0.0}
    overdue = 0.0
    disputes = 0.0
    customer_open = defaultdict(float)
    customer_overdue = defaultdict(float)
    candidates_14d = 0.0

    for x in open_inv:
        residual = money(x.get("amount_residual"))
        partner = x.get("partner_id") or [0, "Unknown"]
        pname = partner[1] if isinstance(partner, list) else str(partner)
        customer_open[pname] += residual
        due = d(x.get("invoice_date_due")) or d(x.get("invoice_date")) or as_of
        dpd = (as_of - due).days
        if dpd <= 0:
            aging["current"] += residual
        elif dpd <= 30:
            aging["1_30"] += residual; overdue += residual; customer_overdue[pname] += residual
        elif dpd <= 60:
            aging["31_60"] += residual; overdue += residual; customer_overdue[pname] += residual
        elif dpd <= 90:
            aging["61_90"] += residual; overdue += residual; customer_overdue[pname] += residual
        else:
            aging["90_plus"] += residual; overdue += residual; customer_overdue[pname] += residual

        # Deterministic candidate pool, not a promise of collection.
        if -14 <= dpd <= 60:
            candidates_14d += residual
        if "[DISPUTE:" in (x.get("ref") or ""):
            disputes += residual

    top_open = sorted(customer_open.items(), key=lambda z: z[1], reverse=True)[:10]
    top_overdue = sorted(customer_overdue.items(), key=lambda z: z[1], reverse=True)[:10]
    concentration_top5 = round(sum(v for _, v in top_open[:5]) / ar * 100, 1) if ar else 0
    info = company_info()

    return {
        "as_of": as_of.isoformat(), "company": info["name"], "currency": info["currency"],
        "invoice_count_365": len(inv), "open_invoice_count": len(open_inv),
        "sales_365": round(sales_365, 2), "ar_open": round(ar, 2), "dso_days": dso,
        "overdue": round(overdue, 2), "aging": {k: round(v, 2) for k, v in aging.items()},
        "disputes": round(disputes, 2), "cash_recoverable_candidates_14d": round(candidates_14d, 2),
        "concentration_top5_pct": concentration_top5,
        "top_open": [{"customer": k, "amount": round(v, 2)} for k, v in top_open],
        "top_overdue": [{"customer": k, "amount": round(v, 2)} for k, v in top_overdue],
        "source": "odoo-live-xmlrpc",
        "source_note": "XML-RPC is used for the current self-hosted Odoo 19 pilot; migrate adapter to JSON-2 before long-term Odoo 22 compatibility.",
    }


def safe_snapshot():
    try:
        return live_snapshot(), None
    except Exception as e:
        return {
            "as_of": today().isoformat(), "company": os.getenv("CUSTOMER_NAME", "CUSTOMER #001"), "currency": "EUR",
            "invoice_count_365": 0, "open_invoice_count": 0, "sales_365": 0, "ar_open": 0,
            "dso_days": 0, "overdue": 0, "aging": {"current":0,"1_30":0,"31_60":0,"61_90":0,"90_plus":0},
            "disputes": 0, "cash_recoverable_candidates_14d": 0, "concentration_top5_pct": 0,
            "top_open": [], "top_overdue": [], "source": "odoo-unavailable"
        }, str(e)[:300]


@app.get("/health")
def health():
    snap, err = safe_snapshot()
    return {"ok": err is None, "service": "finance-ai-os", "version": "2.5.0", "erp": "odoo", "source": snap["source"], "invoices": snap["invoice_count_365"], "error": err}

@app.get("/api/ar-summary")
def ar_summary():
    s, err = safe_snapshot()
    return {"as_of": s["as_of"], "currency": s["currency"], "ar_open": s["ar_open"], "overdue": s["overdue"], "open_invoice_count": s["open_invoice_count"], "disputes": s["disputes"], "source": s["source"], "error": err}

@app.get("/api/dso")
def get_dso():
    s, err = safe_snapshot()
    return {"as_of": s["as_of"], "dso_days": s["dso_days"], "sales_365": s["sales_365"], "ar_open": s["ar_open"], "formula": "AR open / posted customer invoice sales last 365d * 365", "source": s["source"], "error": err}

@app.get("/api/aging")
def get_aging():
    s, err = safe_snapshot()
    return {"as_of": s["as_of"], "currency": s["currency"], "aging": s["aging"], "overdue": s["overdue"], "source": s["source"], "error": err}

@app.get("/api/top-overdue")
def top_overdue(limit: int = Query(10, ge=1, le=50)):
    s, err = safe_snapshot()
    return {"currency": s["currency"], "customers": s["top_overdue"][:limit], "source": s["source"], "error": err}

@app.get("/api/cash-risk")
def cash_risk():
    s, err = safe_snapshot()
    high_risk = s["aging"]["61_90"] + s["aging"]["90_plus"]
    return {
        "as_of": s["as_of"], "currency": s["currency"],
        "overdue": s["overdue"], "high_risk_61_plus": round(high_risk, 2),
        "cash_recoverable_candidates_14d": s["cash_recoverable_candidates_14d"],
        "candidate_method": "Open invoices due within next 14 days or overdue <=60 days; this is a prioritization pool, not a collection forecast.",
        "concentration_top5_pct": s["concentration_top5_pct"], "source": s["source"], "error": err,
    }

@app.get("/api/dso-explain")
def explain_dso_change(previous_dso: float | None = None):
    s, err = safe_snapshot()
    ar = s["ar_open"] or 1
    overdue_pct = round(s["overdue"] / ar * 100, 1) if ar else 0
    old_pct = round((s["aging"]["61_90"] + s["aging"]["90_plus"]) / ar * 100, 1) if ar else 0
    drivers = [
        {"driver": "overdue_share", "value_pct": overdue_pct, "interpretation": "Higher overdue share increases collection cycle pressure."},
        {"driver": "61_plus_share", "value_pct": old_pct, "interpretation": "Older balances are structurally harder to recover."},
        {"driver": "top5_concentration", "value_pct": s["concentration_top5_pct"], "interpretation": "Concentration makes DSO sensitive to a few customers."},
        {"driver": "disputes", "value": s["disputes"], "interpretation": "Invoices tagged as disputes are blocking part of AR."},
    ]
    out = {"current_dso": s["dso_days"], "drivers": drivers, "source": s["source"], "error": err}
    if previous_dso is not None:
        out["previous_dso"] = previous_dso
        out["delta_days"] = round(s["dso_days"] - previous_dso, 1)
    else:
        out["note"] = "Pass previous_dso to calculate an explicit delta; drivers are current-state diagnostics."
    return out

@app.get("/api/metrics")
def metrics():
    s, err = safe_snapshot()
    return {**s, "error": err}

@app.get("/api/alerts")
def alerts():
    s, err = safe_snapshot()
    a = []
    risk61 = s["aging"]["61_90"] + s["aging"]["90_plus"]
    if risk61 > 0:
        a.append({"severity":"critical" if s["aging"]["90_plus"] > 0 else "high", "title":"AR aged 61+ days", "impact":round(risk61,2), "action":"Prioritize oldest balances and validate disputes/promises."})
    if s["concentration_top5_pct"] >= 35:
        a.append({"severity":"high", "title":"Customer concentration risk", "impact_pct":s["concentration_top5_pct"], "action":"Review top 5 exposures and credit limits."})
    if s["disputes"] > 0:
        a.append({"severity":"medium", "title":"Disputed invoices blocking cash", "impact":s["disputes"], "action":"Resolve PO/price/receipt/credit-note causes."})
    if not a:
        a.append({"severity":"info", "title":"No material AR alert under current rules", "impact":0, "action":"Continue monitoring in SHADOW mode."})
    return {"alerts": a, "source": s["source"], "error": err}

@app.get("/api/roi")
def roi(annual_credit_sales: float=8_000_000, dso_reduction_days: float=4, hours_week_saved: float=12, hourly_cost: float=35):
    working_capital=annual_credit_sales*dso_reduction_days/365
    labor=hours_week_saved*hourly_cost*52
    return {"working_capital_released":round(working_capital,2),"annual_productivity_value":round(labor,2),"combined_value_indicator":round(working_capital+labor,2)}

@app.get("/api/customer")
def customer_profile():
    return {"code":os.getenv("CUSTOMER_CODE","CUSTOMER-001"),"name":os.getenv("CUSTOMER_NAME","Mi Primer Cliente"),"mode":os.getenv("FINANCE_MODE","SHADOW"),"erp":os.getenv("ERP_PROVIDER","odoo"),"read_only":os.getenv("READ_ONLY","true").lower()=="true","approval_required":True}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Finance AI OS · CFO Command Center</title><style>
*{box-sizing:border-box}body{font-family:Inter,system-ui,Arial;background:#07131f;color:#eaf2f7;margin:0}.wrap{max-width:1320px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;gap:20px;align-items:center}.ey{color:#56d5dd;font-weight:800;letter-spacing:.08em}.badge{background:#11343a;border:1px solid #245761;color:#8cf6ef;padding:9px 13px;border-radius:999px;font-weight:700}.muted{color:#91a4b6}.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin:20px 0}.card{background:#0d1e2d;border:1px solid #173447;border-radius:16px;padding:18px;box-shadow:0 16px 40px #0004}.value{font-size:29px;font-weight:850;margin-top:6px}.two{display:grid;grid-template-columns:1.15fr .85fr;gap:14px}.aging{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}.bucket{background:#102636;padding:12px;border-radius:11px}.bar{height:8px;background:#172f3f;border-radius:8px;overflow:hidden;margin-top:8px}.fill{height:100%;background:#56d5dd}.alert{padding:12px;border-left:4px solid #ffb84d;background:#102432;border-radius:8px;margin:8px 0}.critical{border-left-color:#ff5d6c}.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;border-bottom:1px solid #173447;padding:9px 6px}.right{text-align:right!important}.source{font-size:12px;color:#6f8799;margin-top:12px}@media(max-width:900px){.grid,.aging{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}.top{align-items:flex-start;flex-direction:column}}@media(max-width:520px){.grid,.aging{grid-template-columns:1fr}}
</style></head><body><div class="wrap"><div class="top"><div><div class="ey">FINANCE AI OS v2.5</div><h1>CFO Command Center</h1><div class="muted" id="company">CUSTOMER #001 · cargando Odoo…</div></div><div class="badge">SHADOW · READ ONLY · HUMAN APPROVAL</div></div><div class="grid" id="kpis"></div><div class="card"><h2>Aging de cuentas por cobrar</h2><div class="aging" id="aging"></div></div><div class="two" style="margin-top:14px"><div class="card"><h2>Top clientes vencidos</h2><table class="table"><thead><tr><th>Cliente</th><th class="right">Importe</th></tr></thead><tbody id="top"></tbody></table></div><div class="card"><h2>Alertas del motor</h2><div id="alerts"></div><div class="source" id="source"></div></div></div></div><script>
let C='EUR';const fmt=n=>new Intl.NumberFormat('es-ES',{style:'currency',currency:C,maximumFractionDigits:0}).format(n||0);const num=n=>new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(n||0);
Promise.all([fetch('/api/metrics').then(r=>r.json()),fetch('/api/alerts').then(r=>r.json())]).then(([m,a])=>{C=m.currency||'EUR';document.getElementById('company').textContent=`${m.company} · ${m.invoice_count_365} facturas últimos 365d · ${m.open_invoice_count} abiertas`;const k=[['DSO',num(m.dso_days)+' días'],['AR abierto',fmt(m.ar_open)],['Vencido',fmt(m.overdue)],['61+ días',fmt((m.aging['61_90']||0)+(m.aging['90_plus']||0))],['Disputas',fmt(m.disputes)]];document.getElementById('kpis').innerHTML=k.map(x=>`<div class="card"><div class="muted">${x[0]}</div><div class="value">${x[1]}</div></div>`).join('');let max=Math.max(...Object.values(m.aging),1);let labels={current:'Corriente','1_30':'1–30','31_60':'31–60','61_90':'61–90','90_plus':'90+'};document.getElementById('aging').innerHTML=Object.entries(m.aging).map(([k,v])=>`<div class="bucket"><b>${labels[k]}</b><div>${fmt(v)}</div><div class="bar"><div class="fill" style="width:${Math.max(2,v/max*100)}%"></div></div></div>`).join('');document.getElementById('top').innerHTML=m.top_overdue.map(x=>`<tr><td>${x.customer}</td><td class="right">${fmt(x.amount)}</td></tr>`).join('')||'<tr><td colspan="2">Sin vencidos</td></tr>';document.getElementById('alerts').innerHTML=a.alerts.map(x=>`<div class="alert ${x.severity==='critical'?'critical':''}"><b>${x.title}</b><br><span class="muted">${x.impact?fmt(x.impact):x.impact_pct?x.impact_pct+'%':''} · ${x.action}</span></div>`).join('');document.getElementById('source').textContent=`Fuente: ${m.source} · corte ${m.as_of}${m.error?' · ERROR '+m.error:''}`;});
</script></body></html>'''
