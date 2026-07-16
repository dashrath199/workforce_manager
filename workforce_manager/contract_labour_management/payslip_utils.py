# -*- coding: utf-8 -*-
"""
Wage Slip and Bank Transfer File generation.

Generates:
1. Individual Wage Slip PDF — Per-employee payslip for a wage month
2. Bulk Wage Slips PDF — All employees in one combined document
3. Bank Transfer CSV — NACH/EFT format for bulk salary payments

Usage: Open a Submitted Wage Sheet → Click "Wage Slips" or "Bank Transfer" buttons
"""
import csv
import io
import frappe
from frappe import _
from frappe.utils import flt, formatdate, now_datetime
from frappe.utils.pdf import get_pdf

STANDARD_HOURS_PER_DAY = 8.0


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_ws_with_details(wage_sheet):
    """Load Wage Sheet with enriched employee master data."""
    ws = frappe.get_doc("Wage Sheet", wage_sheet)
    enriched = []
    for row in ws.details:
        emp = frappe.get_cached_doc("Contract Employee", row.employee)
        total_ded = flt(row.pf_deduction) + flt(row.esi_deduction) + flt(row.pt_deduction) + flt(row.lwf_deduction)
        pf_er = round(flt(row.pf_deduction) * 13.0 / 12.0, 2) if flt(row.pf_deduction) else 0.0
        esi_er = round(flt(row.esi_deduction) * 3.25 / 0.75, 2) if flt(row.esi_deduction) else 0.0

        enriched.append({
            "employee": row.employee,
            "employee_name": emp.first_name + (" " + (emp.last_name or "")).rstrip(),
            "uan": emp.uan_number or "N/A",
            "pf_number": emp.pf_number or "N/A",
            "esi_number": emp.esi_number or "N/A",
            "aadhaar": emp.aadhaar_number or "N/A",
            "bank_name": emp.bank_name or "",
            "bank_account": emp.bank_account_number or "",
            "ifsc": emp.ifsc_code or "",
            "days_present": row.days_present,
            "ot_hours": row.ot_hours,
            "gross_wage": row.gross_wage,
            "pf_deduction": row.pf_deduction,
            "esi_deduction": row.esi_deduction,
            "pt_deduction": row.pt_deduction,
            "lwf_deduction": row.lwf_deduction,
            "total_deduction": total_ded,
            "net_wage": row.net_wage,
            "pf_employer": pf_er,
            "esi_employer": esi_er,
            "total_employer": round(pf_er + esi_er, 2),
        })
    return ws, enriched


def _save_pdf(html, filename):
    """Convert HTML to PDF and save as File attachment."""
    pdf_data = get_pdf(html)
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "content": pdf_data,
        "is_private": 1,
    })
    file_doc.save(ignore_permissions=True)
    frappe.db.commit()
    return file_doc.file_url


def _save_csv(csv_data, filename):
    """Save CSV content as a private File and return the file URL."""
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "content": csv_data.encode("utf-8"),
        "is_private": 1,
    })
    file_doc.save(ignore_permissions=True)
    frappe.db.commit()
    return file_doc.file_url


# ---------------------------------------------------------------------------
#  1. Individual Wage Slip PDF
# ---------------------------------------------------------------------------

def _wage_slip_html(ws, emp, single=True):
    """Generate HTML for a single employee wage slip."""
    import datetime
    now = datetime.datetime.now()
    page_style = "@page { size: A4; margin: 12mm; }" if single else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Wage Slip - {emp['employee_name']}</title>
<style>
    {page_style}
    body {{ font-family: 'Courier New', monospace; font-size: 9.5pt; color: #000; }}
    .header {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 12px; }}
    .header h2 {{ margin: 0; font-size: 14pt; }}
    .header h3 {{ margin: 2px 0; font-size: 11pt; font-weight: normal; }}
    .section {{ margin-bottom: 12px; }}
    .section-title {{ font-weight: bold; font-size: 10pt; border-bottom: 1px solid #666; padding-bottom: 2px; margin-bottom: 6px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
    th, td {{ border: 1px solid #000; padding: 3px 5px; text-align: left; }}
    th {{ background: #e0e0e0; font-weight: bold; text-align: center; }}
    .text-right {{ text-align: right; }}
    .text-center {{ text-align: center; }}
    .totals-row {{ font-weight: bold; background: #f5f5f5; }}
    .footer {{ margin-top: 20px; font-size: 8pt; text-align: center; }}
    .employee-details {{ width: 100%; margin-bottom: 10px; }}
    .employee-details td {{ border: none; padding: 2px 5px; }}
    .signature {{ margin-top: 30px; font-size: 9pt; }}
    .signature td {{ border: none; }}
</style>
</head>
<body>
<div class="header">
    <h2>WAGE SLIP</h2>
    <h3>{ws.contractor} | Site: {ws.site}</h3>
    <p style="margin:2px 0; font-size:9pt;">Month: {ws.wage_month} | Generated: {now.strftime('%d-%m-%Y %H:%M')}</p>
</div>

<table class="employee-details">
    <tr>
        <td width="50%"><strong>Employee:</strong> {emp['employee_name']}</td>
        <td width="50%"><strong>UAN:</strong> {emp['uan']}</td>
    </tr>
    <tr>
        <td><strong>PF No:</strong> {emp['pf_number']}</td>
        <td><strong>ESI No:</strong> {emp['esi_number']}</td>
    </tr>
    <tr>
        <td><strong>Aadhaar:</strong> {emp['aadhaar']}</td>
        <td><strong>Days Present:</strong> {emp['days_present']:.1f}</td>
    </tr>
</table>

<div class="section">
    <div class="section-title">Earnings & Deductions</div>
    <table>
        <tr>
            <th>Particulars</th>
            <th class="text-right">Amount (Rs.)</th>
        </tr>
        <tr>
            <td>Gross Wages ({emp['days_present']:.1f} days)</td>
            <td class="text-right">{flt(emp['gross_wage']):.2f}</td>
        </tr>
        <tr>
            <td>OT Hours ({emp['ot_hours']:.2f} hrs @ 2x)</td>
            <td class="text-right">—</td>
        </tr>
        <tr><td colspan="2" style="border:none; padding:2px;"></td></tr>
        <tr class="totals-row">
            <td><strong>Gross Wage</strong></td>
            <td class="text-right"><strong>{flt(emp['gross_wage']):.2f}</strong></td>
        </tr>
        <tr><td colspan="2" style="border:none; padding:2px;"></td></tr>
        <tr><td colspan="2"><strong>Deductions:</strong></td></tr>
        <tr>
            <td>&nbsp;&nbsp;Provident Fund (PF)</td>
            <td class="text-right">{flt(emp['pf_deduction']):.2f}</td>
        </tr>
        <tr>
            <td>&nbsp;&nbsp;Employees State Insurance (ESI)</td>
            <td class="text-right">{flt(emp['esi_deduction']):.2f}</td>
        </tr>
        <tr>
            <td>&nbsp;&nbsp;Professional Tax (PT)</td>
            <td class="text-right">{flt(emp['pt_deduction']):.2f}</td>
        </tr>
        <tr>
            <td>&nbsp;&nbsp;Labour Welfare Fund (LWF)</td>
            <td class="text-right">{flt(emp['lwf_deduction']):.2f}</td>
        </tr>
        <tr class="totals-row">
            <td><strong>Total Deductions</strong></td>
            <td class="text-right"><strong>{emp['total_deduction']:.2f}</strong></td>
        </tr>
        <tr><td colspan="2" style="border:none; padding:2px;"></td></tr>
        <tr class="totals-row">
            <td><strong>NET PAYABLE</strong></td>
            <td class="text-right"><strong style="font-size:11pt;">{flt(emp['net_wage']):.2f}</strong></td>
        </tr>
    </table>
</div>

<div class="section">
    <div class="section-title">Employer Contributions</div>
    <table>
        <tr><th>Particulars</th><th class="text-right">Amount (Rs.)</th></tr>
        <tr><td>Employer PF</td><td class="text-right">{emp['pf_employer']:.2f}</td></tr>
        <tr><td>Employer ESI</td><td class="text-right">{emp['esi_employer']:.2f}</td></tr>
        <tr class="totals-row"><td><strong>Total Employer Cost</strong></td><td class="text-right"><strong>{emp['total_employer']:.2f}</strong></td></tr>
    </table>
</div>

<table class="signature">
    <tr>
        <td width="50%" style="text-align:center;">_________________________</td>
        <td width="50%" style="text-align:center;">_________________________</td>
    </tr>
    <tr>
        <td style="text-align:center;">Employee Signature</td>
        <td style="text-align:center;">Authorized Signatory</td>
    </tr>
</table>
<p class="footer">This is a computer-generated wage slip. Generated on {now.strftime('%d-%m-%Y %H:%M')}.</p>
</body>
</html>"""


@frappe.whitelist()
def generate_wage_slip(wage_sheet, employee):
    """Generate a single employee's wage slip PDF."""
    ws, employees = _get_ws_with_details(wage_sheet)
    emp = next((e for e in employees if e["employee"] == employee), None)
    if not emp:
        frappe.throw(f"Employee {employee} not found in Wage Sheet {wage_sheet}")

    html = _wage_slip_html(ws, emp)
    filename = f"WageSlip_{employee}_{ws.wage_month.replace('-', '_')}.pdf"
    return _save_pdf(html, filename)


@frappe.whitelist()
def generate_all_wage_slips(wage_sheet):
    """Generate combined wage slip PDF for ALL employees in the Wage Sheet."""
    ws, employees = _get_ws_with_details(wage_sheet)
    pages = []
    for emp in employees:
        pages.append(_wage_slip_html(ws, emp, single=False))

    html = (
        "<!DOCTYPE html><html><body>"
        + '<div style="page-break-after: always;">'.join(pages)
        + "</body></html>"
    )
    filename = f"All_WageSlips_{ws.name.replace('-', '_')}.pdf"
    return _save_pdf(html, filename)


# ---------------------------------------------------------------------------
#  2. Bank Transfer File — CSV for NACH / EFT upload
# ---------------------------------------------------------------------------

@frappe.whitelist()
def generate_bank_transfer_file(wage_sheet):
    """Generate CSV file for bulk bank transfer (NACH/EFT format).

    Columns: Employee Name, Bank Name, Account Number, IFSC Code, Amount, UAN
    Only includes employees with valid bank details.
    """
    ws, employees = _get_ws_with_details(wage_sheet)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "EmployeeName", "BankName", "AccountNumber", "IFSC",
        "Amount", "UAN", "Remarks",
    ])

    total_amount = 0.0
    skipped = 0
    added = 0

    for emp in employees:
        net = flt(emp["net_wage"])
        if net <= 0:
            skipped += 1
            continue

        # Only include employees with bank details
        bank_ac = (emp["bank_account"] or "").strip()
        ifsc = (emp["ifsc"] or "").strip()

        if not bank_ac or not ifsc:
            skipped += 1
            continue

        writer.writerow([
            emp["employee_name"],
            emp["bank_name"],
            bank_ac,
            ifsc,
            f"{net:.2f}",
            emp["uan"],
            f"Wages for {ws.wage_month}",
        ])
        total_amount += net
        added += 1

    # Summary row
    writer.writerow([])
    writer.writerow(["TOTAL", "", "", "", f"{total_amount:.2f}", "", f"{added} employees"])
    if skipped:
        writer.writerow(["NOTE", f"{skipped} employee(s) skipped (no bank details or zero net)"])

    filename = f"BankTransfer_{ws.name.replace('-', '_')}.csv"
    return _save_csv(output.getvalue(), filename)
