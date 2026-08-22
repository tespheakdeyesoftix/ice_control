
def has_app_permission():
    return True

def module_def_has_permission(user:str):
    if not user:
        user = frappe.session.user
    if user=="Administrator":
        return None # not apply user permission
        
    query = f"""(`tabModule Def`.`name` not in ('Website','Workflow','Email','Geo','Integrations','Printing','Contacts','Automation'))"""
    
    return query

def role_has_permission(user:str):
    if not user:
        user = frappe.session.user
    if user=="Administrator":
        return None # not apply user permission

    query = f"""(`tabRole`.`name` not in ('Knowledge Base Editor','Knowledge Base Contributor','Newsletter Manager','Marketing Manager','Translator','Inbox User','Script Manager','Report Manager','Workspace Manager','Dashboard Manager','Website Manager','Administrator','System Manager'))"""
    
    return query

