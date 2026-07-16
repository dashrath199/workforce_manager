import frappe
from frappe.model.document import Document
from frappe.utils import flt

from workforce_manager.contract_labour_management.utils import (
	month_date_range,
	calc_statutory_deductions,
	default_statutory_due_date,
)


class WageSheet(Document):
	def validate(self):
		self.calculate_totals()

	def _calculate_ot_amount(self, employee, ot_hours, hourly_rate):
		"""Calculate OT amount using approved OT requests and configured rates.

		Only counts OT hours that have been approved via Overtime Request.
		Falls back to default 2x rate if no Overtime Settings configured.
		"""
		from workforce_manager.contract_labour_management.doctype.overtime_settings.overtime_settings import (
			get_overtime_settings, get_ot_rate
		)

		if not ot_hours or not hourly_rate:
			return 0.0

		try:
			settings = get_overtime_settings()
			require_approval = settings.require_approval
		except Exception:
			require_approval = False

		if require_approval:
			# Only count OT hours that have an approved Overtime Request
			start_date, end_date = month_date_range(self.wage_month)
			approved_ot_rows = frappe.db.sql("""
				SELECT ar.ot_hours, ar.date, ar.shift
				FROM `tabAttendance Record` ar
				INNER JOIN `tabOvertime Request` ot ON ot.name = ar.overtime_request
				WHERE ar.employee = %s
				  AND ar.date BETWEEN %s AND %s
				  AND ot.status = 'Approved'
				  AND ar.docstatus < 2
			""", (employee, start_date, end_date), as_dict=True)

			ot_amount = 0.0
			for row in approved_ot_rows:
				# Determine OT category from shift
				ot_category = "Regular"
				if row.shift:
					shift_doc = frappe.get_cached_doc("Shift Type", row.shift)
					if shift_doc.is_night_shift:
						ot_category = "Night Shift"

				rate = get_ot_rate(None, ot_category)
				ot_amount += flt(row.ot_hours) * hourly_rate * rate

			return round(ot_amount, 2)
		else:
			# No approval required - use default 2x rate
			rate = 2.0
			try:
				settings = get_overtime_settings()
				rate = get_ot_rate(settings, "Regular")
			except Exception:
				pass
			return round(ot_hours * hourly_rate * rate, 2)

	def calculate_totals(self):
		self.total_gross_wages = sum(flt(row.gross_wage) for row in (self.details or []))
		self.total_net_wages = sum(flt(row.net_wage) for row in (self.details or []))

	def on_submit(self):
		self.status = "Submitted"
		self.sync_statutory_compliance_record()

	def on_cancel(self):
		self.status = "Cancelled"

	@frappe.whitelist()
	def generate_wage_details(self):
		"""
		Pull Attendance for this Site + Contractor + Wage Month, compute gross
		wage from each employee's Wage Category minimum rate, and populate
		statutory deductions (PF/ESI/PT/LWF) per row. Overwrites existing rows.
		"""
		if not (self.site and self.contractor and self.wage_month):
			frappe.throw("Site, Contractor and Wage Month are required before generating wage details.")

		start_date, end_date = month_date_range(self.wage_month)

		employees = frappe.get_all(
			"Contract Employee",
			filters={"site": self.site, "contractor": self.contractor, "status": "Active"},
			fields=["name", "wage_category"],
		)

		self.set("details", [])

		for emp in employees:
			daily_rate = 0.0
			if emp.wage_category:
				daily_rate = flt(frappe.db.get_value("Wage Category", emp.wage_category, "minimum_wage_rate"))

			attendance_rows = frappe.get_all(
				"Attendance Record",
				filters={
					"employee": emp.name,
					"date": ["between", [start_date, end_date]],
				},
				fields=["status", "ot_hours"],
			)

			days_present = sum(
				1.0 if row.status == "Present" else 0.5 if row.status == "Half Day" else 0.0
				for row in attendance_rows
			)
			ot_hours = sum(flt(row.ot_hours) for row in attendance_rows)

			hourly_rate = (daily_rate / 8.0) if daily_rate else 0.0

			# Calculate OT amount using approved OT rates from Overtime Settings
			ot_amount = self._calculate_ot_amount(emp.name, ot_hours, hourly_rate)
			gross_wage = round((daily_rate * days_present) + ot_amount, 2)

			deductions = calc_statutory_deductions(gross_wage)

			self.append("details", {
				"employee": emp.name,
				"days_present": days_present,
				"ot_hours": ot_hours,
				"gross_wage": gross_wage,
				"pf_deduction": deductions["pf_deduction"],
				"esi_deduction": deductions["esi_deduction"],
				"pt_deduction": deductions["pt_deduction"],
				"lwf_deduction": deductions["lwf_deduction"],
				"net_wage": deductions["net_wage"],
			})

		self.calculate_totals()
		self.save()
		return {
			"employees_processed": len(employees),
			"total_gross_wages": self.total_gross_wages,
			"total_net_wages": self.total_net_wages,
		}

	def sync_statutory_compliance_record(self):
		"""On submit, roll this Wage Sheet's deductions into (or create) the
		Contractor's Statutory Compliance Record for the month."""
		total_pf = sum(flt(r.pf_deduction) for r in self.details)
		total_esi = sum(flt(r.esi_deduction) for r in self.details)
		total_pt = sum(flt(r.pt_deduction) for r in self.details)
		total_lwf = sum(flt(r.lwf_deduction) for r in self.details)
		total_statutory = total_pf + total_esi + total_pt + total_lwf

		existing = frappe.db.get_value(
			"Statutory Compliance Record",
			{"contractor": self.contractor, "wage_month": self.wage_month},
			"name",
		)

		if existing:
			scr = frappe.get_doc("Statutory Compliance Record", existing)
			scr.total_amount = flt(scr.total_amount) + total_statutory
		else:
			scr = frappe.new_doc("Statutory Compliance Record")
			scr.naming_series = "SCR-.YYYY.-.#####"
			scr.contractor = self.contractor
			scr.wage_month = self.wage_month
			scr.due_date = default_statutory_due_date(self.wage_month)
			scr.total_amount = total_statutory
			scr.status = "Pending"

		scr.save(ignore_permissions=True)
