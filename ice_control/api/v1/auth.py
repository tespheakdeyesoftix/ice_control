
import frappe
from frappe.auth import LoginManager


@frappe.whitelist(allow_guest=True, methods=["POST"])
def login(usr: str, pwd: str) -> None:
    """Authenticate a user and create Frappe's cookie-based session."""
    frappe.form_dict.update({"usr": usr, "pwd": pwd})

    login_manager = LoginManager()
    login_manager.login()
