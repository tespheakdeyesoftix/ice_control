// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.query_reports["Account Receivable Aging"] = {
	onload(query_report) {
		const report_settings = frappe.query_reports["Account Receivable Aging"];
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
			sort_by: "customer_name",
			sort_order: "asc",
			chart_type: "percentage",
		};

		try {
			const saved = JSON.parse(
				window.localStorage.getItem(
					query_report.report_name || "Account Receivable Aging"
				) || "{}"
			);

			return {
				sort_by: ["customer_code", "customer_name"].includes(saved.sort_by)
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
				query_report.report_name || "Account Receivable Aging",
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
						{ label: __("Customer Code"), value: "customer_code" },
						{ label: __("Customer Name"), value: "customer_name" },
					],
					default: query_report.get_filter_value("sort_by") || "customer_name",
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
				const report_settings = frappe.query_reports["Account Receivable Aging"];
				report_settings.save_settings(query_report, settings);
				query_report.set_filter_value(settings);
				dialog.hide();
				report_settings.preview_report(query_report);
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
			data.customer_code &&
			(column.fieldname === "customer" || column.id === "customer")
		) {
			return frappe.utils.get_form_link(
				"Customer",
				data.customer_code,
				true,
				frappe.utils.escape_html(String(value || ""))
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
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
			on_change(query_report) {
				if (query_report.get_filter_value("customer")) {
					query_report.set_filter_value("customer", "");
				}
			},
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query() {
				const customer_group = frappe.query_report.get_filter_value("customer_group");
				return customer_group ? { filters: { customer_group } } : {};
			},
			on_change() {},
		},
		{
			fieldname: "sort_by",
			fieldtype: "Data",
			default: "customer_name",
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
