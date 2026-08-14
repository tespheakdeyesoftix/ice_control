
import frappe

@frappe.whitelist()
def testme():
    return get_products()

@frappe.whitelist(methods=["POST"])
def get_products(outlet: str | None = None):
    sql="""
        select
            p.product_code,
            p.product_name,
            p.product_category,
            p.price,
            p.unit,
            p.color,
            p.photo,
            p.multiplier as multiplier,
            p.allow_sum_qty,
            p.allow_split_bill,
            p.default_sale_transaction_type 


        from `tabProduct` p
        where
            1=1
        
    """
    data = frappe.db.sql(sql,as_dict= 1)
    product_units = get_product_units() or []
    product_unit_product_codes = set(x.get("product_code") for x in product_units or [])
    
    for p in [x for x in data if x.get("product_code") in product_unit_product_codes]:
        p["product_units"] = [d for d in product_units if d.get("product_code") == p.get("product_code")]

    return data

def get_product_units():
    sql="""
        select
            parent as product_code,
            unit,
            price,
            multiplier,
            base_product_unit,
            photo
        from `tabProduct Units`
    """
    return frappe.db.sql(sql,as_dict=1)
