import frappe


@frappe.whitelist()
def get_default_payment_type():
    payment_type = ""
    currency = ""
    business_info = frappe.get_cached_doc("Business Information")
    data = frappe.db.sql("select name,currency from `tabPayment Type` where is_default = 1 limit 1",as_dict=1)
    if data:
        payment_type = data[0].get("name")
        currency = data[0].get("currency")
    else:
        data = frappe.db.sql("select name,currency from `tabPayment Type` where currency = %(currency)s order by creation desc limit 1",{"outlet":business_info.default_currency},as_dict=1)
        payment_type = data[0].get("name")
        currency = data[0].get("currency")
    exchange_rate = frappe.db.sql("""
                                    select 
                                        currency_exchange_rate 
                                    from `tabExchange Rate` 
                                    where from_currency = %(from_currency)s and to_currency = %(to_currency)s 
                                    order by creation desc limit 1""",
                                     {"from_currency":currency,"to_currency":business_info.default_currency},as_dict=1)
    return {
        "payment_type": payment_type,
        "exchange_rate": exchange_rate[0].get("currency_exchange_rate") or 1,
        "currency": currency
    }

@frappe.whitelist()
def get_exchange_rate(currency:str):
    business_info = frappe.get_cached_doc("Business Information")
    exchange_rate = frappe.db.sql("""
                                    select 
                                        currency_exchange_rate 
                                    from `tabExchange Rate` 
                                    where from_currency = %(from_currency)s and to_currency = %(to_currency)s 
                                    order by creation desc limit 1""",
    {"from_currency":business_info.default_currency,"to_currency":currency},as_dict=1)
    return exchange_rate[0].get("currency_exchange_rate") or 1

@frappe.whitelist()
def money_to_word(amount :float=7569556,currency :str="KHR"):
    amount = str(amount)
    if len(amount)>6:
        first_number = int(amount[:len(amount) - 6])
        return number_to_word(int(first_number)) + "លាន" + number_to_word(int(amount[-6:] )) + " " + ("រៀល" if currency=="KHR" else "ដុល្លា")
    else:
        return number_to_word(int(amount)) + " " + ("រៀល" if currency=="KHR" else "ដុល្លា")
    
@frappe.whitelist()
def number_to_word(amount :float=7569556):
    khmer_digit = ["","មួយ","ពីរ","បី","បួន","ប្រាំ","ប្រាំមួយ","ប្រាំពីរ","ប្រាំបី","ប្រាំបួន"]
    khmer_unit = ["","ដប់","រយ","ពាន់","ម៉ឺន","សែន","លាន"]
    tens_words = ['', 'ដប់', 'ម្ភៃ', 'សាមសិប', 'សែសិប', 'ហាសិប', 'ហុកសិប', 'ចិតសិប', 'ប៉ែតសិប', 'កៅសិប']
    khmer_number = ""
    n = len(str(amount))
    for index, w in enumerate(str(amount)):
        n= n -1
        if n == 1: # we are at 10 word
            khmer_number +=tens_words[int(w)] 
        else:
            khmer_number = khmer_number + khmer_digit[int(w)] 
            
        if w !="0" and n>1:
            khmer_number = khmer_number + khmer_unit[n]
    return khmer_number

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_products_by_outlet(doctype:str, txt:str, searchfield:str, start:int, page_len:int, filters:dict):
    outlet = filters.get("outlet")
    product_codes = filters.get("product_codes") or [""]
    return frappe.db.sql(
        """
        SELECT DISTINCT p.name, p.product_name
        FROM `tabProduct` p
        INNER JOIN `tabProduct Outlet` po
            ON po.parent = p.name
        WHERE
            p.name not in %(product_codes)s  and
            po.outlet = %(outlet)s
          AND po.parenttype = 'Product'
          AND po.parentfield = 'product_outlet'
          AND (
              p.name LIKE %(txt)s
              OR p.product_name LIKE %(txt)s
          )
        ORDER BY p.name
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "outlet": outlet,
            "product_codes":product_codes,
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len,
        },
    )

@frappe.whitelist()
def get_default_bank():
    data = frappe.db.sql("select name,bank_number from `tabBanks` where is_default = 1 and enabled = 1 limit 1",as_dict=1)
    if data:
        return {"name":data[0].get("name"),"bank_number":data[0].get("bank_number")}
    else:
        return {"name":"","bank_number":""}

@frappe.whitelist()
def get_product_default_account(product_code:str,outlet:str):
    if not outlet:
        frappe.throw("Please select outlet first")
    category = frappe.db.get_value("Product", product_code, "product_category")
    default_income_account = frappe.db.get_value("Product Default Accounts", {"parent":product_code,"outlet":outlet}, "default_income_account")
    if not default_income_account:
        default_income_account = frappe.db.get_value("Product Category Default Accounts", {"parent":category,"outlet":outlet}, "default_income_account")
    if not default_income_account:
        default_income_account = frappe.db.get_value("Outlet", outlet, "default_income_account")
    default_expense_account = frappe.db.get_value("Product Default Accounts", {"parent":product_code,"outlet":outlet}, "default_expense_account")
    if not default_expense_account:
        default_expense_account = frappe.db.get_value("Product Category Default Accounts", {"parent":category,"outlet":outlet}, "default_expense_account")
    if not default_expense_account:
        default_expense_account = frappe.db.get_value("Outlet", outlet, "default_cost_of_goods_sold_account")
    default_adjustment_account = frappe.db.get_value("Product Default Accounts", {"parent":product_code,"outlet":outlet}, "default_adjustment_account")
    if not default_adjustment_account:
        default_adjustment_account = frappe.db.get_value("Product Category Default Accounts", {"parent":category,"outlet":outlet}, "default_adjustment_account")
    if not default_adjustment_account:
        default_adjustment_account = frappe.db.get_value("Outlet", outlet, "default_stock_adjustment_account")
    default_stock_account = frappe.db.get_value("Product Default Accounts", {"parent":product_code,"outlet":outlet}, "default_stock_account")
    if not default_stock_account:
        default_stock_account = frappe.db.get_value("Product Category Default Accounts", {"parent":category,"outlet":outlet}, "default_stock_account")
    if not default_stock_account:
        default_stock_account = frappe.db.get_value("Outlet", outlet, "default_stock_account")
    return {
        "default_income_account":default_income_account,
        "default_expense_account":default_expense_account,
        "default_adjustment_account":default_adjustment_account,
        "default_stock_account":default_stock_account
    }

@frappe.whitelist()
def get_outlet_default_accounts(outlet:str):
    doc = frappe.get_cached_doc("Outlet", outlet)
    return{
        "default_receivable_account":doc.default_receivable_account,
        "default_income_account":doc.default_income_account,
        "default_payable_account":doc.default_payable_account,
        "default_purchase_write_off_account":doc.default_purchase_write_off_account,
        "default_cost_of_goods_sold_account":doc.default_cost_of_goods_sold_account,
        "default_stock_adjustment_account":doc.default_stock_adjustment_account,
        "default_stock_account":doc.default_stock_account
    }


@frappe.whitelist()
def get_payment_type_default_account(payment_type:str,outlet:str):
    if not outlet:
        frappe.throw("Please select outlet first")
    default_account = frappe.db.get_value("Has Default Account", {"outlet":outlet,"parent":payment_type}, "default_sale_payment_account")
    return {"default_account":default_account}