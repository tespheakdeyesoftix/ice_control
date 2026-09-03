// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

// main table event
frappe.ui.form.on("Expense", {
	refresh(frm) {
        alert(frm.doc.outlet)
	},
    
	outlet(frm) {
        alert("u change me t o " + frm.doc.outlet)
	},

});



// chid table event
frappe.ui.form.on("Expense Items", {

     expense_items_remove(frm) {
        alert("u remove me")
    },
    
     expense_items_add(frm) {
        alert("u add me")
    },

     quantity(frm, cdt, cdn) {
        return
        const row = frappe.get_doc(cdt, cdn);

        calculeteExpenseItemRow(frm, row)
    },
    price(frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);

        calculeteExpenseItemRow(frm, row)
    },


	
});


function summaryTotal(frm){
    const total_amount = (frm.doc.expense_items || []).reduce(
    (sum, row) => sum + (Number(row.total_amount) || 0),
    0
);

        frm.doc.total_expense = total_amount

        frm.refresh_field("total_expense");
}
function calculeteExpenseItemRow(frm,row){
            row.total_amount = (row.quantity ?? 0) * (row.price ?? 0)
            summaryTotal(frm)
        frm.refresh_field("expense_items");
}


