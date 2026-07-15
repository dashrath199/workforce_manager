# -*- coding: utf-8 -*-
"""
Runs once after `bench install-app workforce_manager` (see hooks.py after_install).
Creates the custom roles and a starter workspace with number cards so the
"Dashboard for workforce visibility" requirement is usable out of the box.
Wrapped defensively — a failure here should never block installation.
"""
import frappe


def after_install():
	_create_roles()
	_create_number_cards()
	_create_workspace()
	frappe.db.commit()


def _create_roles():
	for role in ["HR Manager", "Site Supervisor", "Contractor User"]:
		if not frappe.db.exists("Role", role):
			try:
				frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
					ignore_permissions=True
				)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Workforce Manager install: role creation failed")


def _number_card(label, document_type, function="Count", filters_json="[]", color="#2490EF"):
	if frappe.db.exists("Number Card", label):
		return
	try:
		frappe.get_doc({
			"doctype": "Number Card",
			"label": label,
			"document_type": document_type,
			"function": function,
			"filters_json": filters_json,
			"is_public": 1,
			"show_percentage_stats": 0,
			"color": color,
			"module": "Contract Labour Management",
		}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Workforce Manager install: Number Card '{label}' failed")


def _create_number_cards():
	_number_card("Active Employees", "Contract Employee",
	             filters_json='[["Contract Employee","status","=","Active"]]')
	_number_card("Total Sites", "Site")
	_number_card("Active Contractors", "Contractor")
	_number_card("Attendance Marked Today", "Attendance Record",
	             filters_json=f'[["Attendance Record","date","=","Today"]]')
	_number_card("Outside Geofence (Flagged)", "Attendance Record",
	             filters_json='[["Attendance Record","geofence_status","=","Outside"]]',
	             color="#FF5858")
	_number_card("Pending Statutory Compliance", "Statutory Compliance Record",
	             filters_json='[["Statutory Compliance Record","status","=","Pending"]]',
	             color="#FFA00A")


def _create_workspace():
	if frappe.db.exists("Workspace", "Workforce360"):
		return
	try:
		cards = [
			"Active Employees", "Total Sites", "Active Contractors",
			"Attendance Marked Today", "Outside Geofence (Flagged)",
			"Pending Statutory Compliance",
		]
		content = [{"id": "header", "type": "header",
		            "data": {"text": "<span class=\"h4\">Workforce360 — Overview</span>", "col": 12}}]
		for card in cards:
			content.append({
				"id": card.replace(" ", "_"),
				"type": "number_card",
				"data": {"number_card_name": card, "col": 4},
			})
		shortcuts = [
			{"type": "DocType", "label": "Contract Employee", "link_to": "Contract Employee", "doc_view": "List"},
			{"type": "DocType", "label": "Attendance Record", "link_to": "Attendance Record", "doc_view": "List"},
			{"type": "DocType", "label": "Wage Sheet", "link_to": "Wage Sheet", "doc_view": "List"},
			{"type": "DocType", "label": "Contractor Invoice", "link_to": "Contractor Invoice", "doc_view": "List"},
			{"type": "DocType", "label": "Statutory Compliance Record", "link_to": "Statutory Compliance Record", "doc_view": "List"},
			{"type": "Report", "label": "Site-wise Attendance Summary", "link_to": "Site-wise Attendance Summary"},
		]
		ws = frappe.get_doc({
			"doctype": "Workspace",
			"name": "Workforce360",
			"title": "Workforce360",
			"module": "Contract Labour Management",
			"public": 1,
			"is_hidden": 0,
			"icon": "contact",
			"content": frappe.as_json(content),
			"shortcuts": [dict(s, doctype="Workspace Shortcut") for s in shortcuts],
		})
		ws.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Workforce Manager install: workspace creation failed")
