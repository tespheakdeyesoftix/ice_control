import frappe
from ice_control.api import sale as sale_api
from datetime import date, datetime

@frappe.whitelist(methods=["GET","POST"])
def get_home_page_data( posting_date:str|date = None) ->dict:
    result  = {
        "daily_sale_summary":[]
    }
    if not posting_date:
        posting_date = frappe.utils.today()

    result["daily_sale_summary"].append(  {
        "outlet":"ទឹកកកដើម",
        **sale_api.get_daily_sale_summary(
            outlet = "ទឹកកកដើម",
            posting_date = posting_date
        )
    })
    # tube ice
    result["daily_sale_summary"].append({
            "outlet":"ទឹកកកអនាម័យ",
            **sale_api.get_daily_sale_summary(
                outlet = "ទឹកកកអនាម័យ",
                posting_date = posting_date
            )
        }
    )   

    return result

