import frappe


def boot_session(bootinfo):
    # Frappe has already built module_sidebars before running boot_session.
    # Post-process that payload instead of replacing get_module_sidebars.
    from ice_control.overrides import customize_module_sidebars

    customize_module_sidebars(bootinfo)

    user = frappe.session.user

    business = frappe.get_cached_doc('Business Information')
    bootinfo.business_info = {
        'business_name_en': business.business_name_en,
        'business_name_kh': business.business_name_kh,
        'property_code': business.property_code,
        'photo': business.photo,
        'receipt_logo': business.receipt_logo,
        'address': business.address,
        'phone_number_1': business.phone_number_1,
        'phone_number_2': business.phone_number_2,
    }

    bootinfo.available_outlets = frappe.db.get_list("Outlet")

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
