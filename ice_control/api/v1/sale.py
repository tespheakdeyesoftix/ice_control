import frappe
from ice_control.api import sale as sale_api
from datetime import date, datetime

@frappe.whitelist()
def search_bill_for_edit(outlet:str,keyword:str):
    return sale_api.search_bill_for_edit(outlet = outlet, keyword=keyword)


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

    frappe.msgprint("រក្សាទុកបុងបានសម្រេច",   title="Success",indicator="green")

    return  sale.as_dict()

@frappe.whitelist()
def get_total_pending_order(outlet:str)-> int:
    sql="select count(*) as total from `tabSale` where outlet=%(outlet)s and sale_status = 'Draft'"
    data = frappe.db.sql(sql,{"outlet":outlet},as_dict=1)
    return data[0].get("total")


@frappe.whitelist(methods=["POST"])
def delete_sale(doc_name:str, station_name:str="", note:str = None):
    return sale_api.delete_sale(
        doc_name = doc_name,
        note = note,
        station_name=station_name
    )


@frappe.whitelist()
def test_me():
    return sale_api.get_daily_sale_summary(
        outlet = "ទឹកកកដើម",
        posting_date = frappe.utils.today()
    )


@frappe.whitelist(methods=["GET","POST"])
def get_daily_sale_summary(outlet:str, posting_date:str|date = None) ->dict:
    return sale_api.get_daily_sale_summary(
        outlet = outlet,
        posting_date = posting_date
    )


@frappe.whitelist()
def get_max_pending_order_date(outlet:str)->dict:
    return sale_api.get_max_pending_order_date(outlet=outlet)

@frappe.whitelist()
def get_sale_payment_history(sale_name:str)->dict:
    return sale_api.get_sale_payment_history(sale_name=sale_name)