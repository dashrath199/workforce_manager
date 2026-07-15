import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class EmployeeDocument(Document):
	def validate(self):
		if self.expiry_date and getdate(self.expiry_date) < getdate(today()):
			# Don't block saving old records, just make sure it can't silently be "Verified"
			if self.verified:
				frappe.msgprint(
					f"{self.document_type or 'This document'} expired on {self.expiry_date} but is marked Verified. "
					"Please confirm a renewed document has been collected.",
					indicator="orange",
					alert=True,
				)
