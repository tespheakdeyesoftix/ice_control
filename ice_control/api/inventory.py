import frappe
from typing import Any
def add_inventory_transaction(data=list[dict]):
    # here is sample data
    # {
	# 		"ref_doctype":self.doctype,
	# 		"ref_docname":self.name,
	# 		"posting_date":self.posting_date,
	# 		"stock_location":self.stock_location,
	# 		"product_code":p.product_code,
	# 		"unit":p.unit,
	# 		"quantity": p.quantity,
	# 		"multiplier":p.multiplier or 1,
	# 		"is_calculate_cost":1,
	# 		"cost":p.cost,
	# 		"note": "បញ្ជូលចំនួនបន្ថែមពីបញ្ជារទិញលេខ {}".format(self.name)
	# 	}
    # can be bulk insert in future
    if not data:
        return
    for doc in data:
        if doc.get("ref_doctype") == "Sale":
            product = frappe.get_doc("Product",doc.get("product_code"))
            if(len(product.product_materials)==0):
                update_stocks(doc)
            else:
                for pm in product.product_materials:
                    stock_location = doc.get("stock_location")
                    default_sale_stock_location = frappe.db.get_value("Product",pm.product_code,"default_sale_stock_location")
                    stock_location = default_sale_stock_location if not stock_location else stock_location
                    doc = {
                        "ref_doctype":doc.get("ref_doctype"),
                        "ref_docname":doc.get("ref_docname"),
                        "posting_date":doc.get("posting_date"),
                        "stock_location": stock_location,
                        "product_code":pm.product_code,
                        "unit":pm.unit,
                        "quantity": pm.quantity*doc.get("quantity"),
                        "multiplier":pm.multiplier or 1,
                        "is_calculate_cost":1,
                        "cost":get_stock_location_prouct(pm.product_code,stock_location).get("cost"),
                        "note": doc.get("note")
                    }
                    update_stocks(doc)
        else:
            update_stocks(doc)

def update_stocks(doc):
    doc = frappe.get_doc({"doctype":"Inventory Transactions",**doc})
    doc.base_unit = frappe.get_cached_value("Product",doc.get("product_code"),"unit")
    stock_location_product = get_stock_location_prouct(doc.get("product_code"), doc.get("stock_location"))
    doc.opening_quantity = 0
    if stock_location_product:
        doc.opening_quantity = stock_location_product.get("quantity")
        doc.current_cost = stock_location_product.get("cost") or 0
    doc.in_quantity = abs(doc.get("quantity") or 0) * (doc.get("multiplier") or 1) if (doc.get("quantity") or o) > 0 else 0 
    doc.out_quantity = abs(doc.get("quantity") or 0) * (doc.get("multiplier") or 1) if (doc.get("quantity") or 0) < 0 else 0 
    doc.balance = (doc.get("opening_quantity") or 0) + (doc.get("in_quantity") or 0) - (doc.get("out_quantity") or 0)       
    doc.insert(ignore_permissions=True)
    if not stock_location_product:
        frappe.get_doc({
            "doctype":"Stock Location Products",
            "product_code":doc.get("product_code"),
            "unit": doc.get("base_unit"),
            "stock_location":doc.get("stock_location"),
            "quantity": doc.get("balance"),
            "cost":doc.get("cost") or 0
        }).insert(ignore_permissions=True)
    else:
        frappe.db.set_value("Stock Location Products", stock_location_product.get("name"), {
            "quantity": doc.get("balance"),
            "cost": doc.get("cost") or 0
        })        


def get_stock_location_prouct(product,stock_location):
    sql = "select name, quantity,cost from `tabStock Location Products` where product_code = %(product_code)s and stock_location=%(stock_location)s limit 1"
    data = frappe.db.sql(sql,{"product_code":product, "stock_location":stock_location},as_dict = 1)
    if data:
        # check if not have cost then get max cost from stock location product
        if (data[0].get("cost") or 0 ) == 0:
            cost_data = frappe.db.sql("select max(cost) as cost from `tabStock Location Products` where product_code = %(product_code)s",{"product_code":product},as_dict=1)
            if cost_data:
                data[0]["cost"] = cost_data[0].get("cost",0)
            
        # if still dont have cost get from product purchase price
            if (data[0].get("cost") or 0 ) == 0:
                data[0]["cost"] = frappe.get_cached_value("Product",product,"purchase_price")

        return data[0]
    
    return  None

def get_product_quantity(product,stock_location):
    sql = "select quantity from `tabStock Location Products` where product_code = %(product_code)s and stock_location=%(stock_location)s limit 1"
    data = frappe.db.sql(sql,{"product_code":product, "stock_location":stock_location},as_dict = 1)
    if data:
        return data[0]["quantity"]
    return 0

@frappe.whitelist()
def get_product_unit(product_code):
    sql = """
        select unit from `tabProduct` where name = %(product_code)s
        union 
        select unit from `tabProduct Units` where parent = %(product_code)s
    """
    return frappe.db.sql(sql,{"product_code":product_code},as_dict = 1)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_outlet_products(doctype:str, txt:str, searchfield:str, start:int, page_len:int, filters: dict | None = None):
    outlet = filters.get("outlet")
    allow_purchase = filters.get("allow_purchse")
    extra_filters = ""
    if allow_purchase:
        extra_filters = "and b.allow_purchase = %(allow_purchase)s"
    if outlet:
        data = frappe.db.sql("""
        select 
        b.name,
        b.product_name
        from `tabProduct Outlet` a
        inner join `tabProduct` b on b.name = a.parent
        where coalesce(b.enabled,0) = 1 {0} and a.outlet = %(outlet)s group by b.name,b.product_name""".format(extra_filters),{"outlet":outlet,"allow_purchase":allow_purchase})
        return data
    else:
        data = frappe.db.sql("""
        select 
        name,
        product_name
        from `tabProduct`
        where coalesce(enabled,0) = 1 {0} group by name,product_name""".format(extra_filters),{"allow_purchase":allow_purchase})
        return data

@frappe.whitelist()
def get_product_units_multiplier(product_code:str="",unit:str=""):
    if product_code and unit:
        data = frappe.db.sql("select multiplier from `tabProduct Units` where parent = %(product_code)s and unit = %(unit)s",{"product_code":product_code,"unit":unit},as_dict=1)
        if data:
            return data[0].get("multiplier")
        else:
            product_name = frappe.db.get_value("Product",product_code,"product_name")
            frappe.throw("Product <strong>{}-{}</strong> does not have unit <strong>{}</strong>.".format(product_code,product_name,unit))
    else:
        return 1

@frappe.whitelist()
def get_purchase_cost(param: dict[str, Any]) -> Any:
    from ice_control.api.inventory import get_product_units_multiplier
    doc = param.get("doc")
    product = param.get("product")
    if frappe.db.exists("Product",product.get("product_code")):
        base_unit,purchase_price,cost = frappe.db.get_value("Product",product.get("product_code"),["unit","purchase_price","cost"])
        multiplier = (get_product_units_multiplier(product.get("product_code"),product.get("unit")) or 0)
        vendor_price = frappe.db.sql("""select 
                                            cost 
                                        from `tabVendor Product Price` 
                                        where product = %(product_code)s and 
                                        stock_location = %(stock_location)s and
                                        unit = %(unit)s and
                                        parent = %(party)s""",{"product_code":product.get("product_code"),"stock_location":doc.get("stock_location"),"unit":product.get("unit"),"party":doc.get("party")},as_dict=1)
        if vendor_price:
            return {"cost":vendor_price[0].get("cost"),"multiplier":multiplier}
        else:
            stock_location_product = frappe.db.sql("""select 
                                                cost
                                            from `tabStock Location Products` 
                                            where product_code = %(product_code)s and 
                                            stock_location = %(stock_location)s and 
                                            unit = %(unit)s""",{"product_code":product.get("product_code"),"stock_location":doc.get("stock_location"),"unit":base_unit},as_dict=1)
            if stock_location_product:
                return {"cost": stock_location_product[0].get("cost")*multiplier,"multiplier":multiplier}
            else:
                p_cost = (purchase_price or cost) * multiplier
                return {"cost": p_cost,"multiplier":multiplier}

@frappe.whitelist()
def calculate_cost(product_code:str,stock_location:str,new_qty:float,new_cost:float):
    if frappe.db.exists("Product",product_code):
        costing_method = frappe.db.get_value("Product",product_code,"costing_method")
        current_cost = 0
        current_qty = 0
        current_value = 0
        base_unit = ""
        slp = frappe.db.sql("""
                    select 
                        quantity,
                        cost,
                        unit 
                    from `tabStock Location Products` 
                    where product_code=%(product_code)s and 
                    stock_location=%(stock_location)s""",{"product_code":product_code,"stock_location":stock_location},as_dict=1)
        if slp:
            current_cost = slp[0].get("cost")
            current_qty = slp[0].get("quantity")
            current_value = current_cost * current_qty
            base_unit = slp[0].get("unit")
        if costing_method == "Fixed Cost":
            return current_cost
        else:
            new_value = new_qty*new_cost
            total_value = new_value+current_value
            new_cost = total_value/(current_qty+new_qty)
            return round(new_cost,4)
    else:
        return 0