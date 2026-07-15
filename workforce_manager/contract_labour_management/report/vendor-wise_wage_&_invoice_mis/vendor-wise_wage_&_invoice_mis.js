frappe.query_reports["Vendor-wise Wage & Invoice MIS"] = {
	"filters": [
		{
			"fieldname": "contractor",
			"label": "Contractor",
			"fieldtype": "Link",
			"options": "Contractor"
		},
		{
			"fieldname": "from_date",
			"label": "Posting Date From",
			"fieldtype": "Date"
		},
		{
			"fieldname": "to_date",
			"label": "Posting Date To",
			"fieldtype": "Date"
		}
	]
};
