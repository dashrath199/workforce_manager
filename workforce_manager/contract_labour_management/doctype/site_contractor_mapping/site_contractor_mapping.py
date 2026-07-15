import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class SiteContractorMapping(Document):
	def validate(self):
		if self.deployment_start_date and self.deployment_end_date:
			if getdate(self.deployment_end_date) < getdate(self.deployment_start_date):
				frappe.throw("Deployment End Date cannot be before Deployment Start Date.")
