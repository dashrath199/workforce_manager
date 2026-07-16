import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "site", "label": "Site", "fieldtype": "Link", "options": "Site", "width": 150},
		{"fieldname": "shift", "label": "Shift", "fieldtype": "Link", "options": "Shift Type", "width": 120},
		{"fieldname": "present_days", "label": "Present", "fieldtype": "Int", "width": 90},
		{"fieldname": "half_days", "label": "Half Day", "fieldtype": "Int", "width": 90},
		{"fieldname": "absent_days", "label": "Absent", "fieldtype": "Int", "width": 90},
		{"fieldname": "leave_days", "label": "Leave", "fieldtype": "Int", "width": 90},
		{"fieldname": "total_hours", "label": "Total Hours", "fieldtype": "Float", "width": 110},
		{"fieldname": "total_ot_hours", "label": "Total OT Hours", "fieldtype": "Float", "width": 120},
		{"fieldname": "outside_geofence", "label": "Outside Geofence (flagged)", "fieldtype": "Int", "width": 160},
	]

	conditions, values = ["ar.docstatus < 2"], {}
	if filters.get("from_date"):
		conditions.append("ar.date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("ar.date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("site"):
		conditions.append("ar.site = %(site)s")
		values["site"] = filters["site"]
	if filters.get("shift"):
		conditions.append("ar.shift = %(shift)s")
		values["shift"] = filters["shift"]
	if filters.get("contractor"):
		conditions.append("ce.contractor = %(contractor)s")
		values["contractor"] = filters["contractor"]

	data = frappe.db.sql(f"""
		SELECT
			ar.site as site,
			ar.shift as shift,
			SUM(CASE WHEN ar.status = 'Present' THEN 1 ELSE 0 END) as present_days,
			SUM(CASE WHEN ar.status = 'Half Day' THEN 1 ELSE 0 END) as half_days,
			SUM(CASE WHEN ar.status = 'Absent' THEN 1 ELSE 0 END) as absent_days,
			SUM(CASE WHEN ar.status = 'Leave' THEN 1 ELSE 0 END) as leave_days,
			SUM(ar.hours_worked) as total_hours,
			SUM(ar.ot_hours) as total_ot_hours,
			SUM(CASE WHEN ar.geofence_status = 'Outside' THEN 1 ELSE 0 END) as outside_geofence
		FROM `tabAttendance Record` ar
		LEFT JOIN `tabContract Employee` ce ON ce.name = ar.employee
		WHERE {' AND '.join(conditions)}
		GROUP BY ar.site, ar.shift
		ORDER BY ar.site
	""", values, as_dict=True)

	for row in data:
		row["total_hours"] = flt(row["total_hours"])
		row["total_ot_hours"] = flt(row["total_ot_hours"])

	return columns, data
