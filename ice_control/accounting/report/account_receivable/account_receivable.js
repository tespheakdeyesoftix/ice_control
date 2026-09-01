// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.query_reports["Account Receivable"] = {
	onload(query_report) {
		const report_settings = frappe.query_reports["Account Receivable"];
		query_report.set_filter_value(report_settings.get_saved_settings(query_report));

		query_report.page.add_inner_button(__("View Report"), () => {
			frappe.query_reports["Account Receivable"].preview_report(query_report);
		});
		query_report.page.add_menu_item(__("Setting"), () => {
			frappe.query_reports["Account Receivable"].open_settings_dialog(query_report);
		});
		query_report.page.add_divider();
		report_settings.bind_customer_click(query_report);
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
				window.localStorage.getItem(query_report.report_name || "Account Receivable") || "{}"
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
				query_report.report_name || "Account Receivable",
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
				frappe.query_reports["Account Receivable"].save_settings(
					query_report,
					settings
				);
				query_report.set_filter_value(settings);
				dialog.hide();
				frappe.query_reports["Account Receivable"].preview_report(query_report);
			},
		});

		dialog.show();
	},

	bind_customer_click(query_report) {
		const $wrapper = query_report.page.main;
		$wrapper.off("click.account_receivable_customer", ".account-receivable-customer");
		$wrapper.on(
			"click.account_receivable_customer",
			".account-receivable-customer",
			(event) => {
				event.preventDefault();
				const customer = $(event.currentTarget).attr("data-customer");
				if (customer) {
					this.open_customer_details(query_report, customer);
				}
			}
		);
	},

	async open_customer_details(query_report, customer) {
		const response = await frappe.call({
			method: "ice_control.accounting.report.account_receivable.customer_receivable_details.get_customer_receivable_details",
			args: {
				customer,
				filters: JSON.stringify(query_report.get_filter_values()),
			},
			freeze: true,
			freeze_message: __("Loading customer receivable details..."),
		});

		if (response.message) {
			this.show_customer_details_dialog(response.message);
		}
	},

	show_customer_details_dialog(details) {
		const customer_label = [details.customer.code, details.customer.name]
			.filter(Boolean)
			.join(" - ");
		const dialog = new frappe.ui.Dialog({
			title: __("Receivable Details: {0}", [customer_label]),
			size: "extra-large",
			fields: [{ fieldname: "details_html", fieldtype: "HTML" }],
			primary_action_label: __("Close"),
			primary_action() {
				dialog.hide();
			},
			secondary_action_label: __("Open Customer"),
			secondary_action() {
				dialog.hide();
				frappe.set_route("Form", "Customer", details.customer.code);
			},
		});

		dialog.fields_dict.details_html.$wrapper.html(
			this.get_customer_details_html(details)
		);
		dialog.show();
		dialog.$wrapper.find(".modal-body").css({
			"max-height": "calc(100vh - 180px)",
			"overflow-y": "auto",
		});
	},

	get_customer_details_html(details) {
		const escape = (value) => frappe.utils.escape_html(String(value ?? ""));
		const money = (value) =>
			frappe.format(value || 0, { fieldtype: "Currency" }, { only_value: true });
		const date = (value) => (value ? frappe.datetime.str_to_user(value) : "");
		const summary = details.summary || {};
		const summary_items = [
			[__("Opening Balance"), summary.opening_balance],
			[__("Debit"), summary.debit_amount],
			[__("Credit"), summary.credit_amount],
			[__("Write Off"), summary.write_off_amount],
			[__("Closing Balance"), summary.closing_balance],
		];
		const aging_colors = [
			"#d6ecff",
			"#b8d8f0",
			"#ffe6a7",
			"#ffc857",
			"#f28c45",
			"#d64545",
		];

		const summary_html = summary_items
			.map(
				([label, value]) => `
					<div class="col-sm">
						<div class="border rounded p-3 mb-3">
							<div class="text-muted small">${escape(label)}</div>
							<div class="font-weight-bold">${money(value)}</div>
						</div>
					</div>`
			)
			.join("");

		const aging_html = (details.aging || [])
			.map(
				(item, index) => `
					<div class="col-sm-2">
						<div class="rounded p-2 mb-3" style="border-top: 4px solid ${
							aging_colors[index]
						}; background: var(--control-bg);">
							<div class="text-muted small">${escape(item.label)}</div>
							<div class="font-weight-bold">${money(item.value)}</div>
						</div>
					</div>`
			)
			.join("");

		const transaction_rows = (details.transactions || [])
			.map((transaction) => {
				let voucher = escape(transaction.voucher_no);
				if (transaction.voucher_type && transaction.voucher_no) {
					voucher = frappe.utils.get_form_link(
						transaction.voucher_type,
						transaction.voucher_no,
						true,
						voucher
					);
				}
				const voucher_title = escape(transaction.voucher_type);

				return `
					<tr>
						<td>${escape(date(transaction.posting_date))}</td>
						<td><span title="${voucher_title}">${voucher}</span></td>
						<td>${escape(transaction.account)}</td>
						<td class="text-right">${money(transaction.debit_amount)}</td>
						<td class="text-right">${money(transaction.credit_amount)}</td>
						<td class="text-right">${money(transaction.running_balance)}</td>
						<td class="text-center">${escape(transaction.age)}</td>
						<td>${escape(transaction.remark)}</td>
					</tr>`;
			})
			.join("");

		const transaction_note = details.is_truncated
			? `<div class="alert alert-warning mb-3">${__(
					"Showing the first {0} of {1} transactions.",
					[details.max_transactions, details.transaction_count]
			  )}</div>`
			: `<div class="text-muted mb-3">${__("Transactions: {0}", [
					details.transaction_count || 0,
			  ])}</div>`;

		return `
			<div class="mb-3">
				<div><strong>${escape(details.customer.code)} - ${escape(
					details.customer.name
				)}</strong></div>
				<div class="text-muted">
					${escape(details.customer.group)}
					${details.customer.phone_number ? ` · ${escape(details.customer.phone_number)}` : ""}
				</div>
				<div class="text-muted">
					${escape(details.filters.outlet)} · ${escape(date(details.filters.start_date))}
					— ${escape(date(details.filters.end_date))}
				</div>
			</div>
			<div class="row">${summary_html}</div>
			<h5 class="mt-2">${__("Aging Breakdown")}</h5>
			<div class="row">${aging_html}</div>
			<h5 class="mt-2">${__("GL Transactions")}</h5>
			${transaction_note}
			<div class="table-responsive">
				<table class="table table-bordered table-hover">
					<thead style="position: sticky; top: 0; background: var(--card-bg); z-index: 1;">
						<tr>
							<th>${__("Posting Date")}</th>
							<th>${__("Voucher No")}</th>
							<th>${__("Account")}</th>
							<th class="text-right">${__("Debit")}</th>
							<th class="text-right">${__("Credit")}</th>
							<th class="text-right">${__("Running Balance")}</th>
							<th class="text-center">${__("Age")}</th>
							<th>${__("Remark")}</th>
						</tr>
					</thead>
					<tbody>
						${
							transaction_rows ||
							`<tr><td colspan="8" class="text-center text-muted">${__(
								"No transactions found."
							)}</td></tr>`
						}
					</tbody>
				</table>
			</div>`;
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
			const customer_code = frappe.utils.escape_html(String(data.customer_code));
			const customer_label = frappe.utils.escape_html(String(value || ""));
			return `<a href="#" class="account-receivable-customer" data-customer="${customer_code}">${customer_label}</a>`;
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
