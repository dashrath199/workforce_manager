import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "contractor", "label": "Contractor", "fieldtype": "Link", "options": "Contractor", "width": 150},
		{"fieldname": "wage_month", "label": "Wage Month", "fieldtype": "Data", "width": 100},
		{"fieldname": "posting_date", "label": "Posting Date", "fieldtype": "Date", "width": 110},
		{"fieldname": "total_wages", "label": "Total Wages", "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_service_charge", "label": "Service Charge", "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_gst", "label": "GST", "fieldtype": "Currency", "width": 110},
		{"fieldname": "invoice_value", "label": "Invoice Value", "fieldtype": "Currency", "width": 130},
		{"fieldname": "erpnext_purchase_invoice", "label": "Purchase Invoice", "fieldtype": "Link", "options": "Purchase Invoice", "width": 150},
	]

	conditions, values = ["docstatus < 2"], {}
	if filters.get("contractor"):
		conditions.append("contractor = %(contractor)s")
		values["contractor"] = filters["contractor"]
	if filters.get("from_date"):
		conditions.append("posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	data = frappe.db.sql(f"""
		SELECT `contractor`, `wage_month`, `posting_date`, `total_wages`,
		       `total_service_charge`, `total_gst`, `invoice_value`, `erpnext_purchase_invoice`
		FROM `tabContractor Invoice`
		WHERE {' AND '.join(conditions)}
		ORDER BY `posting_date` DESC
	""", values, as_dict=True)

	for row in data:
		for key in ("total_wages", "total_service_charge", "total_gst", "invoice_value"):
			row[key] = flt(row[key])

	return columns, data
