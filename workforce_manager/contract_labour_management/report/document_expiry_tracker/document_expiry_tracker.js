frappe.query_reports["Document Expiry Tracker"] = {
	"filters": [
		{
			"fieldname": "document_type",
			"label": "Document Type",
			"fieldtype": "Link",
			"options": "Onboarding Document Type"
		},
		{
			"fieldname": "within_days",
			"label": "Expiring Within (Days)",
			"fieldtype": "Int",
			"default": 30
		},
		{
			"fieldname": "only_unverified",
			"label": "Only Unverified",
			"fieldtype": "Check"
		}
	]
};
