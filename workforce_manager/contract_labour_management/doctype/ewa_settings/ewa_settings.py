import frappe
from frappe.model.document import Document
from frappe.utils import flt


class EWASettings(Document):
	@frappe.whitelist()
	def get_eligibility(self, employee):
		"""Check EWA eligibility for a given employee."""
		return ewa_check_eligibility(employee)


def get_ewa_settings():
	"""Return the single EWA Settings doc (creates default if missing)."""
	name = frappe.db.get_value("EWA Settings", "EWA Settings")
	if name:
		return frappe.get_doc("EWA Settings", name)

	doc = frappe.new_doc("EWA Settings")
	doc.title = "EWA Settings"
	doc.insert(ignore_permissions=True)
	return doc


def ewa_check_eligibility(employee):
	"""Calculate EWA eligibility for a worker.

	Returns dict with:
	- eligible: bool
	- reason: str (why not eligible)
	- daily_wage_rate: float
	- days_attended_this_month: int
	- earned_amount: float
	- max_eligible_amount: float
	- already_requested: float
	- can_request_now: float
	- cooldown_remaining: int
	"""
	from frappe.utils import get_first_day, get_last_day, today, date_diff

	settings = get_ewa_settings()

	emp = frappe.get_cached_doc("Contract Employee", employee)
	if not emp:
		return {"eligible": False, "reason": "Employee not found"}

	# --- Restrictions ---
	if settings.require_kyc:
		if not (emp.aadhaar_verified and emp.pan_verified):
			return {"eligible": False, "reason": "KYC not completed (Aadhaar & PAN required)"}

	if settings.require_bank_details:
		if not (emp.bank_account_number and emp.ifsc_code):
			return {"eligible": False, "reason": "Bank details not on file"}

	# --- Calculate earned amount ---
	today_date = today()
	month_start = get_first_day(today_date)
	month_end = get_last_day(today_date)

	# Get daily wage rate from wage category
	daily_wage_rate = 0.0
	if emp.wage_category:
		daily_wage_rate = frappe.db.get_value("Wage Category", emp.wage_category, "minimum_wage_rate") or 0.0

	if daily_wage_rate <= 0:
		return {"eligible": False, "reason": "Wage category / rate not configured"}

	# Count present days this month
	attendance = frappe.get_all(
		"Attendance Record",
		filters={
			"employee": employee,
			"date": ["between", [month_start, month_end]],
			"status": ["in", ["Present", "Half Day"]],
		},
		fields=["status"],
	)

	days_attended = sum(1.0 for a in attendance if a.status == "Present")
	days_attended += sum(0.5 for a in attendance if a.status == "Half Day")

	if days_attended < settings.min_days_worked:
		return {
			"eligible": False,
			"reason": f"Only {int(days_attended)} day(s) attended this month. Minimum required: {settings.min_days_worked}",
			"days_attended": days_attended,
		}

	earned_amount = daily_wage_rate * days_attended
	max_eligible_amount = min(
		round(earned_amount * settings.max_advance_percentage / 100, 2),
		settings.max_advance_amount,
	)

	# --- Check existing requests this month ---
	result = frappe.db.sql("""
		SELECT COALESCE(SUM(requested_amount), 0) AS total
		FROM `tabEWA Request`
		WHERE employee = %s
		  AND status IN ('Submitted', 'Approved', 'Disbursed')
		  AND date BETWEEN %s AND %s
	""", (employee, month_start, month_end), as_dict=True)
	already_requested = flt(result[0].total) if result else 0.0

	can_request_now = max(0, round(max_eligible_amount - already_requested, 2))

	if can_request_now <= 0:
		return {
			"eligible": False,
			"reason": f"Already requested ₹{already_requested}. Maximum eligible this month is ₹{max_eligible_amount}",
			"already_requested": already_requested,
		}

	# --- Cooldown check ---
	last_request = frappe.get_all(
		"EWA Request",
		filters={"employee": employee, "status": ["in", ["Approved", "Disbursed"]]},
		fields=["name", "modified"],
		order_by="modified desc",
		limit_page_length=1,
	)

	cooldown_remaining = 0
	if last_request:
		from frappe.utils import date_diff
		days_since = date_diff(today_date, last_request[0].modified.strftime("%Y-%m-%d"))
		cooldown_remaining = max(0, settings.cooldown_days - days_since)
		if cooldown_remaining > 0:
			return {
				"eligible": False,
				"reason": f"Cooldown period active. Please wait {cooldown_remaining} more day(s).",
				"cooldown_remaining": cooldown_remaining,
			}

	return {
		"eligible": True,
		"reason": "",
		"daily_wage_rate": daily_wage_rate,
		"days_attended": days_attended,
		"earned_amount": round(earned_amount, 2),
		"max_eligible_amount": max_eligible_amount,
		"already_requested": already_requested,
		"can_request_now": can_request_now,
		"cooldown_remaining": 0,
	}
