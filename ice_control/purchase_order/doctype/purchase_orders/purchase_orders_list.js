frappe.listview_settings['Purchase Orders'] = {
    get_indicator(doc) {
       if(doc.status=="Paid"){ 
              return [__("Paid"), "green"];
          }else if(doc.status=="Partially Paid"){
              return [__("Partially Paid"), "orange"];
          }else if(doc.status=="Unpaid"){
              return [__("Unpaid"), "red"];
          }
          else if(doc.status=="Draft"){
              return [__("Draft"), "red"];
          }
          else if(doc.status=="Cancelled"){
              return [__("Cancelled"), "red"];
          }
    },
    refresh: function(listview) {

    },
}

