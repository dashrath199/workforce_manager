import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class ContractEmployee(Document):
	def validate(self):
		self.validate_contractor_deployed_at_site()
		self.validate_aadhaar()

	def validate_contractor_deployed_at_site(self):
		"""
		Employees remain on their Contractor's payroll — they can only be
		mapped to a Site where that Contractor is actively deployed
		(per Site Contractor Mapping), not just any site.
		"""
		if not (self.contractor and self.site):
			return

		site_doc = frappe.get_cached_doc("Site", self.site)
		mapping = None
		for row in (site_doc.contractors or []):
			if row.contractor == self.contractor:
				mapping = row
				break

		if not mapping:
			frappe.throw(
				f"Contractor {frappe.bold(self.contractor)} is not deployed at Site "
				f"{frappe.bold(self.site)}. Add a Site Contractor Mapping first."
			)

		if mapping.status == "Inactive":
			frappe.throw(
				f"Contractor {frappe.bold(self.contractor)}'s deployment at Site "
				f"{frappe.bold(self.site)} is marked Inactive."
			)

		if mapping.deployment_end_date and getdate(mapping.deployment_end_date) < getdate(today()):
			frappe.throw(
				f"Contractor {frappe.bold(self.contractor)}'s deployment at Site "
				f"{frappe.bold(self.site)} ended on {mapping.deployment_end_date}."
			)

	def validate_aadhaar(self):
		if self.aadhaar_number:
			digits = "".join(ch for ch in self.aadhaar_number if ch.isdigit())
			if len(digits) != 12:
				frappe.throw("Aadhaar Number must be exactly 12 digits.")
			self.aadhaar_number = digits
