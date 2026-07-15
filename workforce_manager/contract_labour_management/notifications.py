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
