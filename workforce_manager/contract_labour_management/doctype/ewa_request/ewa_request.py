import frappe
from frappe.model.document import Document
from frappe.utils import flt, now, today


class EWARequest(Document):
	def validate(self):
		self.validate_amount()
		self.validate_duplicate()

	def validate_amount(self):
		if flt(self.requested_amount) <= 0:
			frappe.throw("Requested amount must be greater than zero.")

		if self.max_eligible_amount and flt(self.requested_amount) > flt(self.max_eligible_amount):
			frappe.throw(
				f"Requested amount ₹{self.requested_amount:,.2f} exceeds "
				f"maximum eligible amount ₹{self.max_eligible_amount:,.2f}."
			)

	def validate_duplicate(self):
		if self.get_doc_before_save():
			return  # Not a new doc

		existing = frappe.db.get_value(
			"EWA Request",
			{
				"employee": self.employee,
				"status": ["in", ["Submitted", "Approved", "Disbursed"]],
				"date": today(),
			},
			"name",
		)
		if existing:
			frappe.throw(f"An active EWA Request ({existing}) already exists for this employee.")

	@frappe.whitelist()
	def approve(self):
		"""Approve the EWA request."""
		if self.status != "Submitted":
			frappe.throw("Only Submitted requests can be approved.")
		self.status = "Approved"
		self.approved_by = frappe.session.user
		self.approved_date = now()
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def reject(self, reason=None):
		"""Reject the EWA request."""
		if self.status != "Submitted":
			frappe.throw("Only Submitted requests can be rejected.")
		self.status = "Rejected"
		self.hr_remarks = reason
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def mark_disbursed(self, amount=None):
		"""Mark as disbursed."""
		if self.status != "Approved":
			frappe.throw("Only Approved requests can be marked as disbursed.")
		self.status = "Disbursed"
		self.disbursed_amount = flt(amount) if amount else flt(self.requested_amount)
		self.disbursed_by = frappe.session.user
		self.disbursed_date = now()
		self.save(ignore_permissions=True)
