# -*- coding: utf-8 -*-
"""
Whitelisted API endpoints for the mobile attendance app (GPS check-in/out)
and the Contract Labour Management workspace dashboard.

Mobile app usage:
  POST /api/method/workforce_manager.contract_labour_management.api.mobile_check_in
       {employee, latitude, longitude}
  POST /api/method/workforce_manager.contract_labour_management.api.mobile_check_out
       {employee, latitude, longitude}

Dashboard (workspace) usage:
  POST /api/method/workforce_manager.contract_labour_management.api.get_workspace_kpis
  POST /api/method/workforce_manager.contract_labour_management.api.get_workspace_alerts
  POST /api/method/workforce_manager.contract_labour_management.api.get_attendance_percentage
  POST /api/method/workforce_manager.contract_labour_management.api.get_documents_expiring_count
  POST /api/method/workforce_manager.contract_labour_management.api.get_employee_distribution
  POST /api/method/workforce_manager.contract_labour_management.api.get_contractor_distribution
"""
import json
from datetime import datetime, timedelta

import frappe
from frappe.utils import now_datetime, today, flt, add_days, getdate, formatdate

from workforce_manager.contract_labour_management.utils import (
	haversine_distance_m,
	GEOFENCE_DEFAULT_RADIUS_M,
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _resolve_employee_and_site(employee, site=None):
	emp = frappe.get_doc("Contract Employee", employee)
	if emp.status != "Active":
		frappe.throw(f"Employee {employee} is not Active.")
	site_name = site or emp.site
	if not site_name:
		frappe.throw(f"Employee {employee} has no Site assigned and none was provided.")
	site_doc = frappe.get_doc("Site", site_name)
	return emp, site_doc


def _geofence_status(site_doc, latitude, longitude):
	if latitude is None or longitude is None or not (site_doc.geofence_lat and site_doc.geofence_long):
		return "Inside", None  # can't evaluate -> don't penalize the worker
	distance = haversine_distance_m(site_doc.geofence_lat, site_doc.geofence_long, latitude, longitude)
	radius = flt(site_doc.geofence_radius) or GEOFENCE_DEFAULT_RADIUS_M
	status = "Inside" if distance is not None and distance <= radius else "Outside"
	return status, distance


def _append_geofence_log(attendance, latitude, longitude, status):
	attendance.append("geofence_logs", {
		"log_time": now_datetime(),
		"latitude": latitude,
		"longitude": longitude,
		"status": status,
	})


# ---------------------------------------------------------------------------
#  Mobile check-in / check-out
# ---------------------------------------------------------------------------

@frappe.whitelist()
def mobile_check_in(employee, latitude=None, longitude=None, site=None):
	emp, site_doc = _resolve_employee_and_site(employee, site)

	attendance_date = today()
	existing = frappe.db.get_value(
		"Attendance Record",
		{"employee": employee, "date": attendance_date},
		"name",
	)
	if existing:
		att = frappe.get_doc("Attendance Record", existing)
		if att.check_in_time:
			frappe.throw(f"{employee} has already checked in today at {att.check_in_time}.")
	else:
		att = frappe.new_doc("Attendance Record")
		att.employee = employee
		att.site = site_doc.name
		att.shift = emp.shift
		att.date = attendance_date

	status, distance = _geofence_status(site_doc, latitude, longitude)
	att.check_in_time = now_datetime()
	att.attendance_source = "Mobile App (GPS)"
	_append_geofence_log(att, latitude, longitude, status)

	att.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"attendance_record": att.name,
		"check_in_time": att.check_in_time,
		"geofence_status": status,
		"distance_m": round(distance, 1) if distance is not None else None,
		"message": "Checked in successfully" if status == "Inside" else
		           "Checked in, but you appear to be outside the site geofence. This has been flagged for review.",
	}


@frappe.whitelist()
def mobile_check_out(employee, latitude=None, longitude=None, site=None):
	emp, site_doc = _resolve_employee_and_site(employee, site)

	attendance_date = today()
	existing = frappe.db.get_value(
		"Attendance Record",
		{"employee": employee, "date": attendance_date},
		"name",
	)
	if not existing:
		frappe.throw(f"No check-in found for {employee} today. Please check in first.")

	att = frappe.get_doc("Attendance Record", existing)
	if att.check_out_time:
		frappe.throw(f"{employee} has already checked out today at {att.check_out_time}.")

	status, distance = _geofence_status(site_doc, latitude, longitude)
	att.check_out_time = now_datetime()
	_append_geofence_log(att, latitude, longitude, status)

	att.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"attendance_record": att.name,
		"check_out_time": att.check_out_time,
		"hours_worked": att.hours_worked,
		"ot_hours": att.ot_hours,
		"geofence_status": status,
		"distance_m": round(distance, 1) if distance is not None else None,
	}


@frappe.whitelist()
def get_my_today_attendance(employee):
	"""Convenience call for the mobile app to render current check-in state."""
	name = frappe.db.get_value("Attendance Record", {"employee": employee, "date": today()}, "name")
	if not name:
		return None
	return frappe.get_doc("Attendance Record", name).as_dict()


# ---------------------------------------------------------------------------
#  Workspace Dashboard – KPI data (for Number Cards using "Custom" type)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_workspace_kpis():
	"""Return all KPI values in one call for a custom dashboard refresh."""
	today_str = today()
	active_employees = frappe.db.count("Contract Employee", filters={"status": "Active"})
	todays_attendance = frappe.db.count("Attendance Record", filters={"date": today_str})
	total_attendance = frappe.db.count("Attendance Record", filters={"date": today_str, "status": ["!=", "Absent"]})
	attendance_pct = round((total_attendance / todays_attendance * 100) if todays_attendance else 0, 1)

	return {
		"active_employees": active_employees,
		"todays_attendance": todays_attendance,
		"attendance_percentage": attendance_pct,
		"active_contractors": frappe.db.count("Contractor"),
		"active_sites": frappe.db.count("Site"),
		"pending_compliance": frappe.db.count("Statutory Compliance Record", filters={"status": "Pending"}),
		"documents_expiring": frappe.db.count("Employee Document", filters={"expiry_date": ["<=", add_days(today_str, 30)]}),
		"outside_geofence": frappe.db.count("Attendance Record", filters={"date": today_str, "geofence_status": "Outside"}),
	}


@frappe.whitelist()
def get_attendance_percentage():
	"""Custom Number Card – return today's attendance percentage."""
	today_str = today()
	total = frappe.db.count("Attendance Record", filters={"date": today_str})
	if not total:
		return {"value": 0, "fieldtype": "Percent"}
	present = frappe.db.count("Attendance Record", filters={"date": today_str, "status": ["!=", "Absent"]})
	pct = round(present / total * 100, 1)
	return {"value": pct, "fieldtype": "Percent"}


@frappe.whitelist()
def get_todays_attendance_count():
	"""Custom Number Card – count today's attendance records."""
	today_str = today()
	count = frappe.db.count("Attendance Record", filters={"date": today_str})
	return {"value": count, "fieldtype": "Int"}


@frappe.whitelist()
def get_outside_geofence_count():
	"""Custom Number Card – count attendance records outside geofence today."""
	today_str = today()
	count = frappe.db.count("Attendance Record", filters={"date": today_str, "geofence_status": "Outside"})
	return {"value": count, "fieldtype": "Int"}


@frappe.whitelist()
def get_documents_expiring_count():
	"""Custom Number Card – count documents expiring within 30 days."""
	today_str = today()
	cutoff = add_days(today_str, 30)
	count = frappe.db.count("Employee Document", filters={"expiry_date": ["between", [today_str, cutoff]]})
	return {"value": count, "fieldtype": "Int"}


# ---------------------------------------------------------------------------
#  Workspace Dashboard – Chart data (for custom Dashboard Chart Sources)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_employee_distribution():
	"""Return employee distribution by Site for a pie/bar chart."""
	today_str = today()
	# Group active employees by site
	data = frappe.db.get_all(
		"Contract Employee",
		filters={"status": "Active"},
		fields=["site", "count(*) as count"],
		group_by="site",
		order_by="count desc",
	)
	labels = [row["site"] or "Unassigned" for row in data]
	values = [row["count"] for row in data]
	return {
		"labels": labels,
		"datasets": [
			{"name": "Employees", "values": values}
		],
		"type": "pie",
	}


@frappe.whitelist()
def get_contractor_distribution():
	"""Return contractor distribution by Site for a bar chart."""
	data = frappe.db.get_all(
		"Site Contractor Mapping",
		fields=["parent as site", "count(*) as count"],
		group_by="parent",
		order_by="count desc",
	)
	labels = [row["site"] for row in data]
	values = [row["count"] for row in data]
	return {
		"labels": labels,
		"datasets": [
			{"name": "Contractors", "values": values}
		],
		"type": "bar",
	}


# ---------------------------------------------------------------------------
#  Workspace Dashboard – Alerts and notifications
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_workspace_alerts():
	"""Return alerts / notifications for the workspace banner."""
	today_str = today()
	cutoff_30 = add_days(today_str, 30)

	# 1. Documents expiring within 30 days
	expiring_docs = frappe.db.get_all(
		"Employee Document",
		filters={"expiry_date": ["between", [today_str, cutoff_30]]},
		fields=["name", "employee", "document_type", "expiry_date"],
		order_by="expiry_date asc",
		limit=10,
	)

	# 2. Compliance due (status = Pending)
	pending_compliance = frappe.db.get_all(
		"Statutory Compliance Record",
		filters={"status": "Pending"},
		fields=["name", "compliance_type", "due_date"],
		order_by="due_date asc",
		limit=10,
	)

	# 3. GPS violations today (geofence_status = Outside)
	gps_violations = frappe.db.count("Attendance Record", filters={"date": today_str, "geofence_status": "Outside"})

	# 4. Wage sheets in Draft
	pending_wage_sheets = frappe.db.count("Wage Sheet", filters={"status": "Draft"})

	# 5. Contractor invoices pending approval
	pending_invoices = frappe.db.count("Contractor Invoice", filters={"docstatus": 0})

	alerts = []
	for doc in expiring_docs:
		days_left = (getdate(doc.expiry_date) - getdate(today_str)).days
		alerts.append({
			"type": "warning",
			"icon": "file-text",
			"title": f"Document Expiring: {doc.document_type}",
			"message": f"{doc.employee} – expires in {days_left} day(s) on {formatdate(doc.expiry_date)}",
			"route": f"/app/employee-document/{doc.name}",
		})

	for rec in pending_compliance:
		days_overdue = (getdate(today_str) - getdate(rec.due_date)).days if rec.due_date else 0
		status_text = f"overdue by {days_overdue} day(s)" if days_overdue > 0 else f"due on {formatdate(rec.due_date)}" if rec.due_date else "no due date"
		alerts.append({
			"type": "danger",
			"icon": "alert-triangle",
			"title": f"Compliance: {rec.compliance_type}",
			"message": f"{status_text}",
			"route": f"/app/statutory-compliance-record/{rec.name}",
		})

	if gps_violations:
		alerts.append({
			"type": "warning",
			"icon": "map-pin",
			"title": "GPS Violations Today",
			"message": f"{gps_violations} employee(s) checked in/out outside the geofence",
			"route": "/app/attendance-record?date=today&geofence_status=Outside",
		})

	if pending_wage_sheets:
		alerts.append({
			"type": "info",
			"icon": "dollar-sign",
			"title": "Wage Sheets Pending",
			"message": f"{pending_wage_sheets} wage sheet(s) are still in Draft",
			"route": "/app/wage-sheet?status=Draft",
		})

	if pending_invoices:
		alerts.append({
			"type": "info",
			"icon": "file",
			"title": "Invoices Pending Approval",
			"message": f"{pending_invoices} contractor invoice(s) awaiting approval",
			"route": "/app/contractor-invoice?docstatus=0",
		})

	return {
		"alerts": alerts,
		"counts": {
			"expiring_documents": len(expiring_docs),
			"compliance_due": len(pending_compliance),
			"gps_violations": gps_violations,
			"wage_sheets_pending": pending_wage_sheets,
			"invoices_pending": pending_invoices,
		}
	}
