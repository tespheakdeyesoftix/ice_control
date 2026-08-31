import frappe
from frappe import _

from ice_control.api.bold_reports import _get_report_roles


@frappe.whitelist()
def get_report_list():
	"""Return backend reports enabled for the report-list page."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)

	reports = frappe.get_all(
		"System Report",
		filters={
			"show_in_report_list": 1,
			"is_backend_report": 1,
			"is_group": 0,
		},
		fields=[
			"name",
			"report_title",
			"report_url",
			"parent_system_report",
			"sort_order",
		],
		order_by="parent_system_report asc, sort_order asc, report_title asc",
		limit_page_length=0,
	)
	user_roles = set(frappe.get_roles(frappe.session.user))

	return [
		report
		for report in reports
		if not (allowed_roles := _get_report_roles(report.name))
		or user_roles.intersection(allowed_roles)
	]
