# -*- coding: utf-8 -*-
"""
PF/ESI Challan Filing and ECR (Electronic Challan cum Return) generation.

Generates:
1. PF ECR CSV — Standard format for EPFO portal upload (member-wise)
2. ESI Return CSV — Standard format for ESIC portal upload
3. PF Challan PDF — Summary for payment
4. ESI Challan PDF — Summary for payment
5. PT Challan PDF — Professional Tax payment challan
6. LWF Challan PDF — Labour Welfare Fund payment challan

Usage: Open a Statutory Compliance Record → Click "Generate PF ECR" etc.
"""
import csv
import io
import frappe
from frappe import _
from frappe.utils import flt, getdate, today, formatdate, now_datetime
from frappe.utils.pdf import get_pdf


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_employees_for_sc_record(scr_name):
    """Get all Wage Sheet Details for this contractor + wage month."""
    scr = frappe.get_doc("Statutory Compliance Record", scr_name)
    wage_sheets = frappe.get_all(
        "Wage Sheet",
        filters={
            "contractor": scr.contractor,
            "wage_month": scr.wage_month,
            "docstatus": 1,
        },
        pluck="name",
    )
    if not wage_sheets:
        frappe.throw(f"No submitted Wage Sheets found for contractor {scr.contractor} in {scr.wage_month}")

    details = frappe.get_all(
        "Wage Sheet Detail",
        filters={"parent": ["in", wage_sheets]},
        fields=[
            "employee", "gross_wage", "pf_deduction", "esi_deduction",
            "pt_deduction", "lwf_deduction", "days_present", "ot_hours",
        ],
    )

    # Enrich with employee master data
    enriched = []
    for d in details:
        emp = frappe.get_cached_doc("Contract Employee", d.employee)
        enriched.append({
            **d,
            "employee_name": emp.first_name + (" " + (emp.last_name or "")).rstrip(),
            "uan": emp.uan_number or "",
            "pf_number": emp.pf_number or "",
            "esi_number": emp.esi_number or "",
            "aadhaar": emp.aadhaar_number or "",
        })
    return enriched


def _save_csv_file(csv_data, filename):
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


# ---------------------------------------------------------------------------
#  1. PF ECR — CSV for EPFO portal upload (member-wise)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def generate_pf_ecr(statutory_record):
    """Generate PF ECR CSV in standard EPFO format.
    
    Columns: Member ID, UAN, Name, Gross Wages, Employee PF, Employer PF 3.67%,
             Employer PF 8.33% (Pension), Employer EDLI 0.5%, Employer PF Admin 0.5%
    """
    employees = _get_employees_for_sc_record(statutory_record)
    scr = frappe.get_doc("Statutory Compliance Record", statutory_record)
    month_label = scr.wage_month.replace("-", "_").replace(" ", "_")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "MemberID", "UAN", "Name", "GrossWages",
        "EmployeePF", "EmployerPF_367", "EmployerPension_833",
        "EmployerEDLI_050", "EmployerAdmin_050",
    ])

    total_gross = 0.0
    total_ee_pf = 0.0
    total_er_pf = 0.0
    total_er_pension = 0.0

    for emp in employees:
        gross = flt(emp.gross_wage)
        ee_pf = flt(emp.pf_deduction)
        # Employer contributions
        er_pf = round(gross * 3.67 / 100, 2)
        er_pension = round(gross * 8.33 / 100, 2)
        er_edli = round(gross * 0.50 / 100, 2)
        er_admin = round(gross * 0.50 / 100, 2)

        writer.writerow([
            emp.pf_number or emp.employee,
            emp.uan,
            emp.employee_name,
            f"{gross:.2f}",
            f"{ee_pf:.2f}",
            f"{er_pf:.2f}",
            f"{er_pension:.2f}",
            f"{er_edli:.2f}",
            f"{er_admin:.2f}",
        ])
        total_gross += gross
        total_ee_pf += ee_pf
        total_er_pf += er_pf
        total_er_pension += er_pension

    # Totals row
    writer.writerow([
        "", "", "TOTAL",
        f"{total_gross:.2f}", f"{total_ee_pf:.2f}",
        f"{total_er_pf:.2f}", f"{total_er_pension:.2f}", "", "",
    ])

    filename = f"PF_ECR_{scr.contractor}_{month_label}.csv"
    return _save_csv_file(output.getvalue(), filename)


# ---------------------------------------------------------------------------
#  2. ESI Return — CSV for ESIC portal upload
# ---------------------------------------------------------------------------

@frappe.whitelist()
def generate_esi_return(statutory_record):
    """Generate ESI return CSV.
    
    Columns: Employee Code, Name, Insured Person Name, Gross Wages,
             Employee ESI 0.75%, Employer ESI 3.25%
    """
    employees = _get_employees_for_sc_record(statutory_record)
    scr = frappe.get_doc("Statutory Compliance Record", statutory_record)
    month_label = scr.wage_month.replace("-", "_").replace(" ", "_")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "EmployeeCode", "Name", "IPName", "GrossWages",
        "EmployeeESI", "EmployerESI",
    ])

    total_gross = 0.0
    total_ee_esi = 0.0
    total_er_esi = 0.0

    for emp in employees:
        gross = flt(emp.gross_wage)
        ee_esi = flt(emp.esi_deduction)
        er_esi = round(gross * 3.25 / 100, 2)

        writer.writerow([
            emp.esi_number or emp.employee,
            emp.employee_name,
            emp.employee_name,
            f"{gross:.2f}",
            f"{ee_esi:.2f}",
            f"{er_esi:.2f}",
        ])
        total_gross += gross
        total_ee_esi += ee_esi
        total_er_esi += er_esi

    writer.writerow([
        "", "TOTAL", "", f"{total_gross:.2f}",
        f"{total_ee_esi:.2f}", f"{total_er_esi:.2f}",
    ])

    filename = f"ESI_Return_{scr.contractor}_{month_label}.csv"
    return _save_csv_file(output.getvalue(), filename)


# ---------------------------------------------------------------------------
#  3-6. Challan PDFs — PF, ESI, PT, LWF
# ---------------------------------------------------------------------------

def _challan_html(title, scr, rows, grand_totals, columns):
    """Generate an HTML challan document formatted for PDF."""
    import datetime
    now = datetime.datetime.now()

    thead = "".join(f"<th>{h}</th>" for h in columns)
    tbody = ""
    for row in rows:
        cells = "".join(f"<td>{str(c)}</td>" for c in row)
        tbody += f"<tr>{cells}</tr>"

    # Totals row
    tfoot = "<tr>" + "".join(f"<td><strong>{str(c)}</strong></td>" for c in grand_totals) + "</tr>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
    @page {{ size: A4; margin: 15mm; }}
    body {{ font-family: 'Courier New', monospace; font-size: 10pt; color: #000; }}
    h2 {{ text-align: center; margin-bottom: 4px; font-size: 14pt; }}
    h3 {{ text-align: center; margin: 2px 0 6px; font-size: 11pt; font-weight: normal; }}
    .meta {{ text-align: center; font-size: 9pt; margin-bottom: 10px; }}
    .details {{ font-size: 9pt; margin-bottom: 10px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
    th, td {{ border: 1px solid #000; padding: 4px 6px; text-align: left; }}
    th {{ background: #e0e0e0; font-weight: bold; text-align: center; }}
    .text-right {{ text-align: right; }}
    .text-center {{ text-align: center; }}
    .footer {{ margin-top: 10px; font-size: 8pt; text-align: center; }}
    .signature {{ margin-top: 30px; font-size: 9pt; }}
</style>
</head>
<body>
<h2>{title}</h2>
<h3>{scr.contractor}</h3>
<p class="meta">
    Month: {scr.wage_month} | Due Date: {formatdate(scr.due_date)} |
    Generated: {now.strftime('%d-%m-%Y %H:%M')}
</p>
<table>
<thead><tr>{thead}</tr></thead>
<tbody>{tbody}{tfoot}</tbody>
</table>
<p class="footer">This is a computer-generated challan. Authorized signatory: _________________</p>
</body>
</html>"""


@frappe.whitelist()
def generate_pf_challan(statutory_record):
    """Generate PF Challan PDF with employee-wise and employer contributions."""
    employees = _get_employees_for_sc_record(statutory_record)
    scr = frappe.get_doc("Statutory Compliance Record", statutory_record)

    columns = ["#", "Employee Name", "UAN", "Gross Wages", "Employee PF (12%)",
               "Employer PF (3.67%)", "Employer Pension (8.33%)", "Employer EDLI (0.5%)"]
    rows = []
    tg = tee = ter = tpen = 0.0

    for i, emp in enumerate(employees, 1):
        g = flt(emp.gross_wage)
        ee = flt(emp.pf_deduction)
        er = round(g * 3.67 / 100, 2)
        pen = round(g * 8.33 / 100, 2)
        edli = round(g * 0.50 / 100, 2)
        rows.append([i, emp.employee_name, emp.uan, f"{g:.2f}", f"{ee:.2f}", f"{er:.2f}", f"{pen:.2f}", f"{edli:.2f}"])
        tg += g; tee += ee; ter += er; tpen += pen

    total = f"{tg:.2f}", "TOTAL", "", "", f"{tee:.2f}", f"{ter:.2f}", f"{tpen:.2f}", ""
    html = _challan_html("PF CHALLAN — EPFO", scr, rows, total, columns)
    filename = f"PF_Challan_{scr.contractor}_{scr.wage_month.replace('-', '_')}.pdf"
    return _save_pdf(html, filename)


@frappe.whitelist()
def generate_esi_challan(statutory_record):
    """Generate ESI Challan PDF."""
    employees = _get_employees_for_sc_record(statutory_record)
    scr = frappe.get_doc("Statutory Compliance Record", statutory_record)

    columns = ["#", "Employee Name", "ESI No", "Gross Wages", "Employee ESI (0.75%)", "Employer ESI (3.25%)", "Total ESI"]
    rows = []
    tg = tee = ter = 0.0

    for i, emp in enumerate(employees, 1):
        g = flt(emp.gross_wage)
        ee = flt(emp.esi_deduction)
        er = round(g * 3.25 / 100, 2)
        rows.append([i, emp.employee_name, emp.esi_number, f"{g:.2f}", f"{ee:.2f}", f"{er:.2f}", f"{ee + er:.2f}"])
        tg += g; tee += ee; ter += er

    html = _challan_html("ESI CHALLAN — ESIC", scr, rows,
                         [f"{tg:.2f}", "TOTAL", "", "", f"{tee:.2f}", f"{ter:.2f}", f"{tee + ter:.2f}"], columns)
    filename = f"ESI_Challan_{scr.contractor}_{scr.wage_month.replace('-', '_')}.pdf"
    return _save_pdf(html, filename)


@frappe.whitelist()
def generate_pt_challan(statutory_record):
    """Generate Professional Tax Challan PDF."""
    employees = _get_employees_for_sc_record(statutory_record)
    scr = frappe.get_doc("Statutory Compliance Record", statutory_record)

    columns = ["#", "Employee Name", "Gross Wages", "PT Deducted"]
    rows = []
    tg = tp = 0.0

    for i, emp in enumerate(employees, 1):
        g = flt(emp.gross_wage)
        pt = flt(emp.pt_deduction)
        if pt > 0:
            rows.append([i, emp.employee_name, f"{g:.2f}", f"{pt:.2f}"])
            tg += g; tp += pt

    if not rows:
        frappe.msgprint(_("No PT deductions found for this period."), alert=True, indicator="orange")
        return

    html = _challan_html("PROFESSIONAL TAX CHALLAN", scr, rows,
                         [f"{tg:.2f}", "TOTAL", "", f"{tp:.2f}"], columns)
    filename = f"PT_Challan_{scr.contractor}_{scr.wage_month.replace('-', '_')}.pdf"
    return _save_pdf(html, filename)


@frappe.whitelist()
def generate_lwf_challan(statutory_record):
    """Generate Labour Welfare Fund Challan PDF."""
    employees = _get_employees_for_sc_record(statutory_record)
    scr = frappe.get_doc("Statutory Compliance Record", statutory_record)

    columns = ["#", "Employee Name", "Gross Wages", "LWF Deducted"]
    rows = []
    tg = tl = 0.0

    for i, emp in enumerate(employees, 1):
        g = flt(emp.gross_wage)
        lwf = flt(emp.lwf_deduction)
        if lwf > 0:
            rows.append([i, emp.employee_name, f"{g:.2f}", f"{lwf:.2f}"])
            tg += g; tl += lwf

    if not rows:
        frappe.msgprint(_("No LWF deductions found for this period."), alert=True, indicator="orange")
        return

    html = _challan_html("LABOUR WELFARE FUND CHALLAN", scr, rows,
                         [f"{tg:.2f}", "TOTAL", "", f"{tl:.2f}"], columns)
    filename = f"LWF_Challan_{scr.contractor}_{scr.wage_month.replace('-', '_')}.pdf"
    return _save_pdf(html, filename)
