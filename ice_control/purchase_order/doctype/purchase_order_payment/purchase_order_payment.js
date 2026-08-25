// Copyright (c) 2025, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Order Payment", {
     onload(frm) {         
        frm.set_query("purchase_order", "purchase_orders", function (doc, cdt, cdn) {
            let purchase_order_filter = {
                    "party": doc.party || 'Not Set',
                    "outlet": doc.outlet || 'Not Set',
                    "balance": [">", 0],
                    "docstatus": 1
                };          
            if (doc.purchase_order){
                purchase_order_filter.name = doc.purchase_order
            }
            return {
                "filters": purchase_order_filter,
            };
        });
    },
    posting_date(frm){
        update_allocated_payment_date(frm)
    },
	refresh(frm) {
    
	},
    party_type(frm){
        frm.set_value("party", "");
        frm.refresh_field("party")
    },
    async party(frm) { 
        await get_unpaid_purchase_orders(frm)
        if ((frm.doc.input_amount || 0) > 0) {
            update_allocated_amount(frm)
        } else {
            calculate_totals(frm)
        }  
    },
    async outlet(frm) {
        await get_unpaid_purchase_orders(frm)
        if ((frm.doc.input_amount || 0) > 0) {
            update_allocated_amount(frm)
        } else {
            calculate_totals(frm)
        }  
    },
    payment_type(frm) {
        frappe.call({
        method: 'ice_control.api.api.get_exchange_rate',
        args: {
            "currency": frm.doc.currency
        },
        callback: (r) => {
            frm.set_value("exchange_rate", r.message);
            if ((frm.doc.input_amount || 0) > 0) {
            let exchange_rate = (frm.doc.exchange_rate || 1);
            let input_amount = (frm.doc.payment_amount || 0)*exchange_rate;
            frm.set_value("input_amount",input_amount)
            frm.set_value("payment_amount",input_amount)
            frm.doc.purchase_orders.forEach(r => {
                r.exchange_rate = frm.doc.exchange_rate,
                r.input_write_off_amount = r.write_off_amount*r.exchange_rate
            })
            update_allocated_amount(frm)
        }
        }
        })
    },
    async get_invoices(frm) {
        if (!frm.doc.outlet) {
            frappe.throw(__("Please select outlet"))
            return
        }
        if (!frm.doc.party) {
            frappe.throw(__("Please select Party"))
            return
        }

        if (!frm.doc.start_date) {
            frappe.throw(__("Please select start date"))
            return
        }
        if (!frm.doc.end_date) {
            frappe.throw(__("Please select end date"))
            return
        }
        await get_unpaid_purchase_orders(frm)
        calculate_totals(frm)
    },

    input_amount: function (frm) {
        if (!frm.doc.payment_type) {
            frappe.throw(__("Please select payment type"))
        }
        const payment_amount = frm.doc.input_amount / (parseFloat(frm.doc.exchange_rate) || 1)
        if(payment_amount>frm.doc.amount_to_pay){
            amount_to_pay = frm.doc.amount_to_pay/ (parseFloat(frm.doc.exchange_rate) || 1)
            frm.set_value("input_amount", amount_to_pay);
            payment_amount = amount_to_pay
        }
        frm.set_value("payment_amount", payment_amount);
        if (frm._from_set_value) return;      
        update_allocated_amount(frm);
    },
});

///child table in purchase order payment
frappe.ui.form.on("Purchase Order Payment Invoices", {
    refresh(frm) {

    },
    pay: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];   
        frappe.model.set_value(cdt, cdn, "payment_amount", row.purchase_order_balance || 0);
        calculate_row_purchase_order(frm, cdt, cdn);
        calculate_totals(frm);
    },
    purchase_order: function (frm, cdt, cdn) {
        calculate_row_purchase_order(frm, cdt, cdn);
        calculate_totals(frm);
    },
    purchase_orders_add: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];   
        row.exchange_rate = frm.doc.exchange_rate
        calculate_totals(frm)
    },
    purchase_orders_remove: function (frm, cdt, cdn) {
        calculate_totals(frm)
    },
    input_amount: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];   
        let payment_amount = (row.input_amount || 0) / (row.exchange_rate || 1);
        if(payment_amount>row.purchase_order_balance){
            payment_amount = row.purchase_order_balance
            frappe.model.set_value(cdt, cdn, "input_amount", payment_amount);
        }
        frappe.model.set_value(cdt, cdn, "payment_amount", payment_amount);
        calculate_row_purchase_order(frm, cdt, cdn);
        const total_payment_amount = frm.doc.purchase_orders.reduce((sum, s) => sum + (s.payment_amount || 0), 0);
        frm._from_set_value = true;
        frm.set_value("input_amount",total_payment_amount * parseFloat(frm.doc.exchange_rate || 1)
        ).then(() => {
            frm._from_set_value = false;
            calculate_totals(frm);
        });
    },
    input_write_off_amount: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];   
        frappe.model.set_value(cdt, cdn, "write_off_amount", row.input_write_off_amount / row.exchange_rate);
        calculate_row_purchase_order(frm, cdt, cdn);
        calculate_totals(frm);
    },
});

function calculate_row_purchase_order(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    const payment_amount = row.payment_amount || 0;
    const write_off_amount = (row.write_off_amount || 0);
    frappe.model.set_value(cdt, cdn, "balance", (row.purchase_order_balance || 0) - (payment_amount + write_off_amount));
}

function calculate_totals(frm) {
    const total_amount_to_pay = frm.doc.purchase_orders.reduce((sum, s) => sum + (s.purchase_order_balance || 0), 0);
    const total_write_off_amount = frm.doc.purchase_orders.reduce((sum, s) => sum + (s.write_off_amount || 0), 0);
    const payment_amount = frm.doc.purchase_orders.reduce((sum, s) => sum + (s.payment_amount || 0), 0);
    const total_invoices = frm.doc.purchase_orders.filter(r => r.purchase_order).length;
    const balance = total_amount_to_pay - (payment_amount + total_write_off_amount)
    frm.set_value("payment_amount", payment_amount);
    frm.set_value("total_invoices", total_invoices);
    frm.set_value("amount_to_pay", total_amount_to_pay);
    frm.set_value("total_write_off_amount", total_write_off_amount);
    frm.set_value("balance", balance);
}

function get_unpaid_purchase_orders(frm) {
    if (!frm.doc.party) {
        frm.clear_table("purchase_orders");
        frm.refresh_field("purchase_orders");
        return;
    };
    if (!frm.doc.outlet) return;
    return new Promise((resolve, reject) => {
    frm.call({
        method: "get_unpaid_purchase_orders",
        doc: frm.doc,  
        freeze: true,
        }).then(r => {
            frm.clear_table("purchase_orders");
            (r.message || []).forEach(row => {
                let d = frm.add_child("purchase_orders");
                d.purchase_order = row.name;
                d.outlet = row.outlet;
                d.party_type = row.party_type;
                d.party = row.party;
                d.payment_date = frm.doc.posting_date;
                d.posting_date = row.posting_date;
                d.purchase_order_balance = row.balance;
                d.balance = row.balance;
                d.exchange_rate = frm.doc.exchange_rate
            });
            frm.refresh_field("purchase_orders");
            resolve(r.message || []);
        })
        .catch(err => {
            frm.clear_table("purchase_orders");
            frm.refresh_field("purchase_orders");
            reject(err);
        });
    });
}

function update_allocated_amount(frm) {
    let paid_amount = frm.doc.payment_amount;
    if ((frm.doc.purchase_orders || []).length > 0) {
        frm.doc.purchase_orders.forEach(r => {
            if (paid_amount < r.purchase_order_balance) {
                r.input_amount = paid_amount*r.exchange_rate;
                r.payment_amount = paid_amount;
            }
            else {
                r.input_amount = r.purchase_order_balance*r.exchange_rate;
                r.payment_amount = r.purchase_order_balance
            }
            r.balance = (r.purchase_order_balance || 0) - (r.payment_amount || 0) - (r.write_off_amount || 0)
            paid_amount = paid_amount - r.payment_amount
        });
        frm.refresh_field("purchase_orders")
        calculate_totals(frm);
    }
}

function update_allocated_payment_date(frm) {
    if ((frm.doc.purchase_orders || []).length > 0) {
        frm.doc.purchase_orders.forEach(r => {
            r.payment_date = frm.doc.posting_date;
        });
        frm.refresh_field("purchase_orders");
    }
}

