frappe.pages['server-report-viewer'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Server Report Viewer',
		single_column: true
	});
}