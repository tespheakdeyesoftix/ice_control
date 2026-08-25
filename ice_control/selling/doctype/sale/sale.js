// Copyright (c) 2025, Tes Pheakdey and contributors
// For license information, please see license.txt




frappe.ui.form.on("Sale", {
    setup(frm) {
        frm.set_query("product_code", "sale_products", function (doc, cdt, cdn) {
            return {
                query: "ice_control.api.api.get_products_by_outlet",
                filters: {
                    outlet: doc.outlet,
                    product_codes: doc.sale_products.filter(d => d.product_code).map(x => x.product_code)
                }
            };
        });
    },
    onload(frm) {
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
            if (frm.doc.sale_status != 'Draft') {
                if (frm.doc.enable_edit_mode == 0) {
                    frm.fields.forEach(function (field) {
                        if (field.df.bold == 0) {
                            frm.set_df_property(field.df.fieldname, 'read_only', 1);
                        }

                    });
                }

                if (frm.doc.sale_status === "Closed" || frm.doc.sale_status === "Deleted") {
                    frm.set_read_only();
                }

            }




            // Refresh the fields to apply the changes
            frm.refresh_fields();





        }


        updateSummary(frm);

        addCustomButton(frm)

        renderPaymentHistory(frm)

        renderSplitBillList(frm)



    },
    outlet(frm) {
        if (frm.doc.sale_products?.filter(r => r.product_code).length > 0) {
            frappe.msgprint("អ្នកបានប្តូរទីតាំងលក់ សូមពិនិត្យនឹងជ្រើសរើសទំនិញអោយបានត្រឹមត្រូវ។")
        }

    },

    customer(frm) {
        frm.call("change_customer").then(r => {
            updateSummary(frm);
        })

    }
});




function setIntro(frm) {
    if (!frm.is_new()) {
        if (frm.doc.parent_bill_number) {
            frm.set_intro(__('This bill is split from bill number:') + " " + `<a href='/desk/sale/${frm.doc.parent_bill_number}'>${frm.doc.parent_bill_number}</a>`);


        }
        if (frm.doc.balance > 0 && frm.doc.sale_status == "Closed") {
            const posting_date = frappe.datetime.str_to_obj(frm.doc.posting_date);
            const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());

            const diff_days = frappe.datetime.get_day_diff(today, posting_date);

            if (diff_days > 7 && diff_days < 30) {

                frm.set_intro(__('This bill is credit over {0} days', [diff_days]), "orange");

            } else if (diff_days > 30) {
                frm.set_intro(__('This bill is credit over {0} days', [diff_days]), "red");
            }
        }


    }
}

function setIndicator(frm) {
    if (!frm.is_new()) {
        frm.dashboard.add_indicator(
            __("Total Quantity: {0}", [frappe.format(frm.doc.total_quantity, { "fieldtype": "Float" })]),
            "blue"
        );

        frm.dashboard.add_indicator(
            __("Total Amount: {0}", [fmt_money(frm.doc.total_amount)]),
            "blue"
        );
        frm.dashboard.add_indicator(
            __("Total Payment: {0}", [fmt_money(frm.doc.total_payment)]),
            "green",

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
    sale_products_remove(frm) {

    },
    quantity(frm, cdt, cdn) {
        saleProductChange(frm, cdt, cdn);
    },
    price(frm, cdt, cdn) {
        saleProductChange(frm, cdt, cdn);
    },
    free_quantity(frm, cdt, cdn) {
        saleProductChange(frm, cdt, cdn);
    },
    return_quantity(frm, cdt, cdn) {
        saleProductChange(frm, cdt, cdn);
    },

    product_code(frm, cdt, cdn) {
        get_customer_price(frm, cdt, cdn)

    },
    unit(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        get_customer_price(frm, cdt, cdn)
    }
});

async function get_multiplier(frm, product){
    frappe.call({
      method: 'ice_control.api.inventory.get_purchase_cost',
      args: {
         "param":{
            "doc": frm.doc,
            "product": product
         }
      },
      callback: (r) => {
        frappe.model.set_value(product.doctype, product.name, "multiplier", (r.message.multiplier || 0));
      }
      })
}

function saleProductChange(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    frm.call("sale_product_update", {
        row: row
    }).then(r => {
        updateSummary(frm);
    })
}

function get_customer_price(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    if (row.product_code && frm.doc.customer) {
        frm.call("sale_product_update", {
            row: row,
            check_customer_price: true

        }).then(r => {
            setTimeout(() => {
                get_multiplier(frm,row);
            }, 250);
            updateSummary(frm);
        })
    }


}


function updateSummary(frm) {
    frappe.call({
        method: 'ice_control.selling.doctype.sale.sale.generate_product_qty',
        args: {
            sale_products: frm.doc.sale_products
        },
        callback: (r) => {
            if ((frm.doc.sale_products ?? []).length > 0) {
                const html = frappe.render_template("sale_summary", { product_qty: JSON.parse(r.message), sale: frm.doc });
                $(frm.fields_dict['sale_summary'].wrapper).html(html);

            } else {
                $(frm.fields_dict['sale_summary'].wrapper).empty();
            }
            frm.refresh_field('sale_summary');
        }
    })
}


function addCustomButton(frm) {

    if (frm.doc.balance > 0 && frm.doc.sale_status == "Closed") {
        frm.add_custom_button(__("Add Payment"), function () {
            frappe.route_options = { customer: frm.doc.customer, customer_name: frm.doc.customer_name, sale: frm.doc.name, outlet: frm.doc.outlet };
            frappe.set_route('Form', 'Sale Payment', 'new');

        });
    }

    if (frm.doc.sale_status == "Draft") {

        frm.add_custom_button(__("បិទការលក់"), async function () {

            // validate customer
            if (!frm.doc.customer) {

                frappe.throw({
                    title: "Warning",
                    message: "សូមជ្រើសរើសអិតិថិជន",
                    indicator: "orange"
                });
            }

            frappe.confirm(
                "តើអ្នកពិតជាចង់បិទការលក់បុងនេះមែនទេ?",
                async () => {
                    await frm.set_value("sale_status", "Closed");

                    await frm.save();


                },

            );

        }).addClass("btn-danger");


    }

    // delete button
    if (!frm.is_new() && frm.doc.sale_status!="Deleted") {

        frm.page.set_secondary_action("លុបបុង", () => {
            frappe.warn("លុបបុង","តើអ្នកពិតជាចង់លុបបុងនេះមែនទេ?", () => {
                frm.call("delete_sale").then(async x=>{
                      await frm.reload_doc();
                })

            },
          
        'លុបបុង',
        true 
    );
           
        }).removeClass("btn-secondary")
            .addClass("btn-danger");



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

async function renderSplitBillList(frm) {
    let data = [];

    if (!frm.is_new() && frm.doc.sale_status =='Closed') {
        data = await frappe.db.get_list("Sale", {
            fields: [
                "name",
                "posting_date",
                "customer",
                "customer_name",
                "total_quantity",
                "total_amount",
                "sale_status"
            ],
            filters: {
                parent_bill_number: frm.doc.name
            },
            order_by: "creation desc",
            limit_page_length: 0
        });
    }

    const wrapper = $(frm.fields_dict["html_sale_split_bill_list"].wrapper);
    const html = frappe.render_template("split_bill_list", { data });

    wrapper.html(html);
    wrapper.find(".btn-add-split-bill").on("click", () => {
        openSplitBillDialog();
    });
}

function openSplitBillDialog() {
    const dialog = new frappe.ui.Dialog({
        title: __("Split Bill"),
        fields: []
    });

    dialog.show();
}
