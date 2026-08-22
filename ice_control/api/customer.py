import frappe
from frappe.utils import getdate, today,add_to_date
from frappe.utils.caching import redis_cache


@redis_cache(ttl=86400)
def get_all_customer_product_prices()->list[dict]:
    sql= """
        select  
            a.product_code,
            a.unit,
            max(a.price) as price 
        from `tabCustomer Product Price`  a
        join `tabCustomer` c on c.name = a.parent

        where 
            coalesce(c.enabled,0) = 1 
        group by a.product_code, a.unit


    """
    return frappe.db.sql(sql,as_dict=1)


@redis_cache(ttl=86400)
def get_customer_product_prices(customer:str)->list[dict]:
    sql= """
        select  product_code,unit,max(price) as price 
        from `tabCustomer Product Price`
        where 
            parent = %(customer)s 
        group by product_code, unit


    """
    return frappe.db.sql(sql,{"customer":customer},as_dict=1)


@frappe.whitelist()
def get_customer_dashboard_data(customer: str ="", start_date:str = None, end_date:str=None, outlet:str="")->dict:
 

    if not start_date:
        start_date =  getdate(today()).replace(day=1)
    if not end_date:
        end_date = today()

    return {
        "account_recivable": {},
        "ar_aging":{}
    }
  


@frappe.whitelist()
def get_sale_vs_payment_chart_data(series_type="MTD", customer="",outlet=""):

    start_date = None
    end_date= None
    data = []
    if series_type == "MTD":
       
        start_date =  getdate(today()).replace(day=1)
        end_date = add_to_date(start_date, months=1)
        end_date = add_to_date(end_date, days=-1)
        sql = """
                with a as (
                    select date from `tabDates` where date between %(start_date)s and %(end_date)s
                ),b as (
                    select 
                        s.posting_date,
                        sum(s.total_amount) as amount 
                    from `tabSale` s
                    where 
                        s.sale_status = 'Closed'  and 
                        (%(outlet)s = '' or s.outlet=%(outlet)s) and 
                        (%(customer)s = '' or s.customer = %(customer)s) and 
                        s.posting_date between %(start_date)s and %(end_date)s

                    group by
                        s.posting_date
                ),
                c as (
                    select 
                        s.posting_date,
                        sum(s.paid_amount) as payment_amount ,
                        sum(s.write_off_amount) as write_off_amount 
                    from `tabSale Payment Invoices` s
                    where 
                        s.docstatus = 1 and  
                        (%(outlet)s = '' or s.outlet=%(outlet)s) and 
                        (%(customer)s = '' or s.customer = %(customer)s) and 
                        s.posting_date between %(start_date)s and %(end_date)s

                    group by
                        s.posting_date
                )
                select 
                    day(a.date) as date,
                    coalesce(b.amount,0) as sale_amount,
                    coalesce(c.payment_amount,0) as payment_amount,
                    coalesce(c.write_off_amount,0) as write_off_amount
                from a 
                left join b on b.posting_date = a.date
                left join c on b.posting_date = a.date
                order by date
                """
        data =  frappe.db.sql(sql,{"start_date":start_date,"end_date":end_date,"outlet":outlet,"customer":customer},as_dict = 1)
        
        
    
    else:
        start_date =  getdate(today()).replace(day=1,month=1)
        end_date = add_to_date(start_date, years=1)
        end_date = add_to_date(end_date, days=-1)
        sql = """
                with a as (
                    select DATE_FORMAT(date, '%%b') AS month_text, month(date) as `month`, year(date) as `year` from `tabDates` where date between %(start_date)s and %(end_date)s group by `month`,`year`
                ),b as (
                    select 
                        month(s.posting_date) as `month`,
                        year(s.posting_date) as `year`,
                        sum(s.total_amount) as amount 
                    from `tabSale` s
                    where 
                        s.sale_status = 'Closed'  and 
                        (%(outlet)s = '' or s.outlet=%(outlet)s) and 
                        (%(customer)s = '' or s.customer = %(customer)s) and 
                        s.posting_date between %(start_date)s and %(end_date)s

                    group by
                        `month`,
                        `year`
                ),
                c as (
                    select 
                        month(s.posting_date) as month,
                        year(s.posting_date) as year,
                        sum(s.paid_amount) as payment_amount ,
                        sum(s.write_off_amount) as write_off_amount 
                    from `tabSale Payment Invoices` s
                    where 
                        s.docstatus = 1 and  
                        (%(outlet)s = '' or s.outlet=%(outlet)s) and 
                        (%(customer)s = '' or s.customer = %(customer)s) and 
                        s.posting_date between %(start_date)s and %(end_date)s

                    group by
                        `month`,
                        `year`
                )
                select 
                    a.month_text,
                    coalesce(b.amount,0) as sale_amount,
                    coalesce(c.payment_amount,0) as payment_amount,
                    coalesce(c.write_off_amount,0) as write_off_amount
                from a 
                left join b on b.`month` = a.`month` and b.`year` = a.`year`
                left join c on c.`month` = a.`month` and c.`year` = a.`year`
                 
                """
        data =  frappe.db.sql(sql,{"start_date":start_date,"end_date":end_date,"outlet":outlet,"customer":customer},as_dict = 1)
        
    
    
    return data

@frappe.whitelist()
def get_total_order_chart_data(series_type="MTD", customer="",outlet=""):
    start_date = None
    end_date= None
    data = []
    if series_type == "MTD":
        start_date =  getdate(today()).replace(day=1)
        end_date = add_to_date(start_date, months=1)
        end_date = add_to_date(end_date, days=-1)
        sql = """
                with a as (
                    select date from `tabDates` where date between %(start_date)s and %(end_date)s
                ),b as (
                    select 
                        s.posting_date,
                        count(*) as total_order
                    from `tabSale` s
                    where 
                        s.sale_status = 'Closed'  and 
                        (%(outlet)s = '' or s.outlet=%(outlet)s) and 
                        (%(customer)s = '' or s.customer = %(customer)s) and 
                        s.posting_date between %(start_date)s and %(end_date)s

                    group by
                        s.posting_date
                )
                select 
                    day(a.date) as date,
                    coalesce(b.total_order,0) as total_order
                from a 
                left join b on b.posting_date = a.date
                 
                """
        data =  frappe.db.sql(sql,{"start_date":start_date,"end_date":end_date,"outlet":outlet,"customer":customer},as_dict = 1)
        
        
    
    else:
        start_date =  getdate(today()).replace(day=1,month=1)
        end_date = add_to_date(start_date, years=1)
        end_date = add_to_date(end_date, days=-1)
        sql = """
                with a as (
                    select DATE_FORMAT(date, '%%b') AS month_text, month(date) as `month`, year(date) as `year` from `tabDates` where date between %(start_date)s and %(end_date)s group by `month`,`year`
                ),b as (
                    select 
                        month(s.posting_date) as `month`,
                        year(s.posting_date) as `year`,
                        count(*) as total_order
                    from `tabSale` s
                    where 
                        s.sale_status = 'Closed'  and 
                        (%(outlet)s = '' or s.outlet=%(outlet)s) and 
                        (%(customer)s = '' or s.customer = %(customer)s) and 
                        s.posting_date between %(start_date)s and %(end_date)s

                    group by
                        `month`,
                        `year`
                )
                select 
                    a.month_text,
                    coalesce(b.total_order,0) as total_order
                    
                from a 
                left join b on b.`month` = a.`month` and b.`year` = a.`year`
                 
                 
                """
        data =  frappe.db.sql(sql,{"start_date":start_date,"end_date":end_date,"outlet":outlet,"customer":customer},as_dict = 1)
        
    
    
    return data

@frappe.whitelist()
def get_total_order_quantity_chart_data(series_type="MTD", customer="",outlet=""):
    outlets = []
    if outlet:
        outlets = [outlet]
    else:
        outlets = frappe.get_list("Outlet",pluck="name")
        
    start_date = None
    end_date= None
    data = []
    outlet_fields = ", ".join([f"0 as `{f}`" for f in outlets])
    if series_type == "MTD":
        start_date =  getdate(today()).replace(day=1)
        end_date = add_to_date(start_date, months=1)
        end_date = add_to_date(end_date, days=-1)
        
        sql = """
                    select day(date) as date,{0} from `tabDates` where date between %(start_date)s and %(end_date)s 
                
        """.format(outlet_fields)
        data =  frappe.db.sql(sql,{"start_date":start_date,"end_date":end_date},as_dict = 1)

        # quantity data
        sql = """
            select 
                s.outlet,
                day(s.posting_date) as date,
                sum(s.total_sale_quantity) as quantity 
            from  `tabSale`  s
            where
                s.posting_date between %(start_date)s and %(end_date)s  and 
                s.outlet in %(outlets)s and 
                (%(customer)s = '' or  s.customer = %(customer)s )
            group by 
                s.outlet,
                s.posting_date
        """
        quantity_data = frappe.db.sql(sql,{"start_date":start_date,"end_date":end_date,"customer":customer,"outlets":outlets},as_dict =1)
        for q in quantity_data:
            row = next((x for x in data if  x.get("date")  ==  q.get("date")), None)
            if row:
                row[q.get("outlet")] = q.get("quantity")
        
       
        
    
    else:
        start_date =  getdate(today()).replace(day=1,month=1)
        end_date = add_to_date(start_date, years=1)
        end_date = add_to_date(end_date, days=-1)
        sql = """
                    select DATE_FORMAT(date, '%%b') AS date, month(date) as `month`,year(date) as `year`,{0} from `tabDates` 
                    where date between %(start_date)s and %(end_date)s  
                    group by
                        `month`,
                        `year`
                
        """.format(outlet_fields)
        data =  frappe.db.sql(sql,{"start_date":start_date,"end_date":end_date},as_dict = 1)
        # quantity data
        sql = """
            select 
                s.outlet,
                month(s.posting_date) as `month`,
                year(s.posting_date) as `year`,
                sum(s.total_sale_quantity) as quantity 
            from  `tabSale` s
            where
                s.posting_date between %(start_date)s and %(end_date)s  and 
                s.outlet in %(outlets)s and 
                (%(customer)s = '' or  s.customer = %(customer)s )
            group by 
                s.outlet,
                `month`,
                `year`
        """
        quantity_data = frappe.db.sql(sql,{"start_date":start_date,"end_date":end_date,"customer":customer,"outlets":outlets},as_dict =1)
        for q in quantity_data:
            row = next((x for x in data if  x.get("month")  ==  q.get("month") and x.get("year")  ==  q.get("year")), None)
            if row:
                row[q.get("outlet")] = q.get("quantity")
    
    return {"chart_data":data,"chart_data_fields":outlets}



    
@frappe.whitelist()
def get_revenue_summary(start_date=None,end_date=None, customer="",outlet="",group_by="product_category"):
    outlets = []
    if outlet:
        outlets = [outlet]
    else:
        outlets = frappe.get_list("Outlet",pluck="name")
        
    
    data = []
    
    if not start_date:
        start_date =  getdate(today()).replace(day=1)
    if not end_date:
        end_date = today()
    sql = """
        select 
            sp.{0} as label,
            sum(sp.total_amount) as value 
        from `tabSale Products` sp join `tabSale` s on s.name = sp.parent
        where
            s.sale_status = 'Closed' and 
            s.outlet in %(outlets)s and
            (%(customer)s = '' or s.customer = %(customer)s ) and  
            s.posting_date between %(start_date)s and %(end_date)s
        group by
         label
        """.format(
            group_by
        )
    data = frappe.db.sql (sql,{"customer":customer,"outlets":outlets,"start_date":start_date,"end_date":end_date},as_dict = 1)
    return data
