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




            setSaleFormReadOnly(frm);

            // Refresh the fields to apply the changes
            frm.refresh_fields();





        }


        updateSummary(frm);

        addCustomButton(frm)

        renderPaymentHistory(frm)

        renderSplitBillList(frm)



    },
    after_save(frm) {
        setSaleFormReadOnly(frm);
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

        // check if sale_status == "Draft" show wanring message ask to close bill
        if(frm.doc.sale_status == "Draft"){
            frm.set_intro(__('បុងនេះស្ថិតនៅក្នុងស្ថានភាពរង់ចាំ។ ការដាក់បុងរង់ចាំគឺសម្រាប់រក្សាទុកបណ្តោះអាសន្នក្នុងរយៈពេលខ្លីប៉ុណ្ណោះ មិនមែនសម្រាប់ទុករយៈពេលយូរទេ។ សូមព្យាយាមពិនិត្យ និងបិទការលក់ទាំងនេះឱ្យបានឆាប់បំផុត។'), "red");
        }


    }
}

function setIndicator(frm) {
    if (!frm.is_new()) {
        frm.dashboard.add_indicator(
            __("Sale Quantity: {0} {1}", [frappe.format(frm.doc.total_sale_quantity, { "fieldtype": "Float" }), frm.doc.outlet_unit]),
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
        setTimeout(() => {
            get_multiplier(frm,row);
        }, 250);
    }
});

async function get_multiplier(frm, product){
    frappe.call({
      method: 'ice_control.api.inventory.get_product_units_multiplier',
      args: {
        "product_code": product.product_code,
        "unit": product.unit
      },
      callback: (r) => {
        frappe.model.set_value(product.doctype, product.name, "multiplier", (r.message || 0));
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

    if (
        frm.doc.sale_status === "Closed"
    ) {
        frm.add_custom_button(
            __("Edit Order"),
            () => openEditOrderDialog(frm),
            __("Actions")
        );
    }


    if (frm.doc.balance > 0 && frm.doc.sale_status == "Closed") {
        frm.add_custom_button(__("Add Payment"), function () {
            frappe.route_options = { customer: frm.doc.customer, customer_name: frm.doc.customer_name, sale: frm.doc.name, outlet: frm.doc.outlet };
            frappe.set_route('Form', 'Sale Payment', 'new');

        }, __("Actions"));
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
    if (!frm.is_new() && frm.doc.sale_status != "Deleted") {
        const deleteLabel = __("\u179b\u17bb\u1794\u1794\u17bb\u1784");

        frm.page.set_secondary_action(deleteLabel, () => {
            openDeleteBillDialog(frm, frm.doc.name, null, {
                title: deleteLabel,
                message: __("\u178f\u17be\u17a2\u17d2\u1793\u1780\u1796\u17b7\u178f\u1787\u17b6\u1785\u1784\u17cb\u179b\u17bb\u1794\u1794\u17bb\u1784\u1793\u17c1\u17c7\u1798\u17c2\u1793\u1791\u17c1?"),
                freeze_message: __("Deleting bill..."),
                success_message: __("Bill {0} was deleted.", [frm.doc.name])
            });
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

function setSaleFormReadOnly(frm) {
    if (
        frm.is_new()
        || !["Closed", "Deleted"].includes(frm.doc.sale_status)
    ) {
        return;
    }

    if (!frm._sale_original_perm) {
        frm._sale_original_perm = frm.perm.map(permission => ({
            ...permission
        }));
    }

    frm.fields.forEach(field => {
        if (field.df.bold == 0) {
            if (field._sale_original_read_only === undefined) {
                field._sale_original_read_only = cint(field.df.read_only);
            }
            frm.set_df_property(field.df.fieldname, "read_only", 1);
        }
    });

    frm.set_read_only();
    frm.refresh_fields();
}


function openEditOrderDialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Edit Order"),
        fields: [
            {
                fieldname: "edit_message",
                fieldtype: "HTML",
                options: `
                    <div class="alert alert-warning" style="margin-bottom: 0">
                        ${__("Why do you want to edit this order?")}
                    </div>
                `
            },
            {
                fieldname: "note",
                fieldtype: "Small Text",
                label: __("Note"),
                reqd: 1
            }
        ],
        primary_action_label: __("Confirm"),
        async primary_action(values) {
            dialog.disable_primary_action();

            try {
                await frappe.call({
                    method: "ice_control.selling.doctype.sale.sale.enable_edit_mode",
                    type: "POST",
                    args: {
                        doc_name: frm.doc.name,
                        note: values.note
                    },
                    freeze: true,
                    freeze_message: __("Enabling edit mode...")
                });

                dialog.hide();
                makeSaleFormEditable(frm);
                frm.remove_custom_button(__("Edit Order"), __("Actions"));

                frappe.show_alert({
                    message: __("Edit mode enabled."),
                    indicator: "green"
                });
            } finally {
                dialog.enable_primary_action();
            }
        }
    });

    dialog.show();
}

function makeSaleFormEditable(frm) {
    if (frm._sale_original_perm) {
        frm.perm = frm._sale_original_perm.map(permission => ({
            ...permission
        }));
    }

    frm.fields.forEach(field => {
        if (field._sale_original_read_only !== undefined) {
            frm.set_df_property(
                field.df.fieldname,
                "read_only",
                field._sale_original_read_only
            );
        }
    });

    frm.enable_save();
    frm.refresh_fields();
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

                "customer",
                "customer_name",
                "total_quantity",
                "total_amount",
                "status"
            ],
            filters: {
                parent_bill_number: frm.doc.name,
                sale_status: "Closed"
            },
            order_by: "creation",
            limit_page_length: 0
        });
    }

    const wrapper = $(frm.fields_dict["html_sale_split_bill_list"].wrapper);
    const html = frappe.render_template("split_bill_list", { data });

    wrapper.html(html);
    wrapper.find(".btn-add-split-bill").on("click", () => {
        openSplitBillDialog(frm);
    });
    wrapper.find(".btn-print-split-bill").on("click", async event => {
        const button = $(event.currentTarget);

        button.prop("disabled", true);
        try {
            await window.printDoctypeReport("Sale", button.data("sale-name"));
        } finally {
            button.prop("disabled", false);
        }
    });
    wrapper.find(".btn-edit-split-bill").on("click", async event => {
        const button = $(event.currentTarget);
        const saleName = button.data("sale-name");

        button.prop("disabled", true);
        try {
            const splitBillDoc = await frappe.db.get_doc("Sale", saleName);
            openSplitBillDialog(frm, splitBillDoc);
        } finally {
            button.prop("disabled", false);
        }
    });
    wrapper.find(".btn-delete-split-bill").on("click", event => {
        const button = $(event.currentTarget);
        deleteSplitBill(frm, button.data("sale-name"), button);
    });
}

function deleteSplitBill(frm, saleName, button) {
    const escapedSaleName = frappe.utils.escape_html(String(saleName || ""));

    openDeleteBillDialog(frm, saleName, button, {
        title: __("Delete Split Bill"),
        message: `
            ${__("Are you sure you want to delete split bill")}
            <strong>${escapedSaleName}</strong>?
        `,
        freeze_message: __("Deleting split bill..."),
        success_message: __("Split bill {0} was deleted.", [saleName])
    });
}

function openDeleteBillDialog(frm, saleName, button, options = {}) {
    const dialog = new frappe.ui.Dialog({
        title: options.title || __("Delete Bill"),
        fields: [
            {
                fieldname: "delete_message",
                fieldtype: "HTML",
                options: `
                    <div class="alert alert-warning" style="margin-bottom: 0">
                        ${options.message || __("Are you sure you want to delete this bill?")}
                    </div>
                `
            },
            {
                fieldname: "note",
                fieldtype: "Small Text",
                label: __("Note"),
                reqd: 1
            }
        ],
        primary_action_label: __("Delete"),
        async primary_action(values) {
            if (button) {
                button.prop("disabled", true);
            }
            dialog.disable_primary_action();

            try {
                await frappe.call({
                    method: "ice_control.selling.doctype.sale.sale.delete_bill",
                    args: {
                        doc_name: saleName,
                        note: values.note
                    },
                    freeze: true,
                    freeze_message: options.freeze_message || __("Deleting bill...")
                });

                dialog.hide();

                frappe.show_alert({
                    message: options.success_message
                        || __("Bill {0} was deleted.", [saleName]),
                    indicator: "green"
                });

                await frm.reload_doc();
            } finally {
                if (button) {
                    button.prop("disabled", false);
                }
                dialog.enable_primary_action();
            }
        }
    });

    dialog.show();
    dialog.get_primary_btn()
        .removeClass("btn-primary")
        .addClass("btn-danger");
}

function openSplitBillDialog(frm, splitBillDoc = null) {
    const existingProducts = [...(splitBillDoc?.sale_products || [])];
    const splitBillProducts = (frm.doc.sale_products || [])
        .filter(product => cint(product.allow_split_bill) === 1)
        .map(product => {
            const existingIndex = existingProducts.findIndex(existing =>
                existing.product_code === product.product_code
                && existing.unit === product.unit
            );
            const existingProduct = existingIndex >= 0
                ? existingProducts.splice(existingIndex, 1)[0]
                : null;
            const editQuantity = flt(existingProduct?.quantity || 0);

            return {
                ...product,
                edit_quantity: editQuantity,
                total_sale_quantity:
                    flt(product.total_sale_quantity || 0) + editQuantity
            };
        });

    const productFields = [];
    const secondProductColumn = Math.ceil(splitBillProducts.length / 2);

    splitBillProducts.forEach((product, index) => {
        if (index === secondProductColumn && index > 0) {
            productFields.push({ fieldtype: "Column Break" });
        }

        productFields.push({
            fieldname: `split_bill_product_${index}`,
            fieldtype: "Float",
            label: product.product_name || product.product_code,
            description: `${__("ចំនួនអាចបំបែកបាន")}: ${format_number(
                flt(product.total_sale_quantity || 0),
                null,
                2
            )} ${product.unit || ""}`,
            default: product.edit_quantity,
            non_negative: 1,
            precision: 2,
            product_code: product.product_code,
            sale_product: product.name
        });
    });

    const dialog = new frappe.ui.Dialog({
        title: splitBillDoc ? __("កែប្រែបុងបំបែក") : __("បំបែកបុង"),
        size: "large",
        fields: [
            {
                fieldtype: "Section Break",
                label: __("ព័ត៌មានបុង")
            },
            {
                fieldname: "split_bill_information",
                fieldtype: "HTML",
                options: getSplitBillInformationHtml(
                    splitBillDoc || frm.doc,
                    splitBillProducts
                )
            },
            {
                fieldtype: "Section Break",
                label: __("ព័ត៌មានបំបែកបុងលម្អិត")
            },
            {
                fieldname: "customer",
                fieldtype: "Link",
                label: __("Customer"),
                options: "Customer",
                default: splitBillDoc?.customer || "",
                reqd: 1
            },
            {
                fieldtype: "Column Break"
            },
            {
                fieldname: "reference_number",
                fieldtype: "Data",
                label: __("Reference Number"),
                default: splitBillDoc?.reference_number || ""
            },
            {
                fieldtype: "Section Break",
                label: __("Products")
            },
            ...productFields,
            {
                fieldtype: "Section Break"
            },
            {
                fieldname: "note",
                fieldtype: "Small Text",
                label: __("Note"),
                default: splitBillDoc?.note || ""
            }
        ],
        primary_action_label: __("Save"),
        async primary_action(values) {
            const selectedProducts = splitBillProducts
                .map((product, index) => ({
                    product,
                    quantity: flt(values[`split_bill_product_${index}`] || 0)
                }))
                .filter(row => row.quantity > 0);

            if (!selectedProducts.length) {
                frappe.throw(__("Please enter a quantity for at least one product."));
            }

            const quantityOverLimit = selectedProducts.find(
                row => row.quantity > flt(row.product.total_sale_quantity || 0)
            );

            if (quantityOverLimit) {
                frappe.throw(
                    __("Split quantity for {0} cannot exceed {1}.", [
                        quantityOverLimit.product.product_name
                            || quantityOverLimit.product.product_code,
                        format_number(
                            flt(quantityOverLimit.product.total_sale_quantity || 0),
                            null,
                            2
                        )
                    ])
                );
            }

            dialog.disable_primary_action();

            try {
                const saleValues = {
                    doctype: "Sale",
                    sale_status: "Closed",
                    parent_bill_number: frm.doc.name,
                    customer: values.customer,
                    driver: frm.doc.customer,
                    posting_date: frm.doc.posting_date,
                    outlet: frm.doc.outlet,
                    stock_location: frm.doc.stock_location,
                    note: values.note,
                    reference_number: values.reference_number,
                    sale_products: selectedProducts.map(row =>
                        getSplitBillSaleProduct(row.product, row.quantity, frm)
                    )
                };

                let savedSale;

                if (splitBillDoc) {
                    const response = await frappe.call({
                        method: "frappe.client.save",
                        args: {
                            doc: {
                                ...splitBillDoc,
                                ...saleValues,
                                name: splitBillDoc.name
                            }
                        },
                        freeze: true,
                        freeze_message: __("Saving split bill...")
                    });
                    savedSale = response.message;
                } else {
                    savedSale = await frappe.db.insert(saleValues);
                }

                dialog.hide();

                frappe.show_alert({
                    message: splitBillDoc
                        ? __("Split bill {0} was updated.", [savedSale.name])
                        : __("Split bill {0} was created.", [savedSale.name]),
                    indicator: "green"
                });

                await frm.reload_doc();
            } finally {
                dialog.enable_primary_action();
            }
        }
    });

    dialog.show();
}

function getSplitBillSaleProduct(product, quantity, frm) {
    const multiplier = flt(product.multiplier || 1);
    const price = flt(product.price || 0);

    return {
        doctype: "Sale Products",
        product_code: product.product_code,
        product_name: product.product_name,
        photo: product.photo,
        base_unit: product.base_unit,
        outlet: frm.doc.outlet,
        allow_split_bill: product.allow_split_bill,
        sale_transaction_type: product.sale_transaction_type,
        allow_change_sale_type: product.allow_change_sale_type,
        unit: product.unit,
        multiplier,
        product_category: product.product_category,
        revenue_group: product.revenue_group,
        allow_sum_qty: product.allow_sum_qty,
        is_inventory_product: product.is_inventory_product,
        quantity,
        price,
        product_price: product.product_price,
        free_quantity: 0,
        return_quantity: 0,
        split_quantity: 0,
        total_sale_quantity: quantity,
        sub_total: quantity * price * multiplier,
        total_amount: quantity * price * multiplier,
        cost: product.cost,
        total_cost: flt(product.cost || 0) * quantity,
        stock_location: product.stock_location || frm.doc.stock_location,
        allow_free: product.allow_free,
        allow_change_price: product.allow_change_price,
        allow_return: product.allow_return,
        note: product.note
    };
}

function getSplitBillInformationHtml(doc, products) {
    const escapeHtml = value => frappe.utils.escape_html(String(value ?? ""));

    return frappe.render_template("split_bill_info", {
        bill: {
            name: escapeHtml(doc.name),
            posting_date: escapeHtml(
                frappe.format(doc.posting_date, { fieldtype: "Date" })
            ),
            customer: escapeHtml(
                doc.customer_name || doc.customer || ""
            )
        },
        products: products.map(product => ({
            product_name: escapeHtml(
                product.product_name || product.product_code
            ),
            quantity: escapeHtml(
                format_number(flt(product.total_sale_quantity || 0), null, 2)
            ),
            unit: escapeHtml(product.unit || "")
        }))
    });
}
