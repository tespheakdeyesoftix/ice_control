const payment_status_color =  {"Unpaid":"red","Paid":"green","Partially Paid":"orange"}
frappe.listview_settings['Expense'] = {
    // add fields to fetch
    add_fields: ['status'],
    
  
    get_indicator(doc) {
        // customize indicator color
        if (doc.docstatus==0) {
            return [__("Draft"), "orange"];
        } 
        else if(doc.docstatus==1){
            
            return [__(doc.status), payment_status_color[doc.status]];
        }else{
            return [__("Cancelled"), "red"];
        }
    },
   
}
