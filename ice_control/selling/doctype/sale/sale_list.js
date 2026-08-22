frappe.listview_settings['Sale'] = {
    add_fields: ['balance', 'total_amount','total_paid','is_foc','customer_name','grand_total'],
    hide_name_column: true, // hide the last column which shows the `name`
    // set this to true to apply indicator function on draft documents too
    has_indicator_for_draft: false,

    get_indicator(doc) {
        if(doc.status=="Paid"){ 
            return [__("Paid"), "green"];
        }else if(doc.status=="Partially Paid"){
            return [__("Partially Paid"), "yellow"];
        }else{
            if(doc.status=="Deleted"){
                return [__("Deleted"), "red"];
            }
            else{
                return [__("Unpaid"), "red"];
            }
        }
    },
}