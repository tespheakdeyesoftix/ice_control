import frappe
from ice_control.api import utils

@frappe.whitelist()
def get_doctype_meta(doctype: str):
    return frappe.get_meta(doctype)

@frappe.whitelist(allow_guest=True)
def get_setting(station_name:str="",outlet:str="")->dict:
    return utils.get_setting(station_name=station_name,outlet = outlet)



@frappe.whitelist(methods=["POST"])
def update_doc(
    doctype: str,
    name: str,
    data: dict | str,
    doc_flags: dict | str | None = None,
):
   
    return utils.update_doc(
        doctype=doctype,
        name=name,
        data=data,
        doc_flags=doc_flags
    )

@frappe.whitelist(methods=["POST"])
def get_bold_report_config()->dict:
    return frappe.conf.get("bold_reports")
