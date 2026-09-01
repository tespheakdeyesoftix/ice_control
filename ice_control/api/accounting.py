
from builtins import str
import frappe
from frappe import _
from frappe.model.document import bulk_insert
from frappe.model.naming import make_autoname
from frappe.translate import print_language
import frappe

def submit_general_ledger_entry(docs:list[dict],run_commit:bool = True):
    def get_general_ledger_entry_record(docs:list[dict]):
        for d in docs:
            d["doctype"] = "GL Entry"
            doc = frappe.get_doc(d)
            if doc.amount and not (doc.credit_amount or doc.debit_amount ):
                root_type = frappe.get_cached_value("Chart of Account",doc.account,"root_type")
                if root_type in ["Asset","Expenses"]:
                    if doc.amount>0:
                        doc.debit_amount = abs(doc.amount)
                    else:
                        doc.credit_amount = abs(doc.amount)
                else:
                    if doc.amount>0:
                        doc.credit_amount = abs(doc.amount)
                    else:
                        doc.debit_amount = abs(doc.amount)
            doc.name = make_autoname("hash")
            yield doc
    if run_commit:
        frappe.db.commit()

    bulk_insert("GL Entry", get_general_ledger_entry_record(docs=docs) , chunk_size=10000)

def cancel_general_ledger_entery(doctype,docname):
    outlet = frappe.get_cached_value(doctype,docname,"outlet") or ""
    filters = "where voucher_type='{}' and voucher_no='{}'".format(doctype,docname)
    if doctype == "Sale":
        sale_id = frappe.db.get_value(doctype, docname, 'id')
        filters = "where sale_id='{}'".format(sale_id)
    frappe.db.sql("update `tabGL Entry` set is_cancelled=1 {0}".format(filters))
    frappe.db.commit()
    sql = "select * from `tabGL Entry` {0}".format(filters)
    data = frappe.db.sql(sql,as_dict=1)
    docs = []
    for r in data:
        doc = {
                "doctype":"GL Entry",
                "posting_date":r["posting_date"],
                "account":r["account"],
                "credit_amount":r["debit_amount"],
                "debit_amount":r["credit_amount"],
                "against":r["against"],
                "against_voucher_type":"Sale",
                "against_voucher_no": r["against_voucher_no"],
                "voucher_type":doctype,
                "voucher_no":docname,
                "remark": r["remark"],
                "party_type": r["party_type"],
                "party": r["party"],
                "is_cancelled":1,
                "outlet":outlet
            }
        docs.append(doc)
    submit_general_ledger_entry(docs)

def get_account_type(account:str) -> str:
    return frappe.get_cached_value("Chart of Account",account, "account_type")

def get_customer_credit_balance(customer:str, outlet:str , date:str|date)->float:
    # get credit from database
    sql = """
        select  
            sum(debit_amount- credit_amount) as total 
        from `tabGL Entry` 
        where 
            account_type = 'Receivable' and 
            party = %(customer)s and 
            outlet = %(outlet)s and 
            posting_date <= %(date)s
    """
    data = frappe.db.sql(sql, {"customer":customer,"outlet":outlet, "date":date},as_dict =1)
    
    return data[0].get("total") or 0