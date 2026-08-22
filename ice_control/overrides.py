# my_app/overrides.py
import frappe
import frappe.boot
import json
from frappe.utils.caching import redis_cache
from frappe import _

_original_get_sidebar_items = frappe.boot.get_sidebar_items

 
    

def custom_get_sidebar_items(*args, **kwargs):
    
    
     
    sidebar_items = _original_get_sidebar_items()
    
  
    
    user_outlet = list(set(get_user_permission_outlet()) & set(get_user_outlets(frappe.session.user)))
    for k in sidebar_items.keys():
        if sidebar_items[k].get("app") == "ice_control":
            if k=="reports":
                
                sidebar_items[k]["items"] =  get_sidebar_items(
                                                items = sidebar_items[k]["items"],
                                                outlets = user_outlet
                                            ) +  get_report_sidebar_items()

            else:
                sidebar_items[k]["items"] = get_sidebar_items(
                    items = sidebar_items[k]["items"],
                    outlets = user_outlet
                )

    return sidebar_items

# this is special for override method

frappe.boot.get_sidebar_items = custom_get_sidebar_items


def get_sidebar_items(items:list[dict], outlets:list[str])->list[dict]:
    _items = []
    def has_route_options(item:dict)->bool:
        if (item.get("route_options") or "")=="":
            return True

        _route_options = json.loads(item.get("route_options"))
        # check if route option has key outlet then check outlet with user allow outlet
        if "outlet" in _route_options:
            if _route_options.get("outlet") in outlets:
                return True

        return False

    def has_role(item:dict)->bool:
        if (item.get("filters") or "") == "":
            return True
        _filters = json.loads(item.get("filters"))
        if "roles" in _filters:
            return   bool(set(_filters.get("roles")) & set(get_roles(frappe.session.user)))
        return False


            


    for s in items:
        if has_route_options(item=s) and has_role(item = s):
            _items.append(s)

    return _items or []
 
def get_report_sidebar_items()->list[dict]:
    
    all_reports = get_report_from_db()
    parent_reports = [x for x in all_reports if x.get("is_group") == 1]
    report_roles = get_all_report_roles()
    user_roles = get_roles(frappe.session.user)
    
    def is_report_has_permission(report_name:str)->bool:
        if report_name not in report_roles.keys():
            return True
        return set(report_roles.get(report_name)) & set(user_roles)
         

    
    result = []
    for p in parent_reports:
        if is_report_has_permission(p.get("name")):
            result.append(
                {
                    "label": _(p.get("name")),
                    "link_to": None,
                    "type": "Section Break",
                    "collapsible": 1,
                    "indent": 1,
                    "keep_closed": 1,
                    "url": None,
                    "show_arrow": 0,
                    "filters": None,
                    "route_options": None,
                    "tab": None,
                    "open_in_new_tab": 1,
                    "default_workspace": 0
                    }
            )
        
            # child item
            
            for c in [x for x in all_reports if x.get("parent_system_report") == p.get("name") and x.get("report_url")]:
                if is_report_has_permission(c.get("name")):
                    result.append(
                        {
                            "label": _(c.get("name")),
                            "link_to": "server-report-viewer",
                            "link_type": "Page",
                            "type": "Link",
                            "icon": "panel-top",
                            "child": 1,
                            "collapsible": 1,
                            "indent": 0,
                            "keep_closed": 0,
                            "url": None,
                            "show_arrow": 0,
                            "filters": None,
                            "route_options": json.dumps({"report_url":c.get("report_url")}),
                            "tab": None,
                            "open_in_new_tab": 1,
                            "default_workspace": 0
                            }
                    )



    return result
    


@redis_cache(ttl=300)
def get_report_from_db():
    sql = """
        select 
            name,
            is_group,
            report_url,
            parent_system_report
        from `tabSystem Report`
        where 
            name <> 'All Reports' and 
            is_backend_report = 1
        order by
            sort_order,idx
    """
    return frappe.db.sql(sql,as_dict=1)
    

def get_all_report_roles():
    sql ="""
        select distinct parent, role from `tabHas Role` where
        parenttype = 'System Report'
        
    """
    data  =  frappe.db.sql(sql,as_dict=1)
    result = {}
    for item in data:
        result.setdefault(item["parent"], []).append(item["role"])
    return result


@redis_cache(ttl=300)
def get_roles(user):
    return frappe.get_roles(user)

@redis_cache(ttl=120)
def get_user_outlets(user):
    sql = """
        select 
            a.outlet
        from `tabOutlet Child` a
        join `tabEmployee` b on b.name = a.parent
        where
            b.user_id = %(user_id)s
    """
    data =  frappe.db.sql(sql,{"user_id": user},as_dict =1)
    if data:
        return [x.get("outlet") for x in data]
    return [""]

def get_user_permission_outlet():
    return frappe.db.get_list("Outlet",pluck="name")