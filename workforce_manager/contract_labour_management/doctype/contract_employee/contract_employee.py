import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today
import re


class ContractEmployee(Document):
	def validate(self):
		self.validate_contractor_deployed_at_site()
		self.validate_aadhaar()
		self.validate_pan()
		self.validate_ifsc()
		self.validate_uan()
		self.validate_mobile()
		self.update_onboarding_status()

	# ---------------------------------------------------------------------------
	#  Verhoeff check-digit algorithm for Aadhaar
	# ---------------------------------------------------------------------------

	_verhoeff_d = [
		[0,1,2,3,4,5,6,7,8,9],
		[1,2,3,4,0,6,7,8,9,5],
		[2,3,4,0,1,7,8,9,5,6],
		[3,4,0,1,2,8,9,5,6,7],
		[4,0,1,2,3,9,5,6,7,8],
		[5,9,8,7,6,0,4,3,2,1],
		[6,5,9,8,7,1,0,4,3,2],
		[7,6,5,9,8,2,1,0,4,3],
		[8,7,6,5,9,3,2,1,0,4],
		[9,8,7,6,5,4,3,2,1,0],
	]
	_verhoeff_p = [
		[0,1,2,3,4,5,6,7,8,9],
		[1,5,7,6,2,8,3,0,9,4],
		[5,8,0,3,7,9,6,1,4,2],
		[8,9,1,6,0,4,3,5,2,7],
		[9,4,5,3,1,2,6,8,7,0],
		[4,2,8,6,5,7,3,9,0,1],
		[2,7,9,3,8,0,6,4,1,5],
		[7,0,4,6,9,1,3,2,5,8],
	]
	_verhoeff_inv = [0,4,3,2,1,5,6,7,8,9]

	@staticmethod
	def _verify_verhoeff(num_str):
		"""Return True if num_str passes the Verhoeff check-digit algorithm."""
		try:
			digits = [int(ch) for ch in num_str if ch.isdigit()]
			c = 0
			for i, d in enumerate(reversed(digits)):
				c = ContractEmployee._verhoeff_d[c][ContractEmployee._verhoeff_p[i % 8][d]]
			return c == 0
		except (ValueError, IndexError):
			return False

	# ---------------------------------------------------------------------------
	#  Validators
	# ---------------------------------------------------------------------------

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
		if not self.aadhaar_number:
			self.aadhaar_verified = 0
			self.aadhaar_verification_date = None
			return

		digits = "".join(ch for ch in self.aadhaar_number if ch.isdigit())
		if len(digits) != 12:
			frappe.throw("Aadhaar Number must be exactly 12 digits.")

		if not self._verify_verhoeff(digits):
			frappe.throw(
				"Aadhaar Number failed the Verhoeff checksum check. "
				"Please verify the number entered is correct."
			)

		self.aadhaar_number = digits
		self.aadhaar_verified = 1
		self.aadhaar_verification_date = today()

	def validate_pan(self):
		if not self.pan_number:
			self.pan_verified = 0
			return

		pan = self.pan_number.strip().upper()
		# Format: 5 letters + 4 digits + 1 letter
		if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", pan):
			frappe.throw(
				"PAN Number format is invalid. Expected format: AAAAA9999A "
				"(5 letters, 4 digits, 1 letter)."
			)

		self.pan_number = pan
		self.pan_verified = 1

	def validate_ifsc(self):
		if not self.ifsc_code:
			return

		ifsc = self.ifsc_code.strip().upper()
		# Format: 4 letters + 0 + 6 digits (e.g., SBIN0001234)
		if not re.match(r"^[A-Z]{4}0[0-9]{6}$", ifsc):
			frappe.throw(
				"IFSC Code format is invalid. Expected format: AAAA0123456 "
				"(4 letters, 0, 6 digits)."
			)

		self.ifsc_code = ifsc

	def validate_uan(self):
		if not self.uan_number:
			self.uan_verified = 0
			return

		digits = "".join(ch for ch in self.uan_number if ch.isdigit())
		if len(digits) != 12:
			frappe.throw("UAN (EPFO) Number must be exactly 12 digits.")

		self.uan_number = digits
		self.uan_verified = 1

	def validate_mobile(self):
		if self.mobile_number:
			digits = "".join(ch for ch in self.mobile_number if ch.isdigit())
			if len(digits) != 10:
				frappe.throw("Mobile Number must be exactly 10 digits.")
			self.mobile_number = digits

		if self.emergency_contact_phone:
			digits = "".join(ch for ch in self.emergency_contact_phone if ch.isdigit())
			if len(digits) != 10:
				frappe.throw("Emergency Contact Phone must be exactly 10 digits.")
			self.emergency_contact_phone = digits

	def update_onboarding_status(self):
		"""Auto-calculate onboarding_status based on completed fields."""
		kyc_done = bool(self.aadhaar_verified and self.pan_verified)
		bank_done = bool(self.bank_account_number and self.ifsc_code)
		docs_uploaded = bool(self.documents and len(self.documents) > 0)
		address_done = bool(self.present_address and self.permanent_address)

		if kyc_done and bank_done and docs_uploaded and address_done:
			self.onboarding_status = "Onboarded"
		elif kyc_done and bank_done and docs_uploaded:
			self.onboarding_status = "Bank Details Pending"
		elif kyc_done:
			self.onboarding_status = "Documents Pending"
		elif self.aadhaar_number or self.pan_number:
			self.onboarding_status = "KYC Pending"
		else:
			self.onboarding_status = "Not Started"
