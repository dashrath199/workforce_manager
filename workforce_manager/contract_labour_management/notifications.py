# -*- coding: utf-8 -*-
"""Scheduled alerts: document expiry and statutory compliance due dates.
Runs daily via hooks.py scheduler_events. Creates Frappe Notification Log
entries for all users with the HR Manager role (visible in their bell icon).
"""
import frappe
from frappe.utils import getdate, today, add_days


def _notify_hr_managers(subject, message, document_type=None, document_name=None):
	users = frappe.get_all(
		"Has Role", filters={"role": "HR Manager", "parenttype": "User"}, pluck="parent"
	)
	for user in set(users):
		try:
			frappe.get_doc({
				"doctype": "Notification Log",
				"subject": subject,
				"for_user": user,
				"type": "Alert",
				"document_type": document_type,
				"document_name": document_name,
				"email_content": message,
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Workforce Manager: notification failed")


def send_expiry_alerts():
	"""Called daily (see hooks.py scheduler_events)."""
	_alert_expiring_documents()
	_alert_overdue_statutory_compliance()
	_alert_expiring_contractor_licenses()
	_alert_pending_ot_approvals()


def _alert_pending_ot_approvals():
	"""Alert HR Managers about pending overtime requests."""
	rows = frappe.get_all(
		"Overtime Request",
		filters={"status": ["in", ["Submitted", "Pending Supervisor"]]},
		fields=["name", "employee", "employee_name", "date", "requested_hours", "status"],
		order_by="creation asc",
	)

	pending_count = len(rows)
	if not pending_count:
		return

	# Group by status
	submitted = [r for r in rows if r.status == "Submitted"]
	pending_sup = [r for r in rows if r.status == "Pending Supervisor"]

	if submitted:
		_notify_hr_managers(
			subject=f"OT Approvals Needed: {len(submitted)} request(s) pending HR approval",
			message=(
				f"{len(submitted)} overtime request(s) are pending HR approval.\n"
				+ "\n".join(f"- {r.employee_name} ({r.employee}): {r.requested_hours}h on {r.date}" for r in submitted[:5])
				+ (f"\n... and {len(submitted)-5} more" if len(submitted) > 5 else "")
			),
			document_type="Overtime Request",
			document_name=submitted[0].name,
		)

	if pending_sup:
		_notify_hr_managers(
			subject=f"OT Pending Supervisor: {len(pending_sup)} request(s) awaiting supervisor approval",
			message=(
				f"{len(pending_sup)} overtime request(s) are awaiting site supervisor approval.\n"
				+ "\n".join(f"- {r.employee_name} ({r.employee}): {r.requested_hours}h on {r.date}" for r in pending_sup[:5])
				+ (f"\n... and {len(pending_sup)-5} more" if len(pending_sup) > 5 else "")
			),
			document_type="Overtime Request",
			document_name=pending_sup[0].name,
		)


def _alert_expiring_documents():
	cutoff = add_days(today(), 30)
	rows = frappe.db.sql("""
		SELECT `parent` as employee, `document_type`, `expiry_date`
		FROM `tabEmployee Document`
		WHERE `parenttype` = 'Contract Employee'
		  AND `expiry_date` IS NOT NULL
		  AND `expiry_date` <= %(cutoff)s
		  AND `expiry_date` >= %(today)s
	""", {"cutoff": cutoff, "today": today()}, as_dict=True)

	for row in rows:
		_notify_hr_managers(
			subject=f"Document expiring soon: {row.document_type} for {row.employee}",
			message=f"{row.document_type} for employee {row.employee} expires on {row.expiry_date}.",
			document_type="Contract Employee",
			document_name=row.employee,
		)


def _alert_expiring_contractor_licenses():
	"""Notify HR Managers about contractor licenses expiring within 60 days."""
	from frappe.utils import add_days, today
	cutoff = add_days(today(), 60)
	rows = frappe.db.sql("""
		SELECT cl.name, cl.parent as contractor, cl.license_type, cl.license_number, cl.expiry_date
		FROM `tabContractor License` cl
		WHERE cl.parenttype = 'Contractor'
		  AND cl.expiry_date IS NOT NULL
		  AND cl.expiry_date <= %(cutoff)s
		  AND cl.expiry_date >= %(today)s
		  AND cl.status != 'Expired'
	""", {"cutoff": cutoff, "today": today()}, as_dict=True)

	for row in rows:
		_notify_hr_managers(
			subject=f"Contractor license expiring: {row.license_type} for {row.contractor}",
			message=(
				f"{row.license_type} ({row.license_number}) for contractor {row.contractor} "
				f"expires on {row.expiry_date}. Please arrange renewal."
			),
			document_type="Contractor",
			document_name=row.contractor,
		)


def _alert_overdue_statutory_compliance():
	rows = frappe.get_all(
		"Statutory Compliance Record",
		filters={"status": "Pending", "due_date": ["<=", today()]},
		fields=["name", "contractor", "wage_month", "due_date", "total_amount"],
	)
	for row in rows:
		_notify_hr_managers(
			subject=f"Statutory compliance due: {row.contractor} ({row.wage_month})",
			message=(
				f"PF/ESI/PT/LWF filing for {row.contractor}, month {row.wage_month}, "
				f"amount {row.total_amount} was due on {row.due_date} and is still Pending."
			),
			document_type="Statutory Compliance Record",
			document_name=row.name,
		)
