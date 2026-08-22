
import frappe
from frappe.auth import LoginManager
from frappe import _

@frappe.whitelist(allow_guest=True, methods=["POST"])
def login(usr: str, pwd: str,outlet:str) -> None:
    """Authenticate a user and create Frappe's cookie-based session."""
    frappe.form_dict.update({"usr": usr, "pwd": pwd})
    # validate employee
    employee = validate_employee(usr, outlet)
    



    login_manager = LoginManager()
    login_manager.login()

    # LoginManager returns early for 2FA and forced password-reset flows.
    # Only add account information after a session has been authenticated.
    if frappe.session.user == "Guest":
        return

    


    user = frappe.get_cached_doc("User", frappe.session.user)
    frappe.local.response.update(
        {
            "user": user.name,
            "email": user.email,
            "username": user.username,
            "user_type": user.user_type,
            "user_image": user.user_image,
            "roles": frappe.get_roles(user.name),
            "employee":employee
            
            
        }
    )

def validate_employee(user:str,outlet:str)->dict:
    sql="select name from `tabEmployee` where username=%(user)s"
    emp = frappe.db.sql(sql,{"user":user},as_dict=1)
    if not emp:
        frappe.throw(
            _("ឈ្មោះអ្នកប្រើប្រាស់ ឬលេខសម្ងាត់មិនត្រឹមត្រូវ"),
            frappe.AuthenticationError
        )

    emp = frappe.get_cached_doc("Employee",emp[0].get("name"))
    if not emp.outlets:
        frappe.throw(
            _("អ្នកមិនមានសិទ្ធចេញប៉ុងទេ"),
            frappe.AuthenticationError
        )

    if not outlet in [x.outlet for x in emp.outlets]:
        frappe.throw(
            _("អ្នកមិនមានសិទ្ធចេញប៉ុងទេ នៅទីតាំងលក់ {0}".format(outlet)),
            frappe.AuthenticationError
        )
    
 

    return emp





