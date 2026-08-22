import frappe

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
        doc = frappe.get_doc({"doctype":"Inventory Transactions",**doc})
        doc.base_unit  = frappe.get_cached_value("Product",doc.product_code,"unit")
        stock_location_product = get_stock_location_prouct(doc.product_code, doc.stock_location)
   

        doc.opening_quantity = 0
        if stock_location_product:
            doc.opening_quantity = stock_location_product.get("quantity")
            doc.current_cost = stock_location_product.get("cost") or 0
        if doc.unit ==doc.base_unit:
            doc.in_quantity = abs(doc.quantity) if doc.quantity > 0 else 0 
            doc.out_quantity = abs(doc.quantity) if doc.quantity < 0 else 0 
        else:
            doc.in_quantity = abs(doc.quantity or 0) * (doc.multiplier or 1) if (doc.quantity or o) > 0 else 0 
            doc.out_quantity = abs(doc.quantity or 0) * (doc.multiplier or 1) if (doc.quantity or 0) < 0 else 0 
        doc.balance = (doc.opening_quantity or 0) + (doc.in_quantity or 0) - (doc.out_quantity or 0)
        
        product_cost = stock_location_product.get("cost") if stock_location_product else (doc.cost or 0)
        if doc.is_calculate_cost==1 and stock_location_product:
            old_cost = (stock_location_product.get("quantity") or 0 ) * (stock_location_product.get("cost") or 0)           
            if doc.quantity==0:
                product_cost = doc.cost
            elif doc.quantity>0:
                new_cost = (abs(doc.in_quantity) or 0) * (doc.cost or 0)
                product_cost = (old_cost + new_cost) /  ((stock_location_product.get("quantity") or 0 ) + (doc.in_quantity or 0))
            else:
                product_cost = 0#To do
        else:
            product_cost = doc.cost        
        doc.insert(ignore_permissions=True)
        if not stock_location_product:
            frappe.get_doc({
                "doctype":"Stock Location Products",
                "product_code":doc.product_code,
                "unit": doc.base_unit,
                "stock_location":doc.stock_location,
                "quantity": doc.balance,
                "cost":doc.cost or 0
            }).insert(ignore_permissions=True)
        else:
            frappe.db.set_value("Stock Location Products", stock_location_product.get("name"), {
                "quantity": doc.balance,
                "cost": product_cost or 0
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

