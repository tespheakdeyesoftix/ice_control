
frappe.ui.form.on("Sale Payment", {
    onload(frm) {
        frm.set_query("sale", "sales", function (doc, cdt, cdn) {

            let sale_filter = {
                    "customer": doc.customer || 'Not Set',
                    "outlet": doc.outlet || 'Not Set',
                    "balance": [">", 0],
                    "sale_status": "Closed"
                };

            if (doc.sale){
                sale_filter.name = doc.sale
            }
            return {
                "filters": sale_filter,
            };
        });

            // we run this to for read sale payment, write off and balance again
        updateSalePaymentAmount(frm);

    },
    refresh(frm) {
        setOutlet(frm);
        if(!frm.is_new() && frm.doc.docstatus==0){
            if(frm.doc.exchange_rate){
                set_value_if_changed(frm, "exchange_rate_virtual", 1 / parseFloat(frm.doc.exchange_rate));
            }
        }
    },

    async customer(frm) {
        await getCustomerBalance(frm)
        await get_unpaid_sales(frm)
        if ((frm.doc.input_amount || 0) > 0) {
            update_allocated_amount(frm)
        } else {
            calculate_totals(frm)
        }
    },
    async outlet(frm) {
        await getCustomerBalance(frm)
        await get_unpaid_sales(frm)
        if ((frm.doc.input_amount || 0) > 0) {
            update_allocated_amount(frm)
        } else {
            calculate_totals(frm)
        }

    },
    async payment_type(frm) {
        // if ((frm.doc.input_amount || 0) > 0) {
        //     update_allocated_amount(frm)
        // }
        // if(frm.doc.exchange_rate){
        //     set_value_if_changed(frm, "exchange_rate_virtual", 1 / parseFloat(frm.doc.exchange_rate));
        // }
        frm.call("payment_type_change")
    },
    // this is button get Sale Invoice by Date
    async get_sales_invoice(frm) {
        if (!frm.doc.outlet) {
            frappe.throw(__("Please select outlet"))
            return
        }

        if (!frm.doc.customer) {
            frappe.throw(__("Please select customer"))
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
        await get_unpaid_sales(frm)
        calculate_totals(frm)
    },
    input_amount(frm) {
        if (!frm.doc.payment_type) {
            frappe.throw(__("Please select payment type"))
        }
        const payment_amount = frm.doc.input_amount / (frm.doc.exchange_rate || 1)
        frm.set_value("payment_amount", payment_amount);
        frm.set_value("total_payment_amount_virtual", payment_amount);

        update_allocated_amount(frm);
    },

});


frappe.ui.form.on("Sale Payment Invoices", {
    refresh(frm) {

    },
    sale: function (frm, cdt, cdn) {
        calculate_row_sale(frm, cdt, cdn);
        calculate_totals(frm);
    },
    sales_add: function (frm) {
        calculate_totals(frm)
    },
    sales_remove: function (frm) {
        calculate_totals(frm)

    },

    pay: function (frm, cdt, cdn) {
        // when user click on button pay get sale balance update  to payment amount
        // if we change value in sale payment invoice child table input amount will be clear
        // and total_payment_amount is sum from child table

        let row = locals[cdt][cdn];

        frappe.model.set_value(cdt, cdn, "payment_amount", row.sale_balance || 0);
        calculate_row_sale(frm, cdt, cdn);
        calculate_totals(frm);

    },
    payment_amount: function (frm, cdt, cdn) {
        // if we change value in sale payment invoice child table input amount will be clear
        // and total_payment_amount is sum from child table
        calculate_row_sale(frm, cdt, cdn);
        calculate_totals(frm);

    },
    write_off_amount: function (frm, cdt, cdn) {
        // if we change value in sale payment invoice child table input amount will be clear
        // and total_payment_amount is sum from child table
        calculate_row_sale(frm, cdt, cdn);
        calculate_totals(frm);
    },
})


// ---------------------------------------------------------------------
// Helper: only writes a value if it's actually different from what's
// already stored (using a small tolerance for currency/float rounding).
// This prevents frm.set_value from marking the form "dirty" every time
// a calculation runs and happens to produce the same number again.
// ---------------------------------------------------------------------
function set_value_if_changed(frm, field, new_value, tolerance = 0.001) {
    const current = frm.doc[field];
    if (typeof new_value === "number") {
        const cur_num = parseFloat(current) || 0;
        if (Math.abs(cur_num - new_value) > tolerance) {
            frm.set_value(field, new_value);
        }
    } else {
        if (current !== new_value) {
            frm.set_value(field, new_value);
        }
    }
}

function child_value_if_changed(cdt, cdn, field, new_value, current_value, tolerance = 0.001) {
    const cur_num = parseFloat(current_value) || 0;
    if (Math.abs(cur_num - new_value) > tolerance) {
        frappe.model.set_value(cdt, cdn, field, new_value);
        return true;
    }
    return false;
}


function getCustomerBalance(frm) {
    if (!frm.doc.customer) return;
    if (!frm.doc.outlet) return;
    return new Promise((resolve, reject) => {
        frm.call("get_customer_credit_balance")
            .then(r => {
                frm.set_value("customer_balance", r.message || 0);

                resolve(r.message || 0);
            })
            .catch(err => {
                frm.set_value("customer_balance", 0);
                reject(err);
            });
    });

}

function get_unpaid_sales(frm) {
    if (!frm.doc.customer) {
        frm.clear_table("sales");
        frm.refresh_field("sales");
        return;
    };
    if (!frm.doc.outlet) return;


    return new Promise((resolve, reject) => {
        frm.call("get_unpaid_sales")
            .then(r => {

                frm.clear_table("sales");
                // Loop and add rows
                r.message.forEach(row => {
                    let child_row = frm.add_child("sales");
                    child_row.sale = row.name;
                    child_row.posting_date = row.posting_date;
                    child_row.total_amount = row.total_amount;
                    child_row.paid_amount = row.total_payment;
                    child_row.sale_balance = row.balance;
                    child_row.balance = row.balance;

                });


                frm.refresh_field("sales");
                resolve(r.message || 0);
            })
            .catch(err => {
                frm.set_value("sales", 0);
                reject(err);
            });
    });

}

function update_allocated_amount(frm) {
    let paid_amount = frm.doc.payment_amount;

    if ((frm.doc.sales || []).length > 0) {
        frm.doc.sales.forEach(r => {
            if (paid_amount < r.sale_balance) {
                r.payment_amount = paid_amount;
            }
            else {
                r.payment_amount = r.sale_balance
            }
            r.balance = r.sale_balance - r.payment_amount
            paid_amount = paid_amount - r.payment_amount
        });
        frm.refresh_field("sales")
        calculate_totals(frm);
    }

}


function calculate_row_sale(frm, cdt, cdn) {

    let row = locals[cdt][cdn];
    const payment_amount = row.payment_amount || 0;
    const write_off_amount = row.write_off_amount || 0;
    const new_balance = (row.sale_balance || 0) - (payment_amount + write_off_amount);

    // only write if the balance actually changed (avoids re-dirtying the form)
    child_value_if_changed(cdt, cdn, "balance", new_balance, row.balance);

}


function calculate_totals(frm) {
    const total_amount_to_pay = frm.doc.sales.reduce((sum, s) => sum + (s.sale_balance || 0), 0);
    const payment_amount = frm.doc.sales.reduce((sum, s) => sum + (s.payment_amount || 0), 0);
    const write_off_amount = frm.doc.sales.reduce((sum, s) => sum + (s.write_off_amount || 0), 0);
    const total_sales_invoice = frm.doc.sales.filter(r => r.sale).length;
    const balance = total_amount_to_pay - (payment_amount + write_off_amount)

    // only write values that actually changed, so the form doesn't get
    // marked dirty again right after it was just saved
    set_value_if_changed(frm, "payment_amount", payment_amount);
    set_value_if_changed(frm, "total_sales_invoice", total_sales_invoice);
    set_value_if_changed(frm, "amount_to_pay", total_amount_to_pay);
    set_value_if_changed(frm, "total_amount_to_pay_virtual", total_amount_to_pay);
    set_value_if_changed(frm, "balance", balance);
    set_value_if_changed(frm, "balance_virtual", balance);


}
function set_amount_to_zero(frm) {
    frm.set_value("input_amount", 0);
    frm.set_value("total_amount", 0);
    frm.set_value("payment_balance", frm.doc.currency_symbol + " " + ((frm.doc.balance - frm.doc.total_amount) * (frm.doc.exchange_rate || 1)).toLocaleString());
}

function update_total_amount(frm) {
    if (frm.doc.input_amount == 0 && frm.doc.write_off_amount == 0) {
        frm.set_value("total_amount", 0);
    }
    else {
        let total_amount = ((frm.doc.input_amount || 0) + (frm.doc.write_off_amount || 0)) / (frm.doc.exchange_rate || 1);
        frm.set_value("total_amount", total_amount);
    }
    frm.set_value("payment_balance", frm.doc.currency_symbol + " " + ((frm.doc.balance - frm.doc.total_amount) * (frm.doc.exchange_rate || 1)).toLocaleString());
}

function setOutlet(frm) {

    if (frm.is_new()) {

        frm.call("get_default_outlet").then(r => {
            frm.set_value("outlet", r.message);

        })
    }

}

function updateSalePaymentAmount(frm) {

    // don't touch anything for new docs, submitted docs, or docs with no rows
    if (frm.is_new() || frm.doc.docstatus != 0) return;
    if (!frm.doc.sales || !frm.doc.sales.length) return;

    frappe.db.get_list("Sale", {
        fields: ["name", "total_amount", "total_payment", "total_write_off"],
        filters: { name: ["in", frm.doc.sales.map(x => x.sale)] },
        limit: frm.doc.sales.length
    }).then(data => {

        let changed = false;

        frm.doc.sales.forEach(r => {
            const s = data.find(x => x.name == r.sale);
            if (!s) return;

            const new_total_amount = s.total_amount || 0;
            const new_paid_amount = s.total_payment || 0;
            const new_sale_balance = new_total_amount - (new_paid_amount - (s.total_write_off || 0));
            const new_balance = new_sale_balance - ((r.payment_amount || 0) + (r.write_off_amount || 0));

            // only update + mark "changed" if the value is actually different
            if (Math.abs((r.total_amount || 0) - new_total_amount) > 0.001) {
                r.total_amount = new_total_amount;
                changed = true;
            }
            if (Math.abs((r.paid_amount || 0) - new_paid_amount) > 0.001) {
                r.paid_amount = new_paid_amount;
                changed = true;
            }
            if (Math.abs((r.sale_balance || 0) - new_sale_balance) > 0.001) {
                r.sale_balance = new_sale_balance;
                changed = true;
            }
            if (Math.abs((r.balance || 0) - new_balance) > 0.001) {
                r.balance = new_balance;
                changed = true;
            }
        });

        // nothing changed -> don't touch the form, don't recalc totals,
        // don't mark it dirty. This is the key fix for the "Not Saved" loop.
        if (!changed) return;

        // check if have input amount then recalculate allocate amount
        if (frm.doc.input_amount > 0) {
            update_allocated_amount(frm)
        } else {
            frm.refresh_field("sales")
            calculate_totals(frm);
        }

    })

}
