
frappe.ui.form.on("Sale Payment", {
      setup(frm) {
         frm.set_query("sale", "sales", (doc, cdt, cdn) => {
            const selectedSales = (doc.sales || [])
               .filter(row => row.name !== cdn && row.sale)
               .map(row => row.sale);
            const filters = {
               customer: doc.customer,
               outlet: doc.outlet,
               sale_status: "Closed",
               status: ["in", ["Unpaid", "Partially Paid"]],
               balance: [">", 0],
               posting_date: ["<=", doc.posting_date],
            };

            if (selectedSales.length) {
               filters.name = ["not in", selectedSales];
            }

            return {
               filters,
            }
         })
      },
      refresh(frm) {
         updateExchangeRateDisplay(frm);
         renderSalePaymentSummary(frm);
         hideSalesGridRowActions(frm);
         if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Select Sale Invoice"), () => {
               openSaleInvoiceDialog(frm)
            })
         }
      },
      posting_date(frm) {

         frm.call("get_customer_credit_balance")
      },
      outlet(frm) {
         frm.call("get_customer_credit_balance")
      },
      customer(frm) {
         frm.call("get_customer_credit_balance")
      },
      payment_type(frm) {
         frm.call("get_exchange_rate").then(() => {
            updateExchangeRateDisplay(frm)
         })
      },
      exchange_rate(frm) {
         updateExchangeRateDisplay(frm)
      },


})

frappe.ui.form.on("Sale Payment Invoices", {
    async sales_add(frm, cdt, cdn) {
        if (locals[cdt][cdn].sale) {
            await callUpdateSummary(frm);
        }
    },
    async sales_remove(frm) {
        await callUpdateSummary(frm);
    },
    sale(frm) {
        frappe.after_ajax(() => callUpdateSummary(frm));
    },
    async payment_amount(frm, cdt, cdn) {
        updateChildSaleBalance(frm, cdt, cdn);
        await callUpdateSummary(frm);
    },
    async write_off_amount(frm, cdt, cdn) {
        updateChildSaleBalance(frm, cdt, cdn);
        await callUpdateSummary(frm);
    },
});

async function openSaleInvoiceDialog(frm) {
    if (!frm.doc.customer || !frm.doc.outlet || !frm.doc.posting_date) {
        frappe.msgprint(__("Please select Customer, Outlet, and Posting Date first."));
        return;
    }

    const dialog = new frappe.ui.Dialog({
        title: __("Select Sale Invoice"),
        size: "extra-large",
        fields: [
            {
                fieldname: "start_date",
                fieldtype: "Date",
                label: __("Start Date"),
                onchange: () => loadSaleInvoices(frm, dialog),
            },
            { fieldtype: "Column Break" },
            {
                fieldname: "end_date",
                fieldtype: "Date",
                label: __("End Date"),
                default: frm.doc.posting_date,
                onchange: () => loadSaleInvoices(frm, dialog),
            },
            { fieldtype: "Section Break" },
            {
                fieldname: "sale_invoices",
                fieldtype: "Table",
                label: __("Sale Invoices"),
                cannot_add_rows: true,
                cannot_delete_rows: true,
                in_place_edit: true,
                data: [],
                fields: [
                    { fieldname: "name", fieldtype: "Link", options: "Sale", label: __("Sale Invoice #"), in_list_view: 1, read_only: 1 },
                    { fieldname: "posting_date", fieldtype: "Date", label: __("Posting Date"), in_list_view: 1, read_only: 1 },
                    { fieldname: "total_amount", fieldtype: "Currency", label: __("Total Amount"), in_list_view: 1, read_only: 1 },
                    { fieldname: "total_payment", fieldtype: "Currency", label: __("Paid Amount"), in_list_view: 1, read_only: 1 },
                    { fieldname: "balance", fieldtype: "Currency", label: __("Balance"), in_list_view: 1, read_only: 1 },
                ],
            },
        ],
        primary_action_label: __("Add Selected"),
        async primary_action() {
            const selected = dialog.fields_dict.sale_invoices.grid.get_selected_children();

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one Sale Invoice."));
                return;
            }

            selected.forEach(sale => {
                const row = frm.add_child("sales");
                row.sale = sale.name;
                row.customer = frm.doc.customer;
                row.outlet = frm.doc.outlet;
                row.posting_date = sale.posting_date;
                row.total_amount = sale.total_amount;
                row.paid_amount = sale.total_payment;
                row.sale_balance = sale.balance;
                row.balance = sale.balance;
            });

            frm.refresh_field("sales");
            await callUpdateSummary(frm);
            dialog.hide();
        },
    });

    dialog.show();
    await loadSaleInvoices(frm, dialog);
}

async function loadSaleInvoices(frm, dialog) {
    const startDate = dialog.get_value("start_date");
    const endDate = dialog.get_value("end_date");

    if (startDate && endDate && startDate > endDate) {
        frappe.msgprint(__("Start Date cannot be after End Date."));
        return;
    }

    const selectedSales = (frm.doc.sales || [])
        .filter(row => row.sale)
        .map(row => row.sale);
    const filters = [
        ["Sale", "customer", "=", frm.doc.customer],
        ["Sale", "outlet", "=", frm.doc.outlet],
        ["Sale", "sale_status", "=", "Closed"],
        ["Sale", "status", "in", ["Unpaid", "Partially Paid"]],
        ["Sale", "balance", ">", 0],
        ["Sale", "posting_date", "<=", frm.doc.posting_date],
    ];

    if (startDate) {
        filters.push(["Sale", "posting_date", ">=", startDate]);
    }
    if (endDate) {
        filters.push(["Sale", "posting_date", "<=", endDate]);
    }
    if (selectedSales.length) {
        filters.push(["Sale", "name", "not in", selectedSales]);
    }

    const sales = await frappe.db.get_list("Sale", {
        fields: ["name", "posting_date", "total_amount", "total_payment", "balance"],
        filters,
        order_by: "posting_date",
        limit: 500,
    });
    const table = dialog.fields_dict.sale_invoices;
    table.df.data = sales;
    table.grid.refresh();
}


async function callUpdateSummary(frm) {
    await frm.call("update_summary");
    frm.refresh_fields();
    renderSalePaymentSummary(frm);
}

function updateChildSaleBalance(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    row.balance = flt(row.sale_balance) - flt(row.payment_amount) - flt(row.write_off_amount);
    frm.refresh_field("sales");
}

function hideSalesGridRowActions(frm) {
    const wrapper = frm.get_field("sales")?.$wrapper;
    if (!wrapper) return;

    wrapper.addClass("sales-grid-no-row-actions");

    if (!wrapper.children("style[data-sales-grid-actions]").length) {
        wrapper.prepend(`
            <style data-sales-grid-actions>
                .sales-grid-no-row-actions .btn-open-row,
                .sales-grid-no-row-actions .grid-edit-rows,
                .sales-grid-no-row-actions .grid-duplicate-row,
                .sales-grid-no-row-actions .grid-duplicate-rows {
                    display: none !important;
                }
            </style>
        `);
    }
}

function renderSalePaymentSummary(frm) {
    const field = frm.get_field("html_template_sale_payment_summary");
    if (field) {
        field.$wrapper.html(frappe.render_template("payment_summary", { doc: frm.doc }));
    }
}

function updateExchangeRateDisplay(frm) {
    const field = frm.get_field("exchange_rate_display");
    const exchangeRate = flt(frm.doc.exchange_rate);

    if (!field || exchangeRate <= 0 || exchangeRate === 1) {
        field?.$wrapper.empty().hide();
        return;
    }

    const displayRate = 1 / exchangeRate;


    field.$wrapper
        .html(`
            <div class="alert alert-info mb-2 d-flex justify-content-start align-items-center text-left" role="alert">
                <strong>${__("Exchange Rate")}:</strong>
                <span class="ml-1 text-left" style="text-align: left !important;">${frappe.format(displayRate, { fieldtype: "Currency" })}</span>
            </div>
        `)
        .show();
}

function getCustomerCreditBalance(frm){
    if(frm.doc.customer && frm.doc.posting_date && frm.doc.outlet){
         frm.call("get_customer_credit_balance")
    }else {
        frm.set_value("customer_balance", 0);
    }
}
