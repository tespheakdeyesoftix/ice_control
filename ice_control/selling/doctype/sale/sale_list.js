frappe.listview_settings['Sale'] = {
    add_fields: ['balance', 'total_amount', 'total_paid', 'is_foc', 'customer_name', 'grand_total', 'sale_status', 'status'],
    hide_name_column: true, // hide the last column which shows the `name`
    // set this to true to apply indicator function on draft documents too
    has_indicator_for_draft: false,

    get_indicator(doc) {
        if (doc.sale_status === "Draft") {
            return [__("Draft"), "gray"];
        }
        if (doc.sale_status === "Closed") {

            if (doc.status == "Paid") {
                return [__("Paid"), "green"];
            } else if (doc.status == "Partially Paid") {
                return [__("Partially Paid"), "orange"];
            } else {
                if (doc.status == "Deleted") {
                    return [__("Deleted"), "red"];
                }
                else {
                    return [__("Unpaid"), "red"];
                }
            }
        }

    },
}