import frappe
from frappe.model.document import Document
from frappe.utils import flt


class OvertimeSettings(Document):
	pass


def get_overtime_settings():
	"""Return the single Overtime Settings doc (creates default if missing)."""
	name = frappe.db.get_value("Overtime Settings", "Overtime Settings")
	if name:
		return frappe.get_doc("Overtime Settings", name)

	doc = frappe.new_doc("Overtime Settings")
	doc.title = "Overtime Settings"
	doc.insert(ignore_permissions=True)
	return doc


def get_ot_rate(overtime_settings=None, ot_category="Regular"):
	"""Get the OT rate multiplier based on category.

	Args:
	    overtime_settings: Overtime Settings doc (fetched if None)
	    ot_category: "Regular", "Holiday", or "Night Shift"

	Returns:
	    float: OT rate multiplier (e.g. 2.0 for 2x)
	"""
	settings = overtime_settings or get_overtime_settings()

	if ot_category == "Holiday":
		return flt(settings.holiday_ot_rate) or 3.0
	elif ot_category == "Night Shift":
		return flt(settings.night_shift_ot_rate) or 2.5
	else:
		return flt(settings.regular_ot_rate) or 2.0


def validate_ot_hours(employee, date, requested_hours, overtime_settings=None):
	"""Validate OT hours against max daily/weekly limits.

	Returns:
	    dict with:
	    - valid: bool
	    - reason: str (why not valid)
	    - daily_used: float
	    - weekly_used: float
	"""
	from frappe.utils import getdate, add_days

	settings = overtime_settings or get_overtime_settings()
	max_daily = flt(settings.max_ot_hours_per_day) or 4.0
	max_weekly = flt(settings.max_ot_hours_per_week) or 12.0

	# Check daily limit
	existing_daily = frappe.db.sql("""
		SELECT COALESCE(SUM(ot_hours), 0) AS total
		FROM `tabAttendance Record`
		WHERE employee = %s AND date = %s AND docstatus < 2
	""", (employee, date), as_dict=True)
	daily_used = flt(existing_daily[0].total) if existing_daily else 0.0

	if daily_used + requested_hours > max_daily:
		return {
			"valid": False,
			"reason": f"Requested {requested_hours}h exceeds daily limit of {max_daily}h "
			          f"(already used {daily_used}h today).",
			"daily_used": daily_used,
			"weekly_used": 0,
		}

	# Check weekly limit (from Mon-Sun or rolling 7 days)
	att_date = getdate(date)
	week_start = add_days(att_date, -6)  # rolling 7 days

	existing_weekly = frappe.db.sql("""
		SELECT COALESCE(SUM(ot_hours), 0) AS total
		FROM `tabAttendance Record`
		WHERE employee = %s AND date BETWEEN %s AND %s AND docstatus < 2
	""", (employee, week_start, date), as_dict=True)
	weekly_used = flt(existing_weekly[0].total) if existing_weekly else 0.0

	if weekly_used + requested_hours > max_weekly:
		return {
			"valid": False,
			"reason": f"Requested {requested_hours}h exceeds weekly limit of {max_weekly}h "
			          f"(already used {weekly_used}h this week).",
			"daily_used": daily_used,
			"weekly_used": weekly_used,
		}

	return {
		"valid": True,
		"reason": "",
		"daily_used": daily_used,
		"weekly_used": weekly_used,
	}
