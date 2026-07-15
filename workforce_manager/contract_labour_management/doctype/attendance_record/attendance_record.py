import frappe
from frappe.model.document import Document
from frappe.utils import flt, time_diff_in_hours, get_datetime


class AttendanceRecord(Document):
	def validate(self):
		self.calculate_hours_and_ot()
		self.set_status()
		self.rollup_geofence_status()

	def calculate_hours_and_ot(self):
		if self.check_in_time and self.check_out_time:
			hours = time_diff_in_hours(get_datetime(self.check_out_time), get_datetime(self.check_in_time))
			self.hours_worked = round(max(hours, 0), 2)

			standard_hours = 8.0
			if self.shift:
				standard_hours = frappe.get_cached_doc("Shift Type", self.shift).get_standard_hours()

			self.ot_hours = round(max(self.hours_worked - standard_hours, 0), 2)
		elif self.check_in_time and not self.check_out_time:
			# Still on shift — don't guess hours worked yet
			self.hours_worked = self.hours_worked or 0
			self.ot_hours = self.ot_hours or 0

	def set_status(self):
		# Don't override an explicit manual "Leave" status
		if self.status == "Leave":
			return
		if self.check_in_time:
			if self.hours_worked and self.hours_worked < 4:
				self.status = "Half Day"
			else:
				self.status = "Present"
		else:
			self.status = "Absent"

	def rollup_geofence_status(self):
		"""Overall geofence status = 'Outside' if ANY check-in/out log was outside the site radius."""
		if not self.geofence_logs:
			return
		if any(row.status == "Outside" for row in self.geofence_logs):
			self.geofence_status = "Outside"
		else:
			self.geofence_status = "Inside"
