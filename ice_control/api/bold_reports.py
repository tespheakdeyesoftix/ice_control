import frappe
from frappe import _


def _validate_report_access(report_path: str) -> None:
	report_name = frappe.db.get_value(
		"System Report",
		{"report_url": report_path},
		"name",
	)

	if not report_name:
		frappe.throw(_("You are not permitted to view this report."), frappe.PermissionError)

	allowed_roles = frappe.get_all(
		"Has Role",
		filters={
			"parent": report_name,
			"parenttype": "System Report",
			"parentfield": "roles",
		},
		pluck="role",
	)
	user_roles = set(frappe.get_roles(frappe.session.user))

	if allowed_roles and not user_roles.intersection(allowed_roles):
		frappe.throw(_("You are not permitted to view this report."), frappe.PermissionError)


def _get_bold_reports_config() -> dict[str, str]:
	config = frappe.conf.get("bold_reports") or {}
	required_keys = (
		"report_server_url",
		"report_service_url",
		"report_token",
	)
	missing_keys = [key for key in required_keys if not config.get(key)]

	if missing_keys:
		frappe.log_error(
			message=f"Missing Bold Reports configuration: {', '.join(missing_keys)}",
			title="Bold Reports configuration error",
		)
		frappe.throw(_("Bold Reports is not configured for this site."))

	return config


@frappe.whitelist()
def get_viewer_config(report_path: str) -> dict[str, str]:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)

	report_path = (report_path or "").strip()
	if not report_path:
		frappe.throw(_("A report path is required."))

	_validate_report_access(report_path)
	config = _get_bold_reports_config()

	frappe.local.response.setdefault("headers", {})["Cache-Control"] = "private, no-store"

	return {
		"report_server_url": str(config["report_server_url"]),
		"report_service_url": str(config["report_service_url"]),
		"service_authorization_token": str(config["report_token"]),
	}
