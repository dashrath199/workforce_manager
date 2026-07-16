import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today, add_days


class Contractor(Document):
	def validate(self):
		self.create_or_link_vendor_account()
		self.set_legacy_registration_fields()
		self.validate_licenses()

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

	def set_legacy_registration_fields(self):
		"""Sync latest values from the Contractor Licenses table into the
		legacy single-value fields for backwards compatibility."""
		license_map = {
			"CLRA Registration": "license_no",
			"PF Registration": "pf_registration_no",
			"ESI Registration": "esi_registration_no",
			"PT Registration": "pt_registration_no",
			"LWF Registration": "lwf_registration_no",
		}
		for row in (self.contractor_licenses or []):
			legacy_field = license_map.get(row.license_type)
			if legacy_field and row.license_number:
				setattr(self, legacy_field, row.license_number)

	def validate_licenses(self):
		"""Warn if any active license has expired or is expiring soon."""
		today_date = getdate(today())
		cutoff_60 = add_days(today_date, 60)

		for row in (self.contractor_licenses or []):
			if not row.expiry_date:
				continue
			expiry = getdate(row.expiry_date)
			if expiry < today_date:
				frappe.msgprint(
					f"{row.license_type} ({row.license_number}) expired on {row.expiry_date}. "
					"Please submit a renewed copy.",
					indicator="red",
					alert=True,
				)
			elif expiry <= cutoff_60:
				frappe.msgprint(
					f"{row.license_type} ({row.license_number}) expires on {row.expiry_date}. "
					"Please arrange renewal.",
					indicator="orange",
					alert=True,
				)
