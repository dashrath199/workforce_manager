import frappe
from frappe.model.document import Document
from frappe.utils import flt, now, today


class OvertimeRequest(Document):
	def validate(self):
		self.validate_hours()
		self.validate_duplicate()
		self.calculate_total_hours()
		self.set_employee_details()

	def set_employee_details(self):
		"""Fetch employee details from Contract Employee."""
		if self.employee:
			emp = frappe.get_cached_doc("Contract Employee", self.employee)
			self.employee_name = emp.first_name + (" " + (emp.last_name or "")).rstrip()
			self.site = emp.site
			self.contractor = emp.contractor

	def validate_hours(self):
		"""Validate OT hours against limits."""
		if flt(self.requested_hours) <= 0:
			frappe.throw("OT hours must be greater than zero.")

		from workforce_manager.contract_labour_management.doctype.overtime_settings.overtime_settings import (
			get_overtime_settings,
			validate_ot_hours,
		)

		settings = get_overtime_settings()
		validation = validate_ot_hours(
			self.employee, self.date, flt(self.requested_hours), settings
		)

		if not validation.get("valid"):
			frappe.throw(validation.get("reason"))

		# Auto-approve if hours are within auto-approve threshold
		auto_approve = flt(settings.auto_approve_up_to_hours) or 0
		if auto_approve > 0 and flt(self.requested_hours) <= auto_approve:
			self.status = "Approved"
			self.approved_by = "System (Auto-Approved)"
			self.approval_date = now()

	def validate_duplicate(self):
		"""Prevent duplicate OT requests for same employee+date."""
		if self.get_doc_before_save():
			return  # Existing doc being modified

		existing = frappe.db.get_value(
			"Overtime Request",
			{
				"employee": self.employee,
				"date": self.date,
				"status": ["in", ["Submitted", "Approved"]],
				"name": ["!=", self.name or ""],
			},
			"name",
		)
		if existing:
			frappe.throw(
				f"An active Overtime Request ({existing}) already exists for "
				f"{self.employee} on {self.date}."
			)

	def calculate_total_hours(self):
		"""Set approved_hours from requested_hours if not set."""
		if not self.approved_hours:
			self.approved_hours = flt(self.requested_hours)

	@frappe.whitelist()
	def approve(self, approved_hours=None):
		"""Approve the overtime request."""
		if self.status not in ("Submitted", "Pending Supervisor"):
			frappe.throw("Only submitted requests can be approved.")

		if approved_hours is not None:
			self.approved_hours = flt(approved_hours)

		if self.approved_hours <= 0:
			frappe.throw("Approved hours must be greater than zero.")

		self.status = "Approved"
		self.approved_by = frappe.session.user
		self.approval_date = now()
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def reject(self, reason=None):
		"""Reject the overtime request."""
		if self.status not in ("Submitted", "Pending Supervisor"):
			frappe.throw("Only submitted requests can be rejected.")
		self.status = "Rejected"
		self.hr_remarks = reason or ""
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def approve_supervisor(self):
		"""Site Supervisor pre-approval step (moves to HR approval)."""
		if self.status != "Pending Supervisor":
			frappe.throw("Request is not in Pending Supervisor state.")
		self.status = "Submitted"
		self.supervisor_approved_by = frappe.session.user
		self.supervisor_approved_date = now()
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def get_ot_rate_info(self):
		"""Return the applicable OT rate for this request."""
		from workforce_manager.contract_labour_management.doctype.overtime_settings.overtime_settings import (
			get_overtime_settings, get_ot_rate
		)
		settings = get_overtime_settings()
		rate = get_ot_rate(settings, self.ot_category)
		return {
			"rate_multiplier": rate,
			"category": self.ot_category,
			"description": f"{rate}x for {self.ot_category} OT",
		}
