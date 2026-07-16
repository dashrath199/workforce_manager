import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, today


class LeaveRequest(Document):
	def validate(self):
		self.validate_dates()
		self.calculate_total_days()

	def validate_dates(self):
		if self.from_date and self.to_date:
			if getdate(self.from_date) > getdate(self.to_date):
				frappe.throw("From Date cannot be after To Date.")

	def calculate_total_days(self):
		if self.from_date and self.to_date:
			self.total_days = date_diff(getdate(self.to_date), getdate(self.from_date)) + 1
