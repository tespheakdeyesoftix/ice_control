frappe.ui.form.on("Bank Transfer", {
    onload: function(frm) {
        if(frm.doc.bank == undefined || frm.doc.bank == ""){
            frappe.call({
                method: 'ice_control.api.api.get_default_bank',
                callback: function (r) {
                    frm.set_value("bank",r.message.name)
                    frm.refresh_field('bank');
                },
            });
        }
    },
	currency(frm) {
         frappe.call({
            method: 'ice_control.api.api.get_exchange_rate',
            args:{
                currency:frm.doc.currency
            },
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
