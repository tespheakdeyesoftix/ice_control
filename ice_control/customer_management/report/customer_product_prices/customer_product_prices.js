// Copyright (c) 2025, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Product Prices"] = {
		onload: function(report) {
		report.page.add_inner_button(__("Preview Report"), function () {
			frappe.query_report.refresh();
		});
		 
	},
	filters: [
		{
			"fieldname": "customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"options":"Customer Group",
			"on_change": function (query_report) {

			},
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options":"Customer",
			"on_change": function (query_report) {

			},
		},
		{
			"fieldname": "product_category",
			"label": __("Product Category"),
			"fieldtype": "Link",
			"options":"Product Category",
			"on_change": function (query_report) {

			},
		},
		
	],
};
