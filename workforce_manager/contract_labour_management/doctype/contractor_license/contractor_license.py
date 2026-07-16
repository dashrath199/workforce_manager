import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today, add_days


class ContractorLicense(Document):
	def validate(self):
		self.update_status_based_on_expiry()

	def update_status_based_on_expiry(self):
		"""Auto-set status based on expiry_date."""
		if not self.expiry_date:
			return

		expiry = getdate(self.expiry_date)
		today_date = getdate(today())

		if expiry < today_date:
			self.status = "Expired"
		elif expiry <= add_days(today_date, 60):
			self.status = "Expiring Soon"
