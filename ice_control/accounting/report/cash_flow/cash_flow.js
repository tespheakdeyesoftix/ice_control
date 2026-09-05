// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.query_reports["Cash Flow"] = {
	onload(query_report) {
		query_report.page.add_inner_button(__("View Report"), () => {
			frappe.query_reports["Cash Flow"].preview_report(query_report);
		});
	},

	preview_report(query_report) {
		query_report.refresh();
	},

	formatter(value, row, column, data, default_formatter) {
		const formatted_value = default_formatter(value, row, column, data);

		if (!data) {
			return formatted_value;
		}

		if (Number(data.is_total) === 1) {
			if (column.fieldname === "posting_date") {
				return `<span style="font-weight: 700;">${__("Total")}</span>`;
			}

			return `<span style="font-weight: 700;">${formatted_value}</span>`;
		}

		if (Number(data.is_opening) === 1) {
			if (column.fieldname === "posting_date") {
				return `<span style="font-weight: 700;">${__("Opening Balance")}</span>`;
			}

			return `<span style="font-weight: 700;">${formatted_value}</span>`;
		}

		if (column.fieldname === "inflow" && Number(value) > 0) {
			return `<span class="text-success">${formatted_value}</span>`;
		}

		if (column.fieldname === "outflow" && Number(value) > 0) {
			return `<span class="text-danger">${formatted_value}</span>`;
		}

		if (column.fieldname === "balance" && Number(value) < 0) {
			return `<span class="text-danger">${formatted_value}</span>`;
		}

		return formatted_value;
	},

	filters: [
		{
			fieldname: "outlet",
			label: __("Outlet"),
			fieldtype: "Link",
			options: "Outlet",
			default: frappe.boot.employee_outlet || "",
			reqd: 1,
			on_change() {},
		},
		{
			fieldname: "start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
			on_change() {},
		},
		{
			fieldname: "end_date",
			label: __("End Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
			on_change() {},
		},
		{
			fieldname: "account",
			label: __("Account Code"),
			fieldtype: "MultiSelectList",
			get_data(txt) {
				const outlet = frappe.query_report.get_filter_value("outlet");
				const filters = [
					["Chart of Account", "account_type", "=", "Cash"],
					["Chart of Account", "is_group", "=", 0],
				];

				if (outlet) {
					filters.push([
						"Chart of Account",
						"outlet",
						"in",
						["", outlet],
					]);
				}

				return frappe.db.get_link_options(
					"Chart of Account",
					txt,
					filters
				);
			},
			on_change() {},
		},
	],
};
