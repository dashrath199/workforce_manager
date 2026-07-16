frappe.ui.form.on("Statutory Compliance Record", {
	refresh(frm) {
		// --- ECR / Challan Generation buttons ---
		frm.add_custom_button(__("PF ECR (CSV)"), () => {
			_generate(frm, "workforce_manager.contract_labour_management.challan_utils.generate_pf_ecr");
		}, __("Generate Challans"));

		frm.add_custom_button(__("ESI Return (CSV)"), () => {
			_generate(frm, "workforce_manager.contract_labour_management.challan_utils.generate_esi_return");
		}, __("Generate Challans"));

		frm.add_custom_button(__("PF Challan (PDF)"), () => {
			_generate(frm, "workforce_manager.contract_labour_management.challan_utils.generate_pf_challan");
		}, __("Generate Challans"));

		frm.add_custom_button(__("ESI Challan (PDF)"), () => {
			_generate(frm, "workforce_manager.contract_labour_management.challan_utils.generate_esi_challan");
		}, __("Generate Challans"));

		frm.add_custom_button(__("PT Challan (PDF)"), () => {
			_generate(frm, "workforce_manager.contract_labour_management.challan_utils.generate_pt_challan");
		}, __("Generate Challans"));

		frm.add_custom_button(__("LWF Challan (PDF)"), () => {
			_generate(frm, "workforce_manager.contract_labour_management.challan_utils.generate_lwf_challan");
		}, __("Generate Challans"));
	},
});

function _generate(frm, method) {
	frappe.call({
		method: method,
		args: { statutory_record: frm.doc.name },
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
				message: __("Failed to generate. Error: {0}", [r.message]),
				indicator: "red",
				title: __("Error"),
			});
		},
	});
}
