import frappe
from ice_control.api import customer as customer_api
@frappe.whitelist(methods=["GET"])
def get_customer_product_prices(customer: str) -> list[dict]:
    return customer_api.get_customer_product_prices(
        customer=customer
    )
@frappe.whitelist(methods=["GET"])
def get_all_customer_product_prices() -> list[dict]:
    return customer_api.get_all_customer_product_prices()

