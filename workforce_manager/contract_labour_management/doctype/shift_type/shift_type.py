import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, time_diff_in_hours


class ShiftType(Document):
	def validate(self):
		if self.start_time and self.end_time and self.start_time == self.end_time:
			frappe.throw("Start Time and End Time cannot be the same.")

	def get_standard_hours(self):
		"""Standard working hours for this shift, net of break, handling overnight shifts."""
		if not (self.start_time and self.end_time):
			return 8.0
		start = get_datetime(str(self.start_time))
		end = get_datetime(str(self.end_time))
		if end <= start:
			# overnight shift (e.g. 22:00 - 06:00)
			from datetime import timedelta
			end = end + timedelta(days=1)
		hours = time_diff_in_hours(end, start)
		break_hours = (self.break_duration or 0) / 60.0
		return max(hours - break_hours, 0)
