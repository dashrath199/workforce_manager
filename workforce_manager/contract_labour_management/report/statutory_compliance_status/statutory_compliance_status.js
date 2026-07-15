frappe.query_reports["Statutory Compliance Status"] = {
	"filters": [
		{
			"fieldname": "contractor",
			"label": "Contractor",
			"fieldtype": "Link",
			"options": "Contractor"
		},
		{
			"fieldname": "wage_month",
			"label": "Wage Month (YYYY-MM)",
			"fieldtype": "Data"
		},
		{
			"fieldname": "status",
			"label": "Status",
			"fieldtype": "Select",
			"options": "\nPending\nPaid"
		},
		{
			"fieldname": "only_overdue",
			"label": "Only Overdue",
			"fieldtype": "Check"
		}
	]
};
