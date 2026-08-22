// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Tube Ice Produce", {
// 	refresh(frm) {

// 	},
// });

// Copyright (c) 2025, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tube Ice Produce", {
    refresh(frm) {

       var produce_table = $('[data-fieldname="tube_ice_produce_quantity"]');
        produce_table.find('.grid-footer').remove();
        frm.set_intro();

         if (frm.doc.docstatus != 1 && frm.doc.posting_date) {
            // Convert to Date objects
            let postingDate = frappe.datetime.str_to_obj(frm.doc.posting_date);
            let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());

            // calculate difference in days (postingDate - today)
            let diff = frappe.datetime.get_diff(postingDate, today); // postingDate - today

            // Show intro if posting date is more than 1 day ahead or behind today
            if (diff > 1 || diff < 0) {
                frm.set_intro(`
                    <div style="padding:10px; border:1px solid red; background:#ffe6e6; color:#b30000; border-radius:5px;">
                        ⚠️ Warning: Please double-check the Posting Date before submitting this form!
                    </div>
                `, "red");
                 setTimeout(() => {
                let $closeBtn = frm.$wrapper.find(".close-message");
                $closeBtn.css({
                    "margin-right": "15px",   // adjust position
                    "margin-top": "10px",
                    "cursor": "pointer"
                });
            }, 1);
            }
        }
    },

    onload(frm) {
        getMachineNames(frm)
    },


});

function getMachineNames(frm) {
    if(frm.is_new()){
    frm.clear_table("tube_ice_produce_quantity");

    frm.call("get_tube_machine").then(result=>{
        console.log(result.message)
       result.message.forEach(row => {
            let child_row = frm.add_child("tube_ice_produce_quantity");
            child_row.machine_name = row.name;
            child_row.product_code = row.product_code;
            child_row.start_meter_number = row.start_meter_number;
            child_row.allow_edit_start_meter_number = row.allow_edit_start_meter_number;


        });
         frm.refresh_field("tube_ice_produce_quantity");
    })


    }
}
