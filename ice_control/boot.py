import frappe

def boot_session(bootinfo):
    user = frappe.session.user

    # Admin sees everything
    if user == "Administrator":
        bootinfo.employee_outlet = None
        bootinfo.employee_outlet_type = None
        return

    # Get default_outlet from Employee (match by user_id)
    outlet = frappe.db.get_value("Employee", {"user_id": user}, "default_outlet")

    # Fallback: match by username if user_id is empty
    if not outlet:
        outlet = frappe.db.get_value("Employee", {"username": user}, "default_outlet")

    bootinfo.employee_outlet = outlet

    # Determine outlet type for easy checking
    if outlet:
        if "ទឹកកកដើម" in outlet or "block" in outlet.lower():
            bootinfo.employee_outlet_type = "block_ice"
        elif "ទឹកកកអនាម័យ" in outlet or "tube" in outlet.lower():
            bootinfo.employee_outlet_type = "tube_ice"
        else:
            bootinfo.employee_outlet_type = "unknown"
    else:
        bootinfo.employee_outlet_type = None
