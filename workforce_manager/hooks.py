app_name = "workforce_manager"
app_title = "Workforce Manager"
app_publisher = "Frappe Developer"
app_description = "HRMS / Contract Labour Management system"
app_email = "dev@example.com"
app_license = "mit"

after_install = "workforce_manager.install.after_install"

# Fixtures – standard records exported with the app
fixtures = [
	{"dt": "Workspace", "filters": [["module", "=", "Contract Labour Management"]]},
	{"dt": "Number Card", "filters": [["module", "=", "Contract Labour Management"]]},
	{"dt": "Dashboard Chart", "filters": [["module", "=", "Contract Labour Management"]]},
	{"dt": "Dashboard Chart Source", "filters": [["module", "=", "Contract Labour Management"]]},
]

# Document Events
doc_events = {}

# Scheduled Tasks
scheduler_events = {
	"daily": [
		"workforce_manager.contract_labour_management.notifications.send_expiry_alerts",
	]
}

# Overrides
override_doctype_class = {
    "Site": "workforce_manager.contract_labour_management.doctype.site.site.Site",
    "Contractor": "workforce_manager.contract_labour_management.doctype.contractor.contractor.Contractor",
    "Shift Type": "workforce_manager.contract_labour_management.doctype.shift_type.shift_type.ShiftType",
    "Wage Category": "workforce_manager.contract_labour_management.doctype.wage_category.wage_category.WageCategory",
    "Onboarding Document Type": "workforce_manager.contract_labour_management.doctype.onboarding_document_type.onboarding_document_type.OnboardingDocumentType",
    "Employee Document": "workforce_manager.contract_labour_management.doctype.employee_document.employee_document.EmployeeDocument",
    "Site Contractor Mapping": "workforce_manager.contract_labour_management.doctype.site_contractor_mapping.site_contractor_mapping.SiteContractorMapping",
    "Geofence Check Log": "workforce_manager.contract_labour_management.doctype.geofence_check_log.geofence_check_log.GeofenceCheckLog",
    "Contract Employee": "workforce_manager.contract_labour_management.doctype.contract_employee.contract_employee.ContractEmployee",
    "Attendance Record": "workforce_manager.contract_labour_management.doctype.attendance_record.attendance_record.AttendanceRecord",
    "Wage Sheet Detail": "workforce_manager.contract_labour_management.doctype.wage_sheet_detail.wage_sheet_detail.WageSheetDetail",
    "Wage Sheet": "workforce_manager.contract_labour_management.doctype.wage_sheet.wage_sheet.WageSheet",
    "Contractor Invoice Item": "workforce_manager.contract_labour_management.doctype.contractor_invoice_item.contractor_invoice_item.ContractorInvoiceItem",
    "Contractor Invoice": "workforce_manager.contract_labour_management.doctype.contractor_invoice.contractor_invoice.ContractorInvoice",
    "Statutory Compliance Record": "workforce_manager.contract_labour_management.doctype.statutory_compliance_record.statutory_compliance_record.StatutoryComplianceRecord",
    # Phase5 Overrides Marker
}
