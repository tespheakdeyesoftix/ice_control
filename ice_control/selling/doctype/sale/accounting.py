import frappe
from ice_control.api.accounting import submit_general_ledger_entry,get_account_type



def submit_to_gl_entry(self):
    frappe.db.sql("delete from `tabGL Entry` where voucher_type='Sale' and voucher_no=%(voucher_no)s",{
        "voucher_no":self.name
    })

    if self.total_amount <= 0:
        return

    outlet = frappe.get_cached_doc("Outlet",self.outlet)    
    docs = []
    base_doc = {
        "outlet":self.outlet,
        "posting_date":self.posting_date,
        "voucher_type":"Sale",
        "voucher_no":self.name,
        "party_type":"Customer",
        "party_name":self.customer_name,
        "party":self.customer,
        "amount":self.total_amount,
        
    }
    # income
    
    docs.append( {
        **base_doc,
        "account":outlet.default_income_account,
        "account_type":get_account_type(outlet.default_income_account)
    })


    # receivale
    docs.append( {
        **base_doc,
        "account":outlet.default_receivable_account,
        "account_type":get_account_type(outlet.default_receivable_account)
    })

    submit_general_ledger_entry(docs,False)
