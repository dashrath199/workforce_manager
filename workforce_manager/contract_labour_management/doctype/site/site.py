import frappe
from frappe.model.document import Document
import hashlib
from frappe.utils import now_datetime, get_url
from urllib.parse import quote


class Site(Document):
	def validate(self):
		self.generate_qr_code_id()

	def generate_qr_code_id(self):
		"""Generate a unique QR code identifier for the site if not already set."""
		if not self.qr_code_id:
			# Create a unique hash from site name + timestamp
			raw = f"{self.site_name}-{self.name or ''}-{now_datetime()}"
			hash_str = hashlib.sha256(raw.encode()).hexdigest()[:16]
			self.qr_code_id = f"SITE-{self.site_name.upper().replace(' ', '')[:10]}-{hash_str}"

		# Always update the URL to keep the format current (e.g. after URL schema changes)
		# URL-encode the site name so spaces/special chars don't break the query parameter
		self.qr_download_url = f"{get_url()}/qr?site={quote(self.name or '')}"
