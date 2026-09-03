import frappe
from frappe.boot import build_entity_module_map


@frappe.whitelist()
def test():
    return frappe.boot.get_module_sidebars()


def customize_module_sidebars(bootinfo):
    """Post-process the sidebar payload created by Frappe during session boot."""
    sidebars = bootinfo.get("module_sidebars") or {}
    ice_control_sidebar = sidebars.get("ice_control")
    if not ice_control_sidebar:
        ice_control_sidebar = next(
            (sidebar for sidebar in sidebars.values() if sidebar.get("app") == "ice_control"),
            None,
        )

    if not ice_control_sidebar:
        return sidebars

    ice_control_items = ice_control_sidebar.get("items") or []
    for sidebar in sidebars.values():
        if sidebar.get("app") == "frappe":
            continue

        sidebar["items"] = list(ice_control_items)

    bootinfo.module_sidebars = sidebars

    bootinfo.entity_module = build_entity_module_map(sidebars)
    return sidebars
 
def on_session_creation():
    outlets = frappe.db.get_list("Outlet",pluck="name")
    if len(outlets) == 1:
        frappe.db.set_default("outlet", outlets[0])



  