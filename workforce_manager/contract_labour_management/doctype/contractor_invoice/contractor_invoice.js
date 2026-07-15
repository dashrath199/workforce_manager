frappe.ui.form.on("Contractor Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.contractor && frm.doc.wage_month) {
			frm.add_custom_button(__("Generate from Wage Sheets"), () => {
				frappe.call({
					method: "generate_from_wage_sheets",
					doc: frm.doc,
					freeze: true,
					freeze_message: __("Pulling submitted Wage Sheets..."),
					callback: (r) => {
						frm.reload_doc();
						if (r.message) {
							frappe.msgprint(
								__("Included {0} wage sheet(s). Invoice Value: {1}", [
									r.message.wage_sheets_included,
									r.message.invoice_value,
								])
							);
						}
					},
				});
			}).addClass("btn-primary");
		}
	},
});
