import frappe
from frappe.utils import flt, getdate, today


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "contractor", "label": "Contractor", "fieldtype": "Link", "options": "Contractor", "width": 150},
		{"fieldname": "wage_month", "label": "Wage Month", "fieldtype": "Data", "width": 100},
		{"fieldname": "due_date", "label": "Due Date", "fieldtype": "Date", "width": 100},
		{"fieldname": "payment_date", "label": "Payment Date", "fieldtype": "Date", "width": 110},
		{"fieldname": "total_amount", "label": "Total Amount", "fieldtype": "Currency", "width": 130},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 90},
		{"fieldname": "overdue", "label": "Overdue?", "fieldtype": "Data", "width": 90},
	]

	conditions, values = ["docstatus < 2"], {}
	if filters.get("contractor"):
		conditions.append("contractor = %(contractor)s")
		values["contractor"] = filters["contractor"]
	if filters.get("wage_month"):
		conditions.append("wage_month = %(wage_month)s")
		values["wage_month"] = filters["wage_month"]
	if filters.get("status"):
		conditions.append("status = %(status)s")
		values["status"] = filters["status"]

	data = frappe.db.sql(f"""
		SELECT `contractor`, `wage_month`, `due_date`, `payment_date`, `total_amount`, `status`
		FROM `tabStatutory Compliance Record`
		WHERE {' AND '.join(conditions)}
		ORDER BY `due_date` ASC
	""", values, as_dict=True)

	today_date = getdate(today())
	filtered = []
	for row in data:
		row["total_amount"] = flt(row["total_amount"])
		row["overdue"] = "Yes" if (row["status"] == "Pending" and row["due_date"] and getdate(row["due_date"]) < today_date) else "No"
		if filters.get("only_overdue") and row["overdue"] != "Yes":
			continue
		filtered.append(row)

	return columns, filtered
