// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.query_reports["Balance Sheet"] = {
	onload(query_report) {
		query_report.page.add_inner_button(__("View Report"), () => {
			query_report.refresh();
		});
	},

	tree: true,
	name_field: "account",
	parent_field: "parent_account",
	initial_depth: 2,

	formatter(value, row, column, data, default_formatter) {
		const formatted_value = default_formatter(value, row, column, data);

		if (!data) {
			return formatted_value;
		}

		if (
			column.fieldname === "amount" &&
			Number(data.is_difference) === 1 &&
			Math.abs(Number(value)) > 0.000001
		) {
			return `<span class="text-danger" style="font-weight: 700;">${formatted_value}</span>`;
		}

		if (Number(data.is_total) === 1 || Number(data.is_group) === 1) {
			return `<span style="font-weight: 700;">${formatted_value}</span>`;
		}

		if (column.fieldname === "amount" && Number(value) < 0) {
			return `<span class="text-danger">${formatted_value}</span>`;
		}

		return formatted_value;
	},

	filters: [
		{
			fieldname: "end_date",
			label: __("As of Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			on_change() {},
		},
		{
			fieldname: "outlet",
			label: __("Outlet"),
			fieldtype: "Link",
			options: "Outlet",
			default: frappe.boot.employee_outlet || "",
			on_change() {},
		},
		{
			fieldname: "show_accounts_without_transactions",
			label: __("Show Accounts Without Transactions"),
			fieldtype: "Check",
			default: 0,
			on_change() {},
		},
	],
};
