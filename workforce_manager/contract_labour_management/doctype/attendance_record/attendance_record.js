frappe.ui.form.on("Attendance Record", {
	refresh(frm) {
		// --- Face Verification buttons ---
		if (frm.doc.checkin_selfie && frm.doc.face_verification_status === "Pending") {
			frm.add_custom_button(__("Verify Face"), () => {
				frappe.call({
					method: "workforce_manager.contract_labour_management.face_utils.verify_face",
					args: { attendance_record: frm.doc.name },
					freeze: true,
					freeze_message: __("Running face verification..."),
					callback: (r) => {
						frm.reload_doc();
						if (r.message) {
							frappe.show_alert({
								message: __("Face verification result: {0} (confidence: {1}%)", [
									r.message.status,
									r.message.score || "N/A",
								]),
								indicator: r.message.status === "Verified" ? "green" : "orange",
							});
						}
					},
				});
			});
		}

		// Manual Verify / Reject buttons for HR
		if (frm.doc.checkin_selfie && frm.doc.face_verification_status !== "Verified") {
			if (frm.doc.face_verification_status === "Pending") {
				frm.add_custom_button(__("✓ Manual Verify"), () => {
					frappe.call({
						method: "workforce_manager.contract_labour_management.face_utils.manual_verify",
						args: { attendance_record: frm.doc.name },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				}).addClass("btn-success");
			}

			if (frm.doc.face_verification_status === "Pending" || frm.doc.face_verification_status === "Verified") {
				frm.add_custom_button(__("✗ Mark Mismatched"), () => {
					frappe.confirm(
						__("Are you sure you want to mark this face verification as MISMATCHED? This means the check-in selfie does not match the employee's reference photo."),
						() => {
							frappe.call({
								method: "workforce_manager.contract_labour_management.face_utils.manual_reject",
								args: { attendance_record: frm.doc.name },
								freeze: true,
								callback: () => frm.reload_doc(),
							});
						}
					);
				}).addClass("btn-danger");
			}
		}

		// Show face verification status badge
		if (frm.doc.face_verification_status) {
			const indicators = {
				"Pending": "orange",
				"Verified": "green",
				"Mismatched": "red",
				"No Reference Photo": "gray",
			};
			const indicator = indicators[frm.doc.face_verification_status] || "gray";
			frm.dashboard.set_headline_alert(
				__("Face Verification: {0}", [frm.doc.face_verification_status]),
				indicator
			);
		}
	},
});
