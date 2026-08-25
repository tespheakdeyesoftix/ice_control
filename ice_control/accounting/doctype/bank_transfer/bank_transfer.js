// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Bank Transfer", {
// 	refresh(frm) {

// 	},
// });
// Copyright (c) 2025, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bank Transfer", {
	currency(frm) {
         frappe.call({
            method: "get_currency_exchange_rate",
            doc: frm.doc,
            callback: function (r) {
				frm.set_value("exchange_rate",r.message)
                frm.refresh_field('exchange_rate');
            },
        });
	},
    input_amount(frm){
        update_amount(frm)
    },
    exchange_rate(frm){
        update_amount(frm)
    }
});

function update_amount(frm){
      frm.set_value("amount",frm.doc.input_amount/frm.doc.exchange_rate)
        frm.refresh_field('amount');
}
