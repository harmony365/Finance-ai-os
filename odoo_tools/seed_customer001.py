import os, random
from datetime import date, timedelta
from odoo import Command

SEED = int(os.environ.get("DEMO_SEED", "42001"))
random.seed(SEED)
as_of = date.fromisoformat(os.environ.get("DEMO_AS_OF", date.today().isoformat()))
company_name = os.environ.get("DEMO_COMPANY_NAME", "Finance AI Demo SL")
rename_company = os.environ.get("DEMO_RENAME_COMPANY", "false").lower() in {"1","true","yes"}
reset = os.environ.get("DEMO_RESET", "false").lower() in {"1","true","yes"}

Company = env["res.company"].sudo()
company = env.company
if rename_company and company.name == "My Company":
    company.name = company_name

Partner = env["res.partner"].sudo()
Move = env["account.move"].sudo()
Journal = env["account.journal"].sudo()
Account = env["account.account"].sudo()

sale_journal = Journal.search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
bank_journal = Journal.search([("type", "=", "bank"), ("company_id", "=", company.id)], limit=1)
income = Account.search([("account_type", "=", "income"), ("company_ids", "in", company.id)] if "company_ids" in Account._fields else [("account_type", "=", "income"), ("company_id", "=", company.id)], limit=1)
if not sale_journal or not bank_journal or not income:
    raise SystemExit(f"Missing accounting primitives: sale_journal={bool(sale_journal)} bank_journal={bool(bank_journal)} income={bool(income)}")

marker = "FINANCEAI-DEMO-001"
if reset:
    demo_moves = Move.search([("ref", "ilike", marker)])
    # Only delete demo moves that are still draft; posted accounting records are intentionally not mass-deleted.
    drafts = demo_moves.filtered(lambda m: m.state == "draft")
    if drafts:
        drafts.unlink()

# Customer master: 120 deterministic B2B customers.
partners = []
for i in range(1, 121):
    name = f"Demo Customer {i:03d} SL"
    p = Partner.search([("name", "=", name)], limit=1)
    vals = {
        "name": name,
        "company_type": "company",
        "customer_rank": 1,
        "email": f"finance.customer{i:03d}@example.invalid",
        "phone": f"+34 910 {i:03d} {100+i:03d}",
    }
    if "credit_limit" in Partner._fields:
        vals["credit_limit"] = float(random.choice([25000, 50000, 75000, 100000, 150000]))
    if not p:
        p = Partner.create(vals)
    else:
        p.write({k:v for k,v in vals.items() if k != "customer_rank"})
    partners.append(p)

# Skip if already seeded.
existing = Move.search_count([("ref", "ilike", marker)])
if existing >= 700:
    print(f"SEED_ALREADY_PRESENT: invoices={existing}")
    raise SystemExit(0)

buckets = (
    [("paid", None)] * 380
    + [("current", 0)] * 170
    + [("od_1_30", 15)] * 95
    + [("od_31_60", 45)] * 55
    + [("od_61_90", 75)] * 32
    + [("od_90_plus", 120)] * 18
)
random.shuffle(buckets)

def amount_for(i):
    # About EUR 8M annual invoice volume across 750 invoices.
    return round(random.uniform(3500, 18000), 2)

def due_for(bucket, past_days):
    if bucket == "paid":
        inv_date = as_of - timedelta(days=random.randint(45, 350))
        return inv_date, inv_date + timedelta(days=30)
    if bucket == "current":
        due = as_of + timedelta(days=random.randint(1, 45))
        return max(due - timedelta(days=30), as_of - timedelta(days=28)), due
    due = as_of - timedelta(days=max(1, past_days + random.randint(-7, 7)))
    return due - timedelta(days=30), due

created = paid = partial = disputed = 0
for i, (bucket, past) in enumerate(buckets, start=1):
    existing_move = Move.search([("ref", "ilike", f"{marker}-{i:04d}%")], limit=1)
    if existing_move:
        continue
    partner = partners[(i * 17) % len(partners)]
    amount = amount_for(i)
    inv_date, due = due_for(bucket, past)
    dispute = bucket != "paid" and (i % 17 == 0 or i % 29 == 0)
    dispute_code = random.choice(["PO", "PRICE", "RECEIPT", "CREDIT_NOTE"]) if dispute else ""
    ref = f"{marker}-{i:04d}" + (f" [DISPUTE:{dispute_code}]" if dispute else "")
    move = Move.create({
        "move_type": "out_invoice",
        "partner_id": partner.id,
        "journal_id": sale_journal.id,
        "invoice_date": inv_date,
        "invoice_date_due": due,
        "ref": ref,
        "invoice_line_ids": [Command.create({
            "name": "B2B services / product delivery",
            "quantity": 1.0,
            "price_unit": amount,
            "account_id": income.id,
        })],
    })
    move.action_post()
    created += 1
    if dispute:
        disputed += 1

    # Actual accounting payments through Odoo's payment register wizard.
    if bucket == "paid" or (bucket != "paid" and i % 13 == 0):
        pay_date = min(as_of, due + timedelta(days=random.randint(-3, 25)))
        pay_amount = move.amount_residual if bucket == "paid" else round(move.amount_residual * random.uniform(0.25, 0.60), 2)
        if pay_amount > 0:
            ctx = {"active_model": "account.move", "active_ids": move.ids}
            wizard = env["account.payment.register"].with_context(ctx).create({
                "amount": pay_amount,
                "payment_date": pay_date,
                "journal_id": bank_journal.id,
            })
            wizard.action_create_payments()
            if bucket == "paid": paid += 1
            else: partial += 1

    if i % 50 == 0:
        env.cr.commit()
        print(f"progress invoices={i}")

env.cr.commit()
print(f"SEED_COMPLETE invoices={created} paid={paid} partial={partial} disputes={disputed} customers={len(partners)}")
