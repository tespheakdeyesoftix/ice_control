// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Product", {
	onload(frm) {
        frm.set_query('product_code', 'product_materials', function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            return {
                filters: [
                    ['Product', 'name', '!=', frm.doc.name]
                ]
            };
        });
	},
    refresh(frm){
        if(!frm.is_new() && frm.doc.is_inventory_product == 1){
            frm.set_df_property("is_inventory_product", "read_only", 1)
        }
    }
});
frappe.ui.form.on("Product Materials", {
    unit:function (frm, cdt, cdn){    
        let row = locals[cdt][cdn];
        get_multiplier(frm,row)
    },
});
async function get_multiplier(frm,product){
    frappe.call({
      method: 'ice_control.api.inventory.get_product_units_multiplier',
      args: {
        "product_code":product.product_code,
        "unit":product.unit
      },
      callback: (r) => {
            frappe.model.set_value(product.doctype, product.name, "multipler", (r.message || 0));
        }
    })
}