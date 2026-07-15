import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

from workforce_manager.contract_labour_management.utils import (
	DEFAULT_SERVICE_CHARGE_PERCENT,
	GST_RATE,
)


class ContractorInvoice(Document):
	def validate(self):
		# Ensure totals are calculated using flt() per rules
		total_wages = sum(flt(row.gross_wage) for row in (self.items or []))
		total_sc = sum(flt(row.service_charge) for row in (self.items or []))
		total_gst = sum(flt(row.gst_amount) for row in (self.items or []))

		self.total_wages = total_wages
		self.total_service_charge = total_sc
		self.total_gst = total_gst
		self.invoice_value = total_wages + total_sc + total_gst

	@frappe.whitelist()
	def generate_from_wage_sheets(self):
		"""
		Pull all SUBMITTED Wage Sheets for this Contractor + Wage Month that
		aren't already on an invoice, one line per Site, with service charge
		and GST computed automatically.
		"""
		if not (self.contractor and self.wage_month):
			frappe.throw("Contractor and Wage Month are required before generating invoice items.")

		already_invoiced = frappe.get_all(
			"Contractor Invoice Item",
			filters={"parent": ["!=", self.name]},
			fields=["wage_sheet_ref"],
		)
		invoiced_refs = {row.wage_sheet_ref for row in already_invoiced if row.wage_sheet_ref}

		wage_sheets = frappe.get_all(
			"Wage Sheet",
			filters={
				"contractor": self.contractor,
				"wage_month": self.wage_month,
				"docstatus": 1,
			},
			fields=["name", "site", "total_gross_wages"],
		)

		service_charge_pct = flt(self.service_charge_percentage) or DEFAULT_SERVICE_CHARGE_PERCENT
		self.service_charge_percentage = service_charge_pct

		self.set("items", [])
		for ws in wage_sheets:
			if ws.name in invoiced_refs:
				continue  # already billed on another invoice
			gross_wage = flt(ws.total_gross_wages)
			service_charge = round(gross_wage * service_charge_pct / 100.0, 2)
			gst_amount = round((gross_wage + service_charge) * GST_RATE / 100.0, 2)
			line_total = gross_wage + service_charge + gst_amount

			self.append("items", {
				"site": ws.site,
				"wage_sheet_ref": ws.name,
				"gross_wage": gross_wage,
				"service_charge": service_charge,
				"gst_amount": gst_amount,
				"line_total": line_total,
			})

		self.validate()
		self.save()
		return {"wage_sheets_included": len(self.items), "invoice_value": self.invoice_value}

	def on_submit(self):
		# ERPNext Purchase Invoice Creation Pattern
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		if not company:
			return

		vendor = frappe.db.get_value("Contractor", self.contractor, "vendor_account")

		try:
			pi = frappe.get_doc({
				"doctype": "Purchase Invoice",
				"supplier": vendor if vendor else self.contractor,
				"company": company,
				"posting_date": self.posting_date or today(),
				"items": [{
					"item_name": "Contract Labour Services",
					"qty": 1,
					"rate": flt(self.invoice_value),
					"description": f"Contractor Invoice: {self.name}"
				}]
			})
			# Depending on exact ERPNext setup, item_code or expense_account might be strictly required,
			# but for integration skeleton, we save as draft or try to submit
			pi.insert(ignore_permissions=True)
			# Let users review before submitting PI, or uncomment pi.submit() if Auto-submit is preferred
			# pi.submit()

			self.db_set("erpnext_purchase_invoice", pi.name)
			frappe.db.commit()
		except Exception as e:
			frappe.log_error(f"PI creation failed for {self.name}: {str(e)}", "Contractor Invoice Error")
