// Copyright (c) 2025, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Orders", {
  onload: function (frm) {
     
  },
  refresh: function (frm) { 
     
  },
  party_type:function (frm) {
      frm.set_value("party", "");
      frm.refresh_field("party")
  },

   party:async  function (frm) {
    const product_codes = (frm.doc.purchase_products || []).filter(d => (d.product_code||"")!="" ).map(d => d.product_code); 
    if(product_codes.length > 0){
       (frm.doc.purchase_products || []).forEach((row) => {
        get_init_purchase_cost(frm, row)
      });
    }
  },
});

frappe.ui.form.on("Purchase Order Products", {
  product_code:function (frm, cdt, cdn){    
    let row = locals[cdt][cdn]; // get current child row
    get_init_purchase_cost(frm,row)
  } ,
  quantity: function (frm, cdt, cdn) {
    calculate_total_cost(frm, cdt, cdn);
  },
  cost: function (frm, cdt, cdn) {
    calculate_total_cost(frm, cdt, cdn);
  },
});

frappe.ui.form.on("Purchase Order Payment Child", {
    payments_remove: function(frm,cdt,cdn){
      update_summary(frm);
    },
    payments_add: function (frm, cdt, cdn) {
      if(frm.doc.balance == frm.doc.total_cost){
        let row = locals[cdt][cdn]; // get current child row
        frappe.call({
        method: 'ice_control.api.api.get_default_payment_type',
        callback: (r) => {
            row.payment_type = r.message.payment_type
            row.exchange_rate = r.message.exchange_rate
            row.currency = r.message.currency
            row.input_amount = frm.doc.total_cost/r.message.exchange_rate
            row.payment_amount = frm.doc.total_cost/r.message.exchange_rate
        }
        }).then((r)=>{
            update_summary(frm);
        })
      }
    },
    payment_type: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.call({
        method: 'ice_control.api.api.get_exchange_rate',
        args:{
          currency:row.currency
        },
        callback: (r) => {
            let payment_amount = 0;
            let write_off_amount = 0;
            (frm.doc.payments || []).forEach((a) => {
              if(a.name != row.name)
              payment_amount += a.payment_amount || 0;
              write_off_amount += ((a.write_off_amount || 0)/(a.exchange_rate || 1));
            });
            frappe.model.set_value(cdt, cdn, "exchange_rate", (r.message));
            frappe.model.set_value(cdt, cdn, "input_amount", ((frm.doc.total_cost-(payment_amount+write_off_amount))*r.message));
        }
        }).then((r)=>{
            update_summary(frm);
        })
        calculate_payment_amount(frm, cdt, cdn);
    },
    input_amount: function (frm, cdt, cdn) {
        calculate_payment_amount(frm, cdt, cdn);
    },
    write_off_amount: function (frm, cdt, cdn) {
        calculate_payment_amount(frm, cdt, cdn);
    }
});

async function get_init_purchase_cost(frm, product){
    frappe.call({
      method: 'ice_control.purchase_order.doctype.purchase_orders.purchase_orders.get_purchase_cost',
      args: {
         "param":{
            "doc": frm.doc,
            "product": product
         }
      },
      callback: (r) => {
        frappe.model.set_value(product.doctype, product.name, "cost", (r.message));
      }
      })
    frm.refresh_field("purchase_products");
}

function calculate_total_cost(frm, cdt, cdn) {
  let row = locals[cdt][cdn]; // get current child row
  let total = (row.quantity || 0) * (row.cost || 0);
  frappe.model.set_value(cdt, cdn, "sub_total", total);
  frappe.model.set_value(cdt, cdn, "total_cost", total);
  update_summary(frm);
}

function update_summary(frm) {
  let total_cost = 0;
  let total_quantity = 0;
  let total_payment = 0;
  let write_off_amount = 0;
  (frm.doc.purchase_products || []).forEach((row) => {
    total_cost += row.total_cost || 0;
    total_quantity += row.quantity || 0;
  });
  (frm.doc.payments || []).forEach((row) => {
    total_payment += row.payment_amount || 0;
    write_off_amount += ((row.write_off_amount || 0)/(row.exchange_rate || 1));
  });
  frm.set_value("total_quantity", total_quantity);
  frm.set_value("total_cost", total_cost);
  frm.set_value("total_payment", total_payment);
  frm.set_value("balance", frm.doc.total_cost - (total_payment + write_off_amount));
}

function calculate_payment_amount(frm, cdt, cdn) {
  let row = locals[cdt][cdn];
  let payment_amount = (row.input_amount || 0) / (row.exchange_rate || 1);
  frappe.model.set_value(cdt, cdn, "payment_amount", payment_amount);
  let total_payment = 0;
  let write_off_amount = 0;
  (frm.doc.payments || []).forEach((row) => {
    total_payment += row.payment_amount || 0;
    write_off_amount += ((row.write_off_amount || 0)/(row.exchange_rate || 1));
  });
  frm.set_value("total_payment", total_payment);
  frm.set_value("write_off", write_off_amount);
  frm.set_value("balance", frm.doc.total_cost - (total_payment + write_off_amount));
}
