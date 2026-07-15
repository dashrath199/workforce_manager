import frappe
from frappe.utils import getdate, today, date_diff


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Contract Employee", "width": 150},
		{"fieldname": "document_type", "label": "Document Type", "fieldtype": "Link", "options": "Onboarding Document Type", "width": 150},
		{"fieldname": "document_number", "label": "Document Number", "fieldtype": "Data", "width": 130},
		{"fieldname": "expiry_date", "label": "Expiry Date", "fieldtype": "Date", "width": 110},
		{"fieldname": "days_to_expiry", "label": "Days to Expiry", "fieldtype": "Int", "width": 110},
		{"fieldname": "verified", "label": "Verified", "fieldtype": "Check", "width": 90},
	]

	conditions, values = ["`parenttype` = 'Contract Employee'", "`expiry_date` IS NOT NULL"], {}
	if filters.get("document_type"):
		conditions.append("`document_type` = %(document_type)s")
		values["document_type"] = filters["document_type"]
	if filters.get("only_unverified"):
		conditions.append("`verified` = 0")

	data = frappe.db.sql(f"""
		SELECT `parent` as employee, `document_type`, `document_number`, `expiry_date`, `verified`
		FROM `tabEmployee Document`
		WHERE {' AND '.join(conditions)}
		ORDER BY `expiry_date` ASC
	""", values, as_dict=True)

	within_days = filters.get("within_days")
	today_date = getdate(today())
	filtered = []
	for row in data:
		row["days_to_expiry"] = date_diff(row["expiry_date"], today_date)
		if within_days and row["days_to_expiry"] > int(within_days):
			continue
		filtered.append(row)

	return columns, filtered
