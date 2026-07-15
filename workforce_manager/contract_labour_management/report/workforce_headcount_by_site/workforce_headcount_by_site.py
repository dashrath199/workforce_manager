import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "site", "label": "Site", "fieldtype": "Link", "options": "Site", "width": 150},
		{"fieldname": "contractor", "label": "Contractor", "fieldtype": "Link", "options": "Contractor", "width": 180},
		{"fieldname": "headcount", "label": "Headcount", "fieldtype": "Int", "width": 100},
	]

	conditions, values = ["1=1"], {}
	if filters.get("site"):
		conditions.append("site = %(site)s")
		values["site"] = filters["site"]
	if filters.get("contractor"):
		conditions.append("contractor = %(contractor)s")
		values["contractor"] = filters["contractor"]
	if filters.get("status"):
		conditions.append("status = %(status)s")
		values["status"] = filters["status"]

	data = frappe.db.sql(f"""
		SELECT `site`, `contractor`, COUNT(`name`) as headcount
		FROM `tabContract Employee`
		WHERE {' AND '.join(conditions)}
		GROUP BY `site`, `contractor`
		ORDER BY `site`, `headcount` DESC
	""", values, as_dict=True)

	for row in data:
		row["headcount"] = int(flt(row["headcount"]))

	return columns, data
