frappe.query_reports["Workforce Headcount by Site"] = {
	"filters": [
		{
			"fieldname": "site",
			"label": "Site",
			"fieldtype": "Link",
			"options": "Site"
		},
		{
			"fieldname": "contractor",
			"label": "Contractor",
			"fieldtype": "Link",
			"options": "Contractor"
		},
		{
			"fieldname": "status",
			"label": "Status",
			"fieldtype": "Select",
			"options": "\nActive\nInactive",
			"default": "Active"
		}
	]
};
