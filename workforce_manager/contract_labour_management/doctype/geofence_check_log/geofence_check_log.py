import frappe
from frappe.model.document import Document


class GeofenceCheckLog(Document):
	def validate(self):
		if not self.status:
			self.status = "Inside"
