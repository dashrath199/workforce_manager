frappe.ui.form.on("Wage Sheet", {
	refresh(frm) {
		// --- Generate Wage Details button (Draft mode) ---
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

		// --- Statutory Register buttons (Submitted wage sheets only) ---
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("📋 Muster Roll"), () => {
				_generate_file(frm, "workforce_manager.contract_labour_management.registers.generate_muster_roll");
			}, __("Statutory Registers"));
			frm.add_custom_button(__("📊 Wage Register"), () => {
				_generate_file(frm, "workforce_manager.contract_labour_management.registers.generate_wage_register");
			}, __("Statutory Registers"));
			frm.add_custom_button(__("💰 Deduction Register"), () => {
				_generate_file(frm, "workforce_manager.contract_labour_management.registers.generate_deduction_register");
			}, __("Statutory Registers"));

			// --- Wage Slip buttons ---
			frm.add_custom_button(__("📄 All Wage Slips (PDF)"), () => {
				_generate_file(frm, "workforce_manager.contract_labour_management.payslip_utils.generate_all_wage_slips");
			}, __("Wage Slips"));
			frm.add_custom_button(__("🏦 Bank Transfer File (CSV)"), () => {
				_generate_file(frm, "workforce_manager.contract_labour_management.payslip_utils.generate_bank_transfer_file");
			}, __("Wage Slips"));
		}
	},
});

function _generate_file(frm, method) {
	frappe.call({
		method: method,
		args: { wage_sheet: frm.doc.name },
		freeze: true,
		freeze_message: __("Generating..."),
		callback: (r) => {
			if (r.message) {
				frappe.msgprint({
					message: __("File generated. <a href='{0}' target='_blank'>Download</a>", [r.message]),
					indicator: "green",
					title: __("Success"),
				});
			}
		},
		error: (r) => {
			frappe.msgprint({
				message: __("Failed. Error: {0}", [r.message]),
				indicator: "red",
				title: __("Error"),
			});
		},
	});
}
