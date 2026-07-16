# -*- coding: utf-8 -*-
"""Statutory Register Generation for Contract Labour Management.

Generates three standard Indian labour law registers as PDF:
1. Muster Roll      — Daily attendance register (per employee, per day)
2. Wage Register    — Monthly wage summary (gross, deductions, net)
3. Deduction Register — Statutory deduction breakdown (PF, ESI, PT, LWF)

Usage (called from Wage Sheet form buttons):
    frappe.call({
        method: "workforce_manager.contract_labour_management.registers.generate_muster_roll",
        args: { wage_sheet: "WS-2026-07-00001" },
        callback: (r) => { window.open(r.message); }
    });
"""
import frappe
from frappe import _
from frappe.utils import getdate, flt, today, formatdate
from frappe.utils.pdf import get_pdf
from frappe.utils.data import add_days


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_wage_sheet_data(wage_sheet):
    """Return (ws_doc, rows, month_start, month_end) for a submitted Wage Sheet."""
    ws = frappe.get_doc("Wage Sheet", wage_sheet)
    start_date, end_date = _parse_wage_month(ws.wage_month)
    return ws, ws.details, start_date, end_date


def _parse_wage_month(wage_month):
    """Parse 'Jan-2026' or '2026-01' into (start_date, end_date) date objects."""
    import re
    from datetime import date

    # Try YYYY-MM format first
    m = re.match(r"^(\d{4})-(\d{2})$", wage_month.strip())
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        start = date(y, mo, 1)
        if mo == 12:
            end = date(y + 1, 1, 1)
        else:
            end = date(y, mo + 1, 1)
        return start, add_days(end, -1)

    # Try MMM-YYYY format (e.g. Jan-2026)
    try:
        dt = getdate(f"01-{wage_month.replace(' ', '')}")
        y, mo = dt.year, dt.month
        start = date(y, mo, 1)
        if mo == 12:
            end = date(y + 1, 1, 1)
        else:
            end = date(y, mo + 1, 1)
        return start, add_days(end, -1)
    except Exception:
        frappe.throw(f"Could not parse wage month: {wage_month}")


def _render_pdf(html, filename):
    """Convert HTML to PDF and save as a File attachment. Return the file URL."""
    pdf_data = get_pdf(html)
    # Create a File document
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "content": pdf_data,
        "is_private": 1,
    })
    file_doc.save(ignore_permissions=True)
    frappe.db.commit()
    return file_doc.file_url


def _register_html(title, subtitle, headers, rows):
    """Build a clean tabular HTML document styled like a statutory register."""
    import datetime
    now = datetime.datetime.now()

    thead = "".join(f"<th>{h}</th>" for h in headers)
    tbody = ""
    for i, row in enumerate(rows, 1):
        cells = "".join(f"<td>{str(c)}</td>" for c in row)
        tbody += f"<tr>{cells}</tr>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
    @page {{ size: A4 landscape; margin: 15mm; }}
    body {{ font-family: 'Courier New', monospace; font-size: 10pt; color: #000; }}
    h2 {{ text-align: center; margin-bottom: 4px; font-size: 14pt; }}
    h3 {{ text-align: center; margin: 2px 0 6px; font-size: 11pt; font-weight: normal; }}
    .meta {{ text-align: center; font-size: 9pt; margin-bottom: 10px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; }}
    th, td {{ border: 1px solid #000; padding: 3px 5px; text-align: left; }}
    th {{ background: #e0e0e0; font-weight: bold; text-align: center; }}
    td {{ vertical-align: top; }}
    .text-right {{ text-align: right; }}
    .text-center {{ text-align: center; }}
    .footer {{ margin-top: 10px; font-size: 8pt; text-align: center; }}
</style>
</head>
<body>
<h2>{title}</h2>
<h3>{subtitle}</h3>
<p class="meta">Generated on: {now.strftime('%d-%m-%Y %H:%M')}</p>
<table>
<thead><tr>{thead}</tr></thead>
<tbody>{tbody}</tbody>
</table>
<p class="footer">This is a computer-generated document. Signature not required.</p>
</body>
</html>"""


# ---------------------------------------------------------------------------
#  1. MUSTER ROLL — Daily attendance register
# ---------------------------------------------------------------------------

@frappe.whitelist()
def generate_muster_roll(wage_sheet):
    """Generate Muster Roll PDF for a given Wage Sheet.

    Columns: Employee | Site | Days 1-31 | Total Present | Absent | OT Hours
    """
    ws = frappe.get_doc("Wage Sheet", wage_sheet)
    start_date, end_date = _parse_wage_month(ws.wage_month)

    # Build list of days in month
    from datetime import timedelta
    days = []
    d = start_date
    while d <= end_date:
        days.append(d)
        d += timedelta(days=1)

    # Short day-of-month labels (1, 2, 3 ...)
    day_labels = [str(dd.day) for dd in days]

    attendance_data = {}
    employees = [row.employee for row in ws.details]
    emp_names = {e: e for e in employees}  # fallback
    emp_sites = {}

    # Pre-fetch employee names & sites
    for emp in employees:
        doc = frappe.get_cached_doc("Contract Employee", emp)
        emp_names[emp] = doc.first_name + (" " + (doc.last_name or "")).rstrip()
        emp_sites[emp] = doc.site

    # Fetch attendance records for all employees in this month range
    att_records = frappe.db.get_all(
        "Attendance Record",
        filters={
            "employee": ["in", employees],
            "date": ["between", [start_date, end_date]],
        },
        fields=["employee", "date", "status", "ot_hours"],
    )

    # Build lookup: {employee: {date_str: {status, ot_hours}}}
    for rec in att_records:
        emp = rec["employee"]
        date_key = str(rec["date"])
        if emp not in attendance_data:
            attendance_data[emp] = {}
        attendance_data[emp][date_key] = rec

    # Build rows
    headers = ["#", "Employee Name", "Site"] + day_labels + ["Present Days", "Absent", "OT Hours"]
    rows = []

    for idx, emp in enumerate(employees, 1):
        emp_att = attendance_data.get(emp, {})
        day_cells = []
        present = 0
        absent = 0
        ot_total = 0.0

        for day in days:
            date_key = str(day)
            rec = emp_att.get(date_key)
            if rec:
                if rec["status"] == "Present" or rec["status"] == "Half Day":
                    day_cells.append("P" if rec["status"] == "Present" else "HD")
                    present += 1 if rec["status"] == "Present" else 0.5
                elif rec["status"] == "Leave":
                    day_cells.append("L")
                else:
                    day_cells.append("A")
                    absent += 1
                ot_total += flt(rec["ot_hours"])
            else:
                day_cells.append("A")
                absent += 1

        rows.append([
            idx,
            emp_names.get(emp, emp),
            emp_sites.get(emp, ""),
        ] + day_cells + [
            f"{present:.1f}",
            f"{absent:.0f}",
            f"{ot_total:.2f}",
        ])

    title = "MUSTER ROLL"
    subtitle = (
        f"Site: {ws.site} | Contractor: {ws.contractor} | "
        f"Month: {ws.wage_month} | Wage Sheet: {ws.name}"
    )
    html = _register_html(title, subtitle, headers, rows)
    filename = f"Muster_Roll_{ws.name.replace('-', '_')}.pdf"
    file_url = _render_pdf(html, filename)
    return file_url


# ---------------------------------------------------------------------------
#  2. WAGE REGISTER — Monthly wage summary per employee
# ---------------------------------------------------------------------------

@frappe.whitelist()
def generate_wage_register(wage_sheet):
    """Generate Wage Register PDF.

    Columns: # | Employee | Days Present | OT Hours | Gross Wage |
             PF | ESI | PT | LWF | Total Deductions | Net Wage
    """
    ws = frappe.get_doc("Wage Sheet", wage_sheet)
    emp_docs = {}
    for row in ws.details:
        doc = frappe.get_cached_doc("Contract Employee", row.employee)
        emp_docs[row.employee] = doc

    headers = [
        "#", "Employee Name", "Days Present", "OT Hours",
        "Gross Wage", "PF Deduction", "ESI Deduction",
        "PT Deduction", "LWF Deduction", "Total Deductions", "Net Wage",
    ]
    rows = []
    grand_gross = 0.0
    grand_pf = 0.0
    grand_esi = 0.0
    grand_pt = 0.0
    grand_lwf = 0.0
    grand_ded = 0.0
    grand_net = 0.0

    for idx, row in enumerate(ws.details, 1):
        emp = row.employee
        emp_name = emp_docs[emp].first_name + (" " + (emp_docs[emp].last_name or "")).rstrip()
        total_ded = flt(row.pf_deduction) + flt(row.esi_deduction) + flt(row.pt_deduction) + flt(row.lwf_deduction)

        rows.append([
            idx,
            emp_name,
            f"{row.days_present:.1f}",
            f"{row.ot_hours:.2f}",
            f"{flt(row.gross_wage):.2f}",
            f"{flt(row.pf_deduction):.2f}",
            f"{flt(row.esi_deduction):.2f}",
            f"{flt(row.pt_deduction):.2f}",
            f"{flt(row.lwf_deduction):.2f}",
            f"{total_ded:.2f}",
            f"{flt(row.net_wage):.2f}",
        ])

        grand_gross += flt(row.gross_wage)
        grand_pf += flt(row.pf_deduction)
        grand_esi += flt(row.esi_deduction)
        grand_pt += flt(row.pt_deduction)
        grand_lwf += flt(row.lwf_deduction)
        grand_ded += total_ded
        grand_net += flt(row.net_wage)

    # Totals row
    rows.append([
        "", "GRAND TOTAL",
        f"{sum(flt(r.days_present) for r in ws.details):.1f}",
        f"{sum(flt(r.ot_hours) for r in ws.details):.2f}",
        f"{grand_gross:.2f}",
        f"{grand_pf:.2f}",
        f"{grand_esi:.2f}",
        f"{grand_pt:.2f}",
        f"{grand_lwf:.2f}",
        f"{grand_ded:.2f}",
        f"{grand_net:.2f}",
    ])

    title = "WAGE REGISTER"
    subtitle = (
        f"Site: {ws.site} | Contractor: {ws.contractor} | "
        f"Month: {ws.wage_month} | Status: {ws.status}"
    )
    html = _register_html(title, subtitle, headers, rows)
    filename = f"Wage_Register_{ws.name.replace('-', '_')}.pdf"
    file_url = _render_pdf(html, filename)
    return file_url


# ---------------------------------------------------------------------------
#  3. DEDUCTION REGISTER — Statutory deduction breakdown per employee
# ---------------------------------------------------------------------------

@frappe.whitelist()
def generate_deduction_register(wage_sheet):
    """Generate Deduction Register PDF.

    Columns: # | Employee | Gross Wage | PF (12%) | ESI (0.75%) |
             PT | LWF | Employer PF | Employer ESI | Total Statutory
    """
    ws = frappe.get_doc("Wage Sheet", wage_sheet)
    emp_docs = {}
    for row in ws.details:
        doc = frappe.get_cached_doc("Contract Employee", row.employee)
        emp_docs[row.employee] = doc

    headers = [
        "#", "Employee Name", "Gross Wage",
        "PF (Employee)", "ESI (Employee)", "PT", "LWF",
        "PF (Employer)", "ESI (Employer)",
        "Total Contribution",
    ]
    rows = []
    grand_gross = 0.0
    grand_pf_ee = 0.0
    grand_esi_ee = 0.0
    grand_pt = 0.0
    grand_lwf = 0.0
    grand_pf_er = 0.0
    grand_esi_er = 0.0
    grand_total = 0.0

    for idx, row in enumerate(ws.details, 1):
        emp = row.employee
        emp_name = emp_docs[emp].first_name + (" " + (emp_docs[emp].last_name or "")).rstrip()

        # Employer contributions (PF @ 13%, ESI @ 3.25%)
        pf_ee = flt(row.pf_deduction)
        esi_ee = flt(row.esi_deduction)
        pt = flt(row.pt_deduction)
        lwf = flt(row.lwf_deduction)
        pf_er = round(pf_ee * 13.0 / 12.0, 2) if pf_ee else 0.0
        esi_er = round(esi_ee * 3.25 / 0.75, 2) if esi_ee else 0.0
        total = pf_ee + esi_ee + pt + lwf + pf_er + esi_er

        rows.append([
            idx,
            emp_name,
            f"{flt(row.gross_wage):.2f}",
            f"{pf_ee:.2f}",
            f"{esi_ee:.2f}",
            f"{pt:.2f}",
            f"{lwf:.2f}",
            f"{pf_er:.2f}",
            f"{esi_er:.2f}",
            f"{total:.2f}",
        ])

        grand_gross += flt(row.gross_wage)
        grand_pf_ee += pf_ee
        grand_esi_ee += esi_ee
        grand_pt += pt
        grand_lwf += lwf
        grand_pf_er += pf_er
        grand_esi_er += esi_er
        grand_total += total

    rows.append([
        "", "GRAND TOTAL",
        f"{grand_gross:.2f}",
        f"{grand_pf_ee:.2f}",
        f"{grand_esi_ee:.2f}",
        f"{grand_pt:.2f}",
        f"{grand_lwf:.2f}",
        f"{grand_pf_er:.2f}",
        f"{grand_esi_er:.2f}",
        f"{grand_total:.2f}",
    ])

    title = "STATUTORY DEDUCTION REGISTER"
    subtitle = (
        f"Site: {ws.site} | Contractor: {ws.contractor} | "
        f"Month: {ws.wage_month} | Status: {ws.status}"
    )
    html = _register_html(title, subtitle, headers, rows)
    filename = f"Deduction_Register_{ws.name.replace('-', '_')}.pdf"
    file_url = _render_pdf(html, filename)
    return file_url
