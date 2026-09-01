// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.query_reports["Account Payable"] = {
	onload(query_report) {
		const report_settings = frappe.query_reports["Account Payable"];
		query_report.set_filter_value(report_settings.get_saved_settings(query_report));

		query_report.page.add_inner_button(__("View Report"), () => {
			report_settings.preview_report(query_report);
		});
		query_report.page.add_menu_item(__("Setting"), () => {
			report_settings.open_settings_dialog(query_report);
		});
		query_report.page.add_divider();
	},

	preview_report(query_report) {
		query_report.refresh();
	},

	get_saved_settings(query_report) {
		const defaults = {
			sort_by: "party_name",
			sort_order: "asc",
			chart_type: "percentage",
		};

		try {
			const saved = JSON.parse(
				window.localStorage.getItem(query_report.report_name || "Account Payable") || "{}"
			);

			return {
				sort_by: ["party_code", "party_name"].includes(saved.sort_by)
					? saved.sort_by
					: defaults.sort_by,
				sort_order: ["asc", "desc"].includes(saved.sort_order)
					? saved.sort_order
					: defaults.sort_order,
				chart_type: ["percentage", "bar", "pie"].includes(saved.chart_type)
					? saved.chart_type
					: defaults.chart_type,
			};
		} catch (error) {
			return defaults;
		}
	},

	save_settings(query_report, settings) {
		try {
			window.localStorage.setItem(
				query_report.report_name || "Account Payable",
				JSON.stringify(settings)
			);
		} catch (error) {
			frappe.show_alert({
				message: __("Unable to save report settings in this browser."),
				indicator: "orange",
			});
		}
	},

	open_settings_dialog(query_report) {
		const dialog = new frappe.ui.Dialog({
			title: __("Report Setting"),
			fields: [
				{
					fieldname: "sort_by",
					label: __("Sort By"),
					fieldtype: "Select",
					options: [
						{ label: __("Party Code"), value: "party_code" },
						{ label: __("Party Name"), value: "party_name" },
					],
					default: query_report.get_filter_value("sort_by") || "party_name",
					reqd: 1,
				},
				{
					fieldname: "sort_order",
					label: __("Direction"),
					fieldtype: "Select",
					options: [
						{ label: __("Ascending"), value: "asc" },
						{ label: __("Descending"), value: "desc" },
					],
					default: query_report.get_filter_value("sort_order") || "asc",
					reqd: 1,
				},
				{
					fieldname: "chart_type",
					label: __("Chart Type"),
					fieldtype: "Select",
					options: [
						{ label: __("Percent"), value: "percentage" },
						{ label: __("Bar"), value: "bar" },
						{ label: __("Pie"), value: "pie" },
					],
					default: query_report.get_filter_value("chart_type") || "percentage",
					reqd: 1,
				},
			],
			primary_action_label: __("Apply"),
			primary_action(values) {
				const settings = {
					sort_by: values.sort_by,
					sort_order: values.sort_order,
					chart_type: values.chart_type,
				};
				frappe.query_reports["Account Payable"].save_settings(
					query_report,
					settings
				);
				query_report.set_filter_value(settings);
				dialog.hide();
				frappe.query_reports["Account Payable"].preview_report(query_report);
			},
		});

		dialog.show();
	},

	formatter(value, row, column, data, default_formatter) {
		const formatted_value = default_formatter(value, row, column, data);

		if (data && Number(data.is_total) === 1) {
			return `<div style="font-weight: 700;">${formatted_value}</div>`;
		}

		if (
			data &&
			data.party_code &&
			data.party_type &&
			(column.fieldname === "party" || column.id === "party")
		) {
			const party_label = frappe.utils.escape_html(String(value || ""));
			return frappe.utils.get_form_link(
				data.party_type,
				data.party_code,
				true,
				party_label
			);
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
			fieldname: "outlet",
			label: __("Outlet"),
			fieldtype: "Link",
			options: "Outlet",
			default: frappe.boot.employee_outlet || "",
			on_change() {},
		},
		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Link",
			options: "DocType",
			get_query() {
				return {
					filters: {
						name: ["in", ["Customer", "Vendor", "Employee"]],
					},
				};
			},
			on_change(query_report) {
				if (query_report.get_filter_value("party")) {
					query_report.set_filter_value("party", "");
				}
			},
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "Dynamic Link",
			options: "party_type",
			on_change() {},
		},
		{
			fieldname: "sort_by",
			fieldtype: "Data",
			default: "party_name",
			hidden: 1,
			on_change() {},
		},
		{
			fieldname: "sort_order",
			fieldtype: "Data",
			default: "asc",
			hidden: 1,
			on_change() {},
		},
		{
			fieldname: "chart_type",
			fieldtype: "Data",
			default: "percentage",
			hidden: 1,
			on_change() {},
		},
	],
};
