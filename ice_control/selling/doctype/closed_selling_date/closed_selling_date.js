// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Closed Selling Date", {
	refresh(frm) {
		show_close_date_warning(frm);

		if (frm.is_new() || !frm.doc.outlet || !frm.doc.posting_date) {
			render_close_date_preview(frm, frm.doc.html_preview_close_date_data || "");
			return;
		}

		frm.trigger("refresh_close_date_preview");
	},

	validate(frm) {
		sync_close_date_items(frm);
	},

	before_submit(frm) {
		const rows = sync_close_date_items(frm);

		if (!frm.doc.i_am_confirmed_all_data_below_are_correct) {
			frappe.throw(__("Confirm that all closing data is correct before submitting."));
		}

		const missing_actual = rows.filter((row) => row.actual_value === "");
		if (missing_actual.length) {
			frappe.throw(
				__("Enter Actual Value for every closing item before submitting. Missing: {0}", [
					missing_actual.slice(0, 5).map((row) => row.title).join(", "),
				])
			);
		}

		const missing_notes = rows.filter(
			(row) => Math.abs(row.difference) > 0.005 && !row.note
		);
		if (missing_notes.length) {
			frappe.throw(
				__("A note is required for every non-zero difference. Missing: {0}", [
					missing_notes.slice(0, 5).map((row) => row.title).join(", "),
				])
			);
		}
	},

	after_save(frm) {
		render_close_date_preview(frm, frm.doc.html_preview_close_date_data || "");
		show_close_date_warning(frm);
	},

	async refresh_close_date_preview(frm) {
		const response = await frm.call("get_close_date_data");
		render_close_date_preview(frm, response.message || "");
		show_close_date_warning(frm);
	},
});

frappe.ui.form.on("Closed Selling Date Items", {
	actual_value(frm, cdt, cdn) {
		calculate_child_difference(frm, cdt, cdn);
	},

	value(frm, cdt, cdn) {
		calculate_child_difference(frm, cdt, cdn);
	},
});

function show_close_date_warning(frm) {
	const warning = `
		<div>
			<strong>⚠ ${__("IMPORTANT: Verify every figure before closing this date")}</strong><br>
			${__(
				"Review all data below and tick the confirmation checkbox only when everything is complete and correct. Submitting will close and may lock transactions on or before this date."
			)}
		</div>`;

	frm.dashboard.clear_headline();
	frm.dashboard.set_headline_alert(warning, "red", true);
}

function render_close_date_preview(frm, html) {
	const field = frm.fields_dict.html_preview_close_date_data;
	if (!field || !field.$wrapper) {
		return;
	}

	field.$wrapper.html(html);
	field.$wrapper
		.off("input.close-date-preview")
		.on("input.close-date-preview", ".close-date-preview__actual-input", function () {
			update_preview_difference($(this).closest(".close-date-preview__metric-row"));
		});
}

function get_preview_rows(frm) {
	const field = frm.fields_dict.html_preview_close_date_data;
	if (!field || !field.$wrapper) {
		return [];
	}

	return field.$wrapper
		.find(".close-date-preview__metric-row")
		.map(function () {
			const $row = $(this);
			const actual_value = String($row.find(".close-date-preview__actual-input").val() ?? "").trim();
			const value = flt($row.attr("data-system-value"));
			return {
				category: $row.attr("data-category"),
				title: $row.attr("data-title"),
				fieldtype: $row.attr("data-fieldtype"),
				value,
				actual_value,
				difference: actual_value === "" ? 0 : flt(actual_value) - value,
				note: String($row.find(".close-date-preview__note-input").val() ?? "").trim(),
			};
		})
		.get();
}

function sync_close_date_items(frm) {
	const rows = get_preview_rows(frm);
	if (!rows.length) {
		return rows;
	}

	frm.clear_table("closed_selling_date_items");
	rows.forEach((row) => {
		frm.add_child("closed_selling_date_items", {
			category: row.category,
			title: row.title,
			fieldtype: row.fieldtype,
			value: row.value,
			actual_value: row.actual_value === "" ? null : flt(row.actual_value),
			total_amount: row.actual_value === "" ? null : row.difference,
			note: row.note,
		});
	});
	frm.refresh_field("closed_selling_date_items");
	return rows;
}

function update_preview_difference($row) {
	const actual_value = String($row.find(".close-date-preview__actual-input").val() ?? "").trim();
	const $difference = $row.find(".close-date-preview__difference-value");
	if (actual_value === "") {
		$difference.text("—").removeClass("close-date-preview__difference-value--mismatch");
		return;
	}

	const difference = flt(actual_value) - flt($row.attr("data-system-value"));
	$difference
		.text(format_preview_value(difference, $row.attr("data-fieldtype"), $row.closest(".close-date-preview").attr("data-currency")))
		.toggleClass("close-date-preview__difference-value--mismatch", Math.abs(difference) > 0.005);
}

function format_preview_value(value, fieldtype, currency) {
	return frappe.format(value, {
		fieldtype,
		options: fieldtype === "Currency" ? currency : undefined,
	});
}

function calculate_child_difference(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "total_amount", flt(row.actual_value) - flt(row.value));
}
