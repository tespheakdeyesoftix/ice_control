// Copyright (c) 2025, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sale", {
    onload(frm){
        if (!frm.is_new()) {
            frm.call("update_sale_information")
        }
    },
    refresh(frm) {
        frm.dashboard.clear_headline();
        setIntro(frm);
        setIndicator(frm)


        if (!frm.is_new()) {




            // make all control read only
            if(frm.doc.sale_status !='Draft' ){
                if (frm.doc.enable_edit_mode==0){
                     frm.fields.forEach(function(field) {
                        if(field.df.bold==0){
                            frm.set_df_property(field.df.fieldname, 'read_only', 1);
                        }

                    });
                }



        }

            // Refresh the fields to apply the changes
            frm.refresh_fields();





        }


        updateSummary(frm);

        addCustomButton(frm)

        renderPaymentHistory(frm)
	},
    outlet(frm) {
        get_default_accounts(frm);
        // get_products_default_account(frm)
    },

    customer(frm) {
        frappe.call({
            method: 'ice_control.customer_management.doctype.customer.customer.get_customer_product_price',
            args: {
               customer: frm.doc.customer,
               products: frm.doc.sale_products
            },
            callback: (r) => {
                frm.clear_table("sale_products");
                r.message.forEach((r => {
                    p = frm.add_child("sale_products");
                    p.product_code = r.product_code;
                    p.product_name = r.product_name;
                    p.product_category = r.product_category;
                    p.revenue_group = r.revenue_group;
                    p.free_quantity = r.free_quantity;
                    p.total_sale_quantity = r.quantity - r.free_quantity;
                    p.quantity = r.quantity;
                    p.price = r.price;
                    p.sub_total = r.sub_total;
                    p.total_amount = r.total_amount;
                    p.allow_sum_qty = r.allow_sum_qty;
                    p.note = r.note;
                    p.unit = r.unit,
                    p.multiplier = r.multiplier
                }))
                frm.refresh_field("sale_products");
                update_sale_total(frm)
            }
        })
    }
});

function setIntro(frm){
    if(!frm.is_new()){
        if (frm.doc.parent_bill_number){
            frm.set_intro(__('This bill is split from bill number:') + " " + `<a href='/desk/sale/${frm.doc.parent_bill_number}'>${frm.doc.parent_bill_number}</a>`);


        }
        if (frm.doc.balance>0){
             const posting_date = frappe.datetime.str_to_obj(frm.doc.posting_date);
            const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());

            const diff_days = frappe.datetime.get_day_diff(today, posting_date);

            if (diff_days>7 && diff_days<30){

                frm.set_intro(__('This bill is credit over {0} days', [diff_days]),"orange");

            }else if(diff_days>30){
                 frm.set_intro( __('This bill is credit over {0} days',[diff_days]),"red");
            }
        }


    }
}

function setIndicator(frm){
    if(!frm.is_new()){
         frm.dashboard.add_indicator(
                __("Total Quantity: {0}", [frappe.format(frm.doc.total_quantity,{"fieldtype":"Float"})]),
                "blue"
            );

            frm.dashboard.add_indicator(
                __("Total Amount: {0}", [fmt_money(frm.doc.total_amount)]),
                "blue"
            );
            frm.dashboard.add_indicator(
                __("Total Payment: {0}", [fmt_money(frm.doc.total_payment)]),
                "green"  ,

            );
            frm.dashboard.add_indicator(
                __("Write Off Amount: {0}", [fmt_money(frm.doc.total_write_off)]),
                "red"
            );

            frm.dashboard.add_indicator(
                __("Balance: {0}", [fmt_money(frm.doc.balance)]),
                "blue"
            );

    }
}

frappe.ui.form.on("Sale Products", {
    sale_products_remove(frm){
        update_sale_total(frm)
    },
    quantity(frm,cdt,cdn) {
        cal_total_product(frm,cdt,cdn);
    },
    price(frm,cdt,cdn) {
        cal_total_product(frm,cdt,cdn);
    },
    free_quantity(frm,cdt,cdn) {
        cal_total_product(frm,cdt,cdn);
    },
    product_code(frm,cdt,cdn) {
        get_customer_price(frm,cdt,cdn)
        // get_products_default_account(frm)
    },
    unit(frm,cdt,cdn) {
        get_customer_price(frm,cdt,cdn)
    }
});




function get_customer_price(frm,cdt,cdn){
    row = locals[cdt][cdn];
    frappe.call({
        method: 'ice_control.customer_management.doctype.customer.customer.get_customer_product_price',
        args: {
            customer: frm.doc.customer,
            product_code: row.product_code,
            unit: row.unit
        },
        callback: (r) => {
            if(r.message){
                frappe.model.set_value(cdt, cdn, "price", r.message.price);
                frappe.model.set_value(cdt, cdn, "free_quantity", r.message.free_quantity);
                frappe.model.set_value(cdt, cdn, "multiplier", r.message.multiplier);
                cal_total_product(frm,cdt,cdn);
            }
        }
    })
}

function updateSummary(frm) {
    frappe.call({
        method: 'ice_control.selling.doctype.sale.sale.generate_product_qty',
        args: {
            sale_products: frm.doc.sale_products
        },
        callback: (r) => {
            if((frm.doc.sale_products??[]).length > 0){
                const html = frappe.render_template("sale_summary", {product_qty: JSON.parse(r.message),sale: frm.doc});
                $(frm.fields_dict['sale_summary'].wrapper).html(html);

            }else{
                $(frm.fields_dict['sale_summary'].wrapper).empty();
            }
            frm.refresh_field('sale_summary');
        }
    })
}

function cal_total_product(frm,cdt,cdn) {
    let row = locals[cdt][cdn];
    sale_quantity = row.quantity - row.free_quantity;
    let total_amount = sale_quantity * row.price * row.multiplier;
    frappe.model.set_value(cdt, cdn, "total_sale_quantity", sale_quantity);
    frappe.model.set_value(cdt, cdn, "sub_total", row.quantity * row.price * row.multiplier);
    frappe.model.set_value(cdt, cdn, "total_amount", total_amount);
    update_sale_total(frm);
}

function update_sale_total(frm) {
    let total_quantity = 0;
    let total_free_quantity = 0;
    let total_total_sale_quantity = 0;
    let total_sale_amount = 0;
    frm.doc.sale_products.forEach(a => {
        if(a.allow_sum_qty == 1){
            total_quantity += a.quantity;
            total_free_quantity += a.free_quantity;
            total_total_sale_quantity += a.total_sale_quantity;
            total_sale_amount += a.total_amount;
        }
    });
    frm.set_value("total_quantity", total_quantity);
    frm.set_value("total_free", total_free_quantity);
    frm.set_value("total_sale_quantity", total_total_sale_quantity);
    frm.set_value("total_amount", total_sale_amount);
    frm.set_value("balance", total_sale_amount);
    updateSummary(frm);
}


function addCustomButton(frm){

    if(frm.doc.balance>0){
        frm.add_custom_button(__("Add Payment"), function() {
        frappe.route_options = { customer: frm.doc.customer,customer_name:frm.doc.customer_name, sale:frm.doc.name,outlet:frm.doc.outlet };
        frappe.set_route('Form', 'Sale Payment', 'new');

    });

    }


    // // add menu from report
    // frappe.db.get_list("System Report",{fields:["name","report_title","report_url"],filters:[["is_doctype_report","=",1],["doctype_name","=",frm.doctype]]}).then(result=>{
    //     if(result){
    //         result.forEach(r=>{

    //              frm.add_custom_button(__(r.report_title), function() {
    //                     printDoc(frm,r.name)

    // }, __('View Reports'));
    //         })
    //     }

    // })

}

function renderPaymentHistory(frm) {

    frm.call("get_payment_history").then(result => {

        const html = frappe.render_template("payment_history", {
            data: result.message || []
        });

        $(frm.fields_dict["html_payment_history"].wrapper).html(html);
    });
}
