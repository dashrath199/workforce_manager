import frappe
from frappe.model.document import Document


class Contractor(Document):
	def validate(self):
		self.create_or_link_vendor_account()

	def create_or_link_vendor_account(self):
		"""
		Employees mapped to this Contractor stay on the Contractor's payroll —
		the Contractor itself is our client's vendor for billing/GST purposes.
		Auto-create the corresponding ERPNext Supplier the first time a
		Contractor is saved, so invoicing has somewhere to post to.
		"""
		if self.vendor_account:
			return
		if not self.contractor_name:
			return

		existing = frappe.db.get_value("Supplier", {"supplier_name": self.contractor_name}, "name")
		if existing:
			self.vendor_account = existing
			return

		try:
			supplier = frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": self.contractor_name,
				"supplier_group": frappe.db.get_value("Supplier Group", {}, "name") or "All Supplier Groups",
				"supplier_type": "Company",
				"tax_id": self.pf_registration_no or None,
			})
			supplier.insert(ignore_permissions=True, ignore_mandatory=True)
			self.vendor_account = supplier.name
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Contractor: Supplier auto-creation failed")
