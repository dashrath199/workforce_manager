frappe.ui.form.on("Wage Sheet", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.site && frm.doc.contractor && frm.doc.wage_month) {
			frm.add_custom_button(__("Generate Wage Details from Attendance"), () => {
				frappe.call({
					method: "generate_wage_details",
					doc: frm.doc,
					freeze: true,
					freeze_message: __("Pulling attendance and computing wages..."),
					callback: (r) => {
						frm.reload_doc();
						if (r.message) {
							frappe.msgprint(
								__("Processed {0} employees. Gross: {1}, Net: {2}", [
									r.message.employees_processed,
									r.message.total_gross_wages,
									r.message.total_net_wages,
								])
							);
						}
					},
				});
			}).addClass("btn-primary");
		}
	},
});
