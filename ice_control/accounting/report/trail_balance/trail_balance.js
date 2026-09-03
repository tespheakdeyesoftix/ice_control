// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.query_reports["Trail Balance"] = {
	onload(query_report) {
		query_report.page.add_inner_button(__("View Report"), () => {
			query_report.refresh();
		});
	},

	tree: true,
	name_field: "account_code",
	parent_field: "parent_account",
	initial_depth: 2,

	formatter(value, row, column, data, default_formatter) {
		const formatted_value = default_formatter(value, row, column, data);

		if (!data) {
			return formatted_value;
		}

		if (Number(data.is_total) === 1 || Number(data.is_group) === 1) {
			return `<span style="font-weight: 700;">${formatted_value}</span>`;
		}

		if (Number(value) < 0 && column.fieldtype === "Currency") {
			return `<span class="text-danger">${formatted_value}</span>`;
		}

		return formatted_value;
	},

	filters: [
		{
			fieldname: "start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "end_date",
			label: __("End Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
		{
			fieldname: "outlet",
			label: __("Outlet"),
			fieldtype: "Link",
			options: "Outlet",
			default: frappe.boot.employee_outlet || "",
		},
		{
			fieldname: "show_accounts_without_transactions",
			label: __("Show Accounts Without Transactions"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
