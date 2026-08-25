frappe.borrow_product = {
    onBulkReturnProduct: function (options = null) {
        return returnProduct(options);   // ✅ return Promise
    },
};

let last_customer = null;


function returnProduct(options) {
    return new Promise((resolve) => {

        let resolved = false; // ✅ guard flag
        let last_customer = null;

        const safeResolve = (value) => {
            if (resolved) return;
            resolved = true;
            resolve(value);
        };

        const d = new frappe.ui.Dialog({
            title: __('Add Return Product'),
            size: "extra-large",
            fields: [
                {
                    fieldname: 'customer',
                    label: __('Customer'),
                    fieldtype: 'Link',
                    options: "Customer",
                    default: options?.customer || frappe.utils.get_url_arg('customer') || "",
                    reqd: 1,
                    read_only:options?.customer,
                    onchange() {
                        const customer = d.get_value('customer');
                        if (!customer || customer === last_customer) return;
                        last_customer = customer;
                        load_return_products(d, customer);
                    }
                },
                { fieldtype: "Column Break" },
                {
                    fieldname: 'posting_date',
                    label: __('Return Date'),
                    fieldtype: 'Date',
                    reqd: 1,
                    default: frappe.datetime.nowdate()
                },
                { fieldtype: "Section Break" },
                returnProductTableField()
            ],
            primary_action_label: __('Save'),
            async primary_action(values) {

                if (values.return_products.find(
                    x => flt(x.remaining_quantity) - flt(x.return_quantity || 0) < 0
                )) {
                    frappe.throw(__("Return quantity can not be greater than borrow quantity"));
                    safeResolve(false);
                    return;
                }

                d.disable_primary_action();

                try {
                    await frappe.call({
                        method: 'ice_control.selling_ifms.doctype.borrow_product.borrow_product.update_bulk_return_product',
                        args: { data: values },
                        freeze: true,
                        freeze_message: __('Saving...')
                    });

                    frappe.show_alert({
                        message: __('Save successfully'),
                        indicator: 'green'
                    });

                    safeResolve(true); // ✅ SUCCESS
                    d.hide();
                } catch (e) {
                    console.error(e);
                    safeResolve(false);
                } finally {
                    d.enable_primary_action();
                }
            }
        });

        // ❌ Only resolve false if NOT already resolved
        d.onhide = () => safeResolve(false);

        d.show();

        if(options?.customer ||  frappe.utils.get_url_arg('customer')){
            load_return_products(d,options?.customer ||  frappe.utils.get_url_arg('customer'))
        }
    });
}


function returnProductTableField() {
    return {
        fieldname: 'return_products',
        reqd: 1,
        fieldtype: 'Table',
        label: __('Return Product'),
        cannot_add_rows: true,
        data: [],
        fields: [
            {
                fieldname: 'name',
                fieldtype: 'Data',
                label: __('Name'),
                hidden: 1
            },
            {
                fieldname: 'product_name',
                label: __('Product'),
                fieldtype: 'Data',
                in_list_view: 1,
                read_only: 1
            },
            {
                fieldname: 'posting_date',
                label: __('Borrow Date'),
                fieldtype: 'Date',
                in_list_view: 1,
                read_only: 1
            },
            {
                fieldtype: 'Float',
                fieldname: 'borrow_quantity',
                label: __('Borrow QTY'),
                in_list_view: 1,
                read_only: 1,
                width: 50
            },
            {
                fieldtype: 'Float',
                fieldname: 'returned_quantity',
                label: __('Returned QTY'),
                in_list_view: 1,
                read_only: 1,
                width: 50
            },
            {
                fieldtype: 'Float',
                fieldname: 'remaining_quantity',
                label: __('Remaining QTY'),
                in_list_view: 1,
                read_only: 1
            },
            {
                fieldtype: 'Float',
                fieldname: 'return_quantity',
                label: __('Return QTY'),
                in_list_view: 1,
                onchange(e) {
                    const $input = $(e.currentTarget);
                    const $row = $input.closest('.grid-row');
                    const grid_row = $row.data('grid_row');
                    if (!grid_row) return;

                    const row = grid_row.doc;
                    const remaining = flt(row.remaining_quantity);
                    const return_qty = flt($input.val());

                    row.return_quantity = return_qty;
                    row.balance_quantity = remaining - return_qty;

                   
                    grid_row.refresh();    
                  
                    
                }
            },
            {
                fieldtype: 'Float',
                fieldname: 'balance_quantity',
                label: __('Balance QTY'),
                in_list_view: 1,
                read_only: 1
            },
            {
                fieldtype: 'Data',
                fieldname: 'note',
                label: __('Note'),
                in_list_view: 1
            }
        ]
    };
}

function load_return_products(d, customer) {
    frappe.call({
        method: 'ice_control.selling_ifms.doctype.borrow_product.borrow_product.get_customer_borrow_product_remaining',
        args: { customer },
        freeze: true,
        freeze_message: __('Loading products...')
    }).then(r => {
        if (!r.message) return;

        const table = d.fields_dict.return_products;
        table.df.data = r.message;
        table.grid.refresh();

    });
}
