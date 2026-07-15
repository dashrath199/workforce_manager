import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class StatutoryComplianceRecord(Document):
	def validate(self):
		self.status = "Paid" if self.payment_date else "Pending"

	def is_overdue(self):
		return self.status == "Pending" and self.due_date and getdate(self.due_date) < getdate(today())
