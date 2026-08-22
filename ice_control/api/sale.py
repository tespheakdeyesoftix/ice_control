import frappe
from ice_control.selling.doctype.sale.sale import delete_bill
from datetime import date, datetime

def search_bill_for_edit(outlet:str,keyword:str):
    exists = frappe.db.exists("Sale", keyword)
    if exists:
        doc =  frappe.get_doc("Sale",keyword)
        # validate
        if doc.outlet != outlet:
            frappe.throw("បុងនេះមិនមាននៅក្នុងទីតាំងលក់ {0} ទេ".format(outlet) )
            
            

        if doc.can_edit_bill == 0:
            frappe.throw("អតិថិជននេះមិនអនុញ្ញត្តិអោយកែបុងទេ")
            
        
        if doc.sale_status == 'Deleted':
            frappe.throw("មិនអាចកែប្រែបុងដែលបានលុបបានទេ")

        if doc.status in ["Paid","Partially Paid"]:
            frappe.throw("មិនអាចកែប្រែបុងដែលបានបង់ប្រាក់បានទេ")

        # if bill already split not allow to edit also
        if doc.total_split_bill > 0: 
            frappe.throw("មិនអាចកែប្រែបុងដែលបានបំបែកហើយបានទេ")

        return doc.as_dict()

    else:
        frappe.throw("បុងលេខ {0} មិនមាននៅក្នុងប្រព័ន្ធទេ".format(keyword))

    



def delete_sale(doc_name:str,station_name:str="",  note:str = None) -> dict:
    return delete_bill(
        doc_name = doc_name,
        station_name = station_name,
        note = note
    )
    




def get_daily_sale_summary(outlet:str, posting_date:str|date = None) ->dict:
    posting_date = posting_date or frappe.utils.today()
    filter = {
        "posting_date":posting_date,
        "outlet": outlet
    }
    
    result = {
        "default_unit":frappe.get_cached_value("Outlet",outlet,"default_unit")
    }

    # kpi
    sql = """
        select 
            count(*) as total_order,
            sum(total_amount) as total_amount,
            sum(total_sale_quantity) as total_quantity
        from `tabSale` s 
        where
            s.posting_date = %(posting_date)s and 
            s.outlet = %(outlet)s  and 
            s.sale_status = "Closed"
    """
    data = frappe.db.sql(sql,filter,as_dict = 1)
    result = { **result, **data[0]}

    # get pending order
     # kpi
    sql = """
        select 
            count(*) as total_pending_order,
            sum(total_amount) as total_pending_amount,
            sum(total_sale_quantity) as total_pending_quantity
        from `tabSale` s 
        where
            s.outlet = %(outlet)s  and 
            s.sale_status = 'Draft'
    """

    data = frappe.db.sql(sql,filter,as_dict = 1)
    
    result = { **result, **data[0]}
    # sale product summary
    result["sale_product_summary"] = get_daily_sale_product_summary(outlet = outlet , posting_date = posting_date)

    # get deleted sale order
    
    result = {
        **result,
        **get_daily_deleted_order_summary(outlet = outlet, posting_date = posting_date)
    }


    return result


def get_daily_deleted_order_summary(outlet:str, posting_date:str|date)->dict:
    sql = """
        select 
            count(*) as total_deleted_order,
            coalesce(sum(total_amount),0) as total_deleted_amount,
            coalesce(sum(total_sale_quantity),0) as total_deleted_quantity
        from `tabSale` s 
        where
            s.outlet = %(outlet)s  and 
            s.sale_status = 'Deleted' and 
            DATE(s.deleted_date) = %(posting_date)s 
    """
    
    data = frappe.db.sql(sql,{"outlet":outlet,"posting_date":posting_date},as_dict = 1)
    return data[0]
    
def get_daily_sale_product_summary(outlet:str, posting_date:str|date)->lsit[dict]:
    sql="""
        select 
            sp.product_code,
            sp.product_name,
            sp.unit,
            sum(sp.quantity) as quantity,
            sum(sp.free_quantity) as free_quantity,
            sum(sp.return_quantity) as return_quantity,
            sum(sp.split_quantity) as split_quantity,
            sum(sp.total_sale_quantity) as total_sale_quantity,
            sum(sp.total_amount) as total_amount 
            
        from `tabSale Products` sp
        join `tabSale` s on s.name = sp.parent
        join `tabProduct` p on p.name = sp.product_code
        where
            s.outlet = %(outlet)s and 
            s.posting_date = %(posting_date)s and 
            s.sale_status = 'Closed'
        group by
            sp.product_code,
            sp.product_name,
            sp.unit
        order by p.sort_order, p.product_name
    """
    data = frappe.db.sql(
        sql,
        {"outlet":outlet, "posting_date":posting_date},
        as_dict = 1
    )
    return data

def get_max_pending_order_date(outlet:str)->dict:
    return frappe.db.sql(
        "select max(creation) as pending_date,count(*) as total_pending_order,sum(total_amount) as pending_order_amount from `tabSale` where sale_status = 'Draft' and outlet =%(outlet)s",
        {"outlet":outlet},
        as_dict = 1

    )[0]

def get_sale_payment_history(sale_name:str) ->list[dict]:
    sql ="""
        select 
            b.name,
            b.posting_date,
            b.payment_type,
            a.total_amount,
            a.paid_amount,
            a.sale_balance,
            a.payment_amount,
            a.write_off_amount,
            a.balance,
            a.note,
            b.creation,
            b.created_by
        from `tabSale Payment Invoices` a 
        join `tabSale Payment` b on b.name = a.parent
        where
            b.docstatus = 1 and 
            a.sale =%(sale_name)s
    """
    data = frappe.db.sql(sql,{"sale_name":sale_name},as_dict = 1)
    return data

