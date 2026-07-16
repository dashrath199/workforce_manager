frappe.query_reports["Site-wise Attendance Summary"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"default": frappe.datetime.month_end(),
			"reqd": 1
		},
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
			"fieldname": "shift",
			"label": "Shift",
			"fieldtype": "Link",
			"options": "Shift Type"
		}
	]
};
