from builtins import str
import frappe
import base64
from frappe import _
import json
from frappe.model.document import bulk_insert
from frappe.model.naming import make_autoname
from frappe.translate import print_language
import os
import frappe
from frappe.utils import get_files_path
from frappe.utils.file_manager import save_file

from frappe.utils.caching import redis_cache
from datetime import date, datetime



def replace_format(string):
    from datetime import datetime
    short_year = datetime.now().strftime("%y")
    year = datetime.now().strftime("%Y")
    month = datetime.now().strftime("%m")
    return string.replace('.', '').replace('YYYY', year).replace('yyyy', year).replace('YY', short_year).replace('yy', short_year).replace('MM', month).replace('#', '')

@frappe.whitelist()
def reset_sale_transaction(password):
    if password == "eposadmin@855855" and frappe.session.user == "Administrator":

        frappe.db.sql("delete from `tabSale`")
        frappe.db.sql("delete from `tabSale Products`")
        frappe.db.sql("delete from `tabSale Payment`")
        frappe.db.sql("delete from `tabBulk Sale Payment`")
        frappe.db.sql("delete from `tabBulk Sale`")
        frappe.db.sql("delete from `tabClosed Selling Date`")
        frappe.db.sql("delete from `tabClosed Selling Date Data`")
        frappe.db.sql("delete from `tabClosed Selling Date Items`")
        frappe.db.sql("delete from `tabStock In`")
        frappe.db.sql("delete from `tabStock In Products`")

        doctypes = ["Sale","Sale Payment","Bulk Sale Payment","Closed Selling Date","Closed Selling Date Data","Stock In","Journal Entry"]
        for d in doctypes:
            formats = ""
            if d == "Closed Selling Date Data":
                formats = "CSDD.YYYY.-.#####"
            else:
                formats =  frappe.get_meta(d).get_field("naming_series").options
            if formats:
                if "#" in formats:
                    format_text = replace_format(formats)
                    sql = "update `tabSeries` set current = 0 where name='{}'".format(format_text)
                    frappe.db.sql(sql)
        return "reset"
    else:
        return "wrong password"

def ensure_date(posting_date,creation):
    from datetime import datetime,date,time
    a = datetime.strptime(creation, "%Y-%m-%d %H:%M:%S.%f")
    now = time(a.hour, a.minute, a.second)
    if isinstance(posting_date, str):
        return  datetime.combine(datetime.strptime(posting_date, "%Y-%m-%d").date(), now)
    elif isinstance(posting_date, datetime):
        return posting_date
    elif isinstance(posting_date, date):
        return  datetime.combine(posting_date, now)
    else:
        return datetime.now()

# we call this from hook
@frappe.whitelist()
def validate_close_date(doc,method):
    if doc.doctype in get_validate_close_date_doctype():
        frappe.msgprint("validate close date from hook")
        get_previous_closed_date(doc.posting_date, doc.creation, doc.outlet)

@redis_cache(ttl=60*60*24)
def get_validate_close_date_doctype():
    data = frappe.db.sql("select closed_doctype from `tabClosed Selling Date Doctype`",as_dict = 1)
    return [d.get("closed_doctype") for d in data]

@frappe.whitelist()
def get_previous_closed_date(posting_date:str|date,creation:str|datetime,outlet:str|None):

    b = frappe.db.sql("select posting_date,creation from `tabClosed Selling Date` where docstatus=1 and outlet = '{0}' order by CONCAT(posting_date,' ',DATE_FORMAT(modified, '%H:%i:%s')) desc limit 1".format(outlet),as_dict=1)

    if len(b or []) > 0:
        posting_date =frappe.utils.getdate(ensure_date(str(posting_date),str(creation)))
        previous_closed_date = frappe.utils.getdate(ensure_date(str(b[0]["posting_date"]),str(b[0]["creation"])))


        if previous_closed_date >= posting_date:
            frappe.throw("អ្នកមិនធ្វើប្រតិបត្តិការនេះបានទេ។ ព្រោះថ្ងៃទី {} ត្រូបានបិទបញ្ជីររួចហើយ.".format(frappe.format(previous_closed_date,{"fieldtype":"Date"})))


@frappe.whitelist()
def get_currency_symbol(currency):
    symbol = frappe.get_cached_value("Currency", currency, "symbol")
    return symbol

@frappe.whitelist()
def get_meta(doctype=None):
    data =  frappe.get_meta(doctype)
    return data

@frappe.whitelist(allow_guest=True)
def get_setting(station_name:str="",outlet:str=None):
    data  = frappe.get_cached_doc("Business Information",None)
    data =json.loads( frappe.as_json(data))

 

    if station_name:

        if frappe.db.exists("Station", station_name):
            data["can_login_multi_site"]  = frappe.get_cached_value("Station",station_name,"can_login_multi_site")

            data["outlet"]  = outlet or  frappe.get_cached_value("Station",station_name,"outlet")

            data["default_unit"]  = frappe.get_cached_value("Outlet",data.get("outlet"),"default_unit")
            data["default_stock_location"]  = frappe.get_cached_value("Outlet",data.get("outlet"),"default_stock_location")


    data["currency"] = frappe.get_cached_value("System Settings", None, "currency")
    data["currency_symbol"] = frappe.get_cached_value("Currency",data.get("currency"),"symbol")
    data["second_currency_symbol"] = frappe.get_cached_value("Currency",data.get("second_currency"),"symbol")

    # payment type
    payment_types = frappe.db.get_list("Payment Type",["name","currency"],ignore_permissions=True)

    for p in payment_types:
        p["exchange_rate"] = get_exchange_rate(from_currency=p.get("currency"), to_currency = data.get("currency"))
    data["payment_types"] = payment_types

    exchange_rate = get_exchange_rate(from_currency=data.get("currency"),to_currency=data.get("second_currency"))
    data["exchange_rate"]  = exchange_rate
    data["exchange_rate_display"]  = exchange_rate if exchange_rate>1 else 1/exchange_rate
    return data



def get_exchange_rate(from_currency:str=None, to_currency:str=None)->float:
    if not to_currency:
        to_currency = frappe.get_cached_value("Business Information",None,"default_currency")
        
    exchange_rate = 1
    exchange_rate_data =  frappe.db.sql("select currency_exchange_rate from `tabExchange Rate` where from_currency=%(from_currency)s and to_currency =  %(to_currency)s and docstatus = 1 order by creation desc  limit 1",{"from_currency":from_currency,"to_currency":to_currency},as_dict = 1)
    if exchange_rate_data:
        from decimal import Decimal
        exchange_rate = Decimal( exchange_rate_data[0].get("currency_exchange_rate",1))
    return exchange_rate



@frappe.whitelist(allow_guest=True)
def check_api_url(property_code,station_name,old_station_name):
    if not station_name:
        frappe.throw(_("Please enter your device name"))

    doc = frappe.get_cached_doc("Business Information",None)
    if doc.property_code ==  property_code:

        # check station
        if station_name != old_station_name:
            if frappe.db.exists("Station", station_name):
                if frappe.get_cached_value("Station",station_name,"is_used") ==1:
                    frappe.throw(_("This station name is already in used"))
            else:
                frappe.throw(_("This station name is not exist"))



        return {
            "property_code":property_code,
            "property_name":doc.business_name_en,
            "photo":doc.photo,
            "station_name":station_name,
            "outlet":frappe.get_cached_value("Station",station_name,"outlet"),
            "can_login_multi_site":frappe.get_cached_value("Station",station_name,"can_login_multi_site")
    }

    frappe.throw(_("Property {property_code} does not exist").format(property_code=property_code))


def generate_keys(user):
	"""
	generate api key and api secret

	:param user: str
	"""
	# frappe.only_for("System Manager")
	user_details = frappe.get_doc("User", user)
	api_secret = frappe.generate_hash(length=15)
	# if api key is not set generate api key
	if not user_details.api_key:
		api_key = frappe.generate_hash(length=15)
		user_details.api_key = api_key
	user_details.api_secret = api_secret
	user_details.save(ignore_permissions=True)

	return api_secret



@frappe.whitelist(allow_guest=True)
def check_user_login(property):

    if frappe.session.sid == "Guest":
        frappe.response["message"] =  frappe.session.sid
    else:
        frappe.response["message"] = get_response_user_information(property)

def get_response_user_information(property):
    phone_number =""
    address =""
    employee_id=""
    position=""
    photo=""
    home_page = ""
    role_profile=""
    user = frappe.get_doc("User", frappe.session.user)


    sql = """
        select
           *
        from `tabEmployee`
        where
            user_id = '{}'
        limit 1
    """.format(frappe.session.user)

    data = frappe.db.sql(sql, as_dict=1)
    user_info={}

    if data:
        position = data[0].get("position")
        employee_id = data[0].get("name")
        phone_number = data[0].get("phone_number")
        address = data[0].get("address")
        photo = data[0].get("photo")
        home_page = data[0].get("default_frontend_home_page")

        role_profile = data[0].get("role_profile")
        user_info=data[0]



    api_generate = generate_keys(frappe.session.user)
    # get home_page


    return {
            "username":user.username,
            "full_name":user.full_name,
            "role_profile":role_profile,
            "photo":photo,
            "phone_number":phone_number,
            "address":address,
            "name":frappe.session.user,
            "position":position,
            "token": base64.b64encode(str("{}:{}".format(user.api_key,api_generate)).encode("utf-8")).decode('utf-8'),
            "employee_id":employee_id,
            "home_page":home_page,
            "user_info":user_info


    }

 


@frappe.whitelist()
def getCurrentUser():
    return   frappe.get_cached_doc("User", frappe.session.user)

def get_default_outlet():
    sql="select default_outlet from `tabEmployee` where user_id = %(user_id)s"
    data = frappe.db.sql(sql,{"user_id":frappe.session.user},as_dict = 1)
    if data:
        return data[0].get("default_outlet")
    return frappe.get_list("Outlet",pluck='name')[0]



def money_to_word(amount=7569556,currency="KHR"):
    amount = str(amount)
    if len(amount)>6:
        first_number = int(amount[:len(amount) - 6])


        return number_to_word(int(first_number)) + "លាន" + number_to_word(int(amount[-6:] )) + " " + ("រៀល" if currency=="KHR" else "ដុល្លា")
    else:
        return number_to_word(int(amount)) + " " + ("រៀល" if currency=="KHR" else "ដុល្លា")

def number_to_word(amount=7569556):

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


def clear_cache(doc, method):
    frappe.clear_document_cache(doc.doctype,doc.name)
    get_validate_close_date_doctype.clear_cache()

@frappe.whitelist()
def add_audit_trail_log(data):
    if isinstance(data, list):
        for d in data:
            d["doctype"] = "Audit Trail Log"
            d["username"] = frappe.get_cached_value("User",frappe.session.user,"full_name")
            frappe.get_doc(d).insert(ignore_permissions=True)
    else:
        data["doctype"] = "Audit Trail Log"
        data["username"] = frappe.get_cached_value("User",frappe.session.user,"full_name")
        frappe.get_doc(data).insert(ignore_permissions=True)
    frappe.db.commit()



def get_sale_product_changed(old_list, new_list,compare_field="product_code"):
    result = {
        "quantity_changes": [],
        "price_changes": [],
        "removed_products": [],
        "added_products": []
    }

    # Convert to dict for easy lookup
    old_map = {item.get(compare_field): item for item in old_list if item.get(compare_field)}
    new_map = {item.get(compare_field): item for item in new_list if item.get(compare_field)}

    # 1. Check for quantity and price changes
    for code, old_item in old_map.items():
        new_item = new_map.get(code)
        if new_item:
            old_qty = old_item.get("total_sale_quantity", 0)
            new_qty = new_item.get("total_sale_quantity", 0)
            if old_qty != new_qty:
                result["quantity_changes"].append({
                    "name":old_item.get("name"),
                    "product_code": old_item.get("product_code"),
                    "product_name": old_item.get("product_name", ""),
                    "old_quantity": old_qty,
                    "new_quantity": new_qty,
                    "unit": new_item.get("unit"),
                    "stock_location": new_item.get("stock_location")
                })

            old_price = old_item.get("price", 0)
            new_price = new_item.get("price", 0)
            if old_price != new_price:
                result["price_changes"].append({
                    "product_code":old_item.get("product_code"),
                    "product_name": old_item.get("product_name", ""),
                    "old_price": old_price,
                    "new_price": new_price
                })

    # 2. Check for removed products
    for code, old_item in old_map.items():
        if code not in new_map:
            result["removed_products"].append({
                "name":old_item.get("name"),
                "product_code": old_item.get("product_code"),
                "product_name": old_item.get("product_name", ""),
                "quantity": old_item.get("quantity"),
                "price": old_item.get("price"),
                "unit":old_item.get("unit"),
                "stock_location":old_item.get("stock_location"),

            })

    # 3. Check for added products
    for code, new_item in new_map.items():
        if code not in old_map:
            result["added_products"].append({
                "name":new_item.get("name"),
                "product_code": new_item.get("product_code"),
                "product_name": new_item.get("product_name", ""),
                "quantity": new_item.get("quantity", 0),
                "price": new_item.get("price", 0),
                "unit":new_item.get('unit'),
                "stock_location":new_item.get('stock_location')
            })

    return result



@frappe.whitelist()
def get_count(doctype, filters=None, or_filters=None):
    table = f"`tab{doctype}`"

    where_clauses = []
    params = {}

    # AND filters: [["field", "=", value], ...]
    if filters:
        for idx, flt in enumerate(filters):
            field, op, value = flt
            key = f"and_param_{idx}"
            where_clauses.append(f"{field} {op} %({key})s")
            params[key] = value

    # OR filters: [["field", "like", value], ...]
    if or_filters:
        or_parts = []
        for idx, flt in enumerate(or_filters):
            field, op, value = flt
            key = f"or_param_{idx}"
            or_parts.append(f"{field} {op} %({key})s")
            params[key] = value

        # join OR conditions
        where_clauses.append("(" + " OR ".join(or_parts) + ")")

    # Build WHERE
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # Build final SQL
    sql = f"""
        SELECT COUNT(*) AS total
        FROM {table}
        {where_sql}
    """

    # Execute SQL + return integer
    result = frappe.db.sql(sql, params, as_dict=True)
    return result[0].total if result else 0



 

def update_doc(
    doctype: str,
    name: str,
    data: dict | str,
    doc_flags: dict | str | None = None,
):
    if isinstance(data, str):
        data = json.loads(data)

    if isinstance(doc_flags, str):
        doc_flags = json.loads(doc_flags)

    print("DATA:", data)
    print("DOC FLAGS:", doc_flags)

    doc = frappe.get_doc(doctype, name)

    # Set document fields
    for field, value in data.items():
        doc.set(field, value)

    # Set Frappe document flags
    if doc_flags:
        doc.flags.update(doc_flags)

    doc.save()

    return doc



@frappe.whitelist()
@redis_cache(ttl=60*60)
def get_payment_types()->list[dict]:
    data =frappe.db.sql( "select name, currency from `tabPayment Type`",as_dict = 1)
    for d in data:
        d['exchange_rate'] = get_exchange_rate(d.get("currency"), frappe.get_cached_value("Business Information",None,"default_currency"))

    return data