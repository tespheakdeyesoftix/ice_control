import frappe


@frappe.whitelist(methods=["POST"])
def save_order(data: dict | str) -> dict:
    """Insert or update a Sale and return the saved document."""
    payload = frappe.parse_json(data) if isinstance(data, str) else data


    sale_data = payload.get("doc")
    if not isinstance(sale_data, dict):
        frappe.throw("Data must contain a Sale document in 'doc'", frappe.ValidationError)

    sale_data = sale_data.copy()
    name = sale_data.pop("name", None)
    sale_data.pop("doctype", None)

    if name:
        sale = frappe.get_doc("Sale", name)
        sale.update(sale_data)
        sale.save()
        action = "updated"
    else:
        sale = frappe.get_doc({"doctype": "Sale", **sale_data})
        sale.insert()
        action = "inserted"

    return  sale.as_dict()




