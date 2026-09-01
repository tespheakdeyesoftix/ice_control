
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
         frm.__previous_customer = frm.doc.customer;
         frm.__previous_outlet = frm.doc.outlet;
         refreshSalePaymentIndicators(frm);
         updateExchangeRateDisplay(frm);
         renderSalePaymentSummary(frm);
         hideSalesGridRowActions(frm);
         setTimeout(() => {
            setupSalesRowIndicators(frm);
         }, 500);

         if (frm.is_new() && frm.doc.sale) {
            addSaleFromRoute(frm);
         }

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
         handleSaleContextChange(frm, "outlet")
      },
      customer(frm) {
         handleSaleContextChange(frm, "customer")
      },
      payment_type(frm) {
         frm.call("get_exchange_rate").then(() => {
            updateExchangeRateDisplay(frm)
            renderAmountToPayDisplay(frm)
         })
      },
      exchange_rate(frm) {
         updateExchangeRateDisplay(frm)
         renderAmountToPayDisplay(frm)
      },
      currency(frm) {
         renderAmountToPayDisplay(frm)
      },
      async input_amount(frm) {
         await callAllocatePaymentAmount(frm);
      },


})

async function addSaleFromRoute(frm) {
    const saleName = frm.doc.sale;
    if (!saleName || frm.__adding_route_sale === saleName) return;

    frm.doc.sales = (frm.doc.sales || []).filter(row => row.sale);
    if (frm.doc.sales.some(row => row.sale === saleName)) {
        frm.refresh_field("sales");
        return;
    }

    frm.__adding_route_sale = saleName;
    try {
        const result = await frappe.db.get_value("Sale", saleName, [
            "name",
            "customer",
            "outlet",
            "posting_date",
            "total_amount",
            "total_payment",
            "balance",
        ]);
        const sale = result.message;

        if (
            !sale?.name
            || !frm.is_new()
            || frm.doc.sale !== saleName
            || (frm.doc.sales || []).some(row => row.sale === saleName)
        ) {
            return;
        }

        const row = frm.add_child("sales");
        row.sale = sale.name;
        row.customer = sale.customer;
        row.outlet = sale.outlet;
        row.posting_date = sale.posting_date;
        row.total_amount = sale.total_amount;
        row.paid_amount = sale.total_payment;
        row.sale_balance = sale.balance;
        row.balance = sale.balance;

        frm.refresh_field("sales");
        await callAllocatePaymentAmount(frm);
    } finally {
        if (frm.__adding_route_sale === saleName) {
            frm.__adding_route_sale = null;
        }
    }
}

function refreshSalePaymentIndicators(frm) {
    const requestId = (frm.__sale_payment_indicator_request_id || 0) + 1;
    frm.__sale_payment_indicator_request_id = requestId;

    if (frm.doc.docstatus !== 1) return;
    frm.dashboard.clear_headline();
    addSalePaymentIndicators(frm, requestId);
}

async function addSalePaymentIndicators(frm, requestId) {
    const defaultCurrency = await getDefaultCurrency(frm);
    const precision = await getCurrencyPrecision(frm, defaultCurrency);

    if (
        frm.doc.docstatus !== 1
        || frm.__sale_payment_indicator_request_id !== requestId
    ) {
        return;
    }

    const formatAmount = value => format_currency(
        flt(value),
        defaultCurrency,
        precision
    );

    frm.dashboard.add_indicator(
        __("Amount to Pay") + ": " + formatAmount(frm.doc.amount_to_pay),
        "blue"
    );
    frm.dashboard.add_indicator(
        __("Payment Amount") + ": " + formatAmount(frm.doc.payment_amount),
        "green"
    );
    frm.dashboard.add_indicator(
        __("Write Off Amount") + ": " + formatAmount(frm.doc.write_off_amount),
        "red"
    );
    frm.dashboard.add_indicator(
        __("Balance") + ": " + formatAmount(frm.doc.balance),
        "blue"
    );
}

function handleSaleContextChange(frm, fieldname) {
    if (frm.__reverting_sale_context) return;

    const previousKey = fieldname === "customer"
        ? "__previous_customer"
        : "__previous_outlet";
    const previousValue = frm[previousKey];
    const currentValue = frm.doc[fieldname];
    const hasSelectedSales = (frm.doc.sales || []).some(row => row.sale);

    if (!hasSelectedSales || previousValue === currentValue) {
        frm[previousKey] = currentValue;
        getCustomerCreditBalance(frm);
        return;
    }

    const fieldLabel = fieldname === "customer" ? __("Customer") : __("Outlet");
    frappe.confirm(
        __("Changing {0} will clear all selected Sale Invoices. You must select the Sale Invoices again. Do you want to continue?", [fieldLabel]),
        async () => {
            frm[previousKey] = currentValue;
            frm.clear_table("sales");
            frm.refresh_field("sales");
            await callAllocatePaymentAmount(frm);
            getCustomerCreditBalance(frm);
        },
        async () => {
            frm.__reverting_sale_context = true;
            await frm.set_value(fieldname, previousValue);
            frm.__reverting_sale_context = false;
        }
    );
}

frappe.ui.form.on("Sale Payment Invoices", {
    sales_add(frm, cdt, cdn) {
        if (locals[cdt][cdn].sale) {
            scheduleAllocatePaymentAmount(frm);
        }
    },
    sales_remove(frm) {
        scheduleAllocationAfterRowRemoval(frm);
    },
    sale(frm) {
        frappe.after_ajax(() => callAllocatePaymentAmount(frm));
    },
    async payment_amount(frm, cdt, cdn) {
        if (frm.__syncing_manual_child_amounts) return;
        frm.__syncing_manual_child_amounts = true;
        try {
            updateChildSaleBalance(frm, cdt, cdn);
            await syncParentPaymentAmount(frm);
            await callUpdateSummary(frm);
        } finally {
            frm.__syncing_manual_child_amounts = false;
        }
    },
    async write_off_amount(frm, cdt, cdn) {
        if (frm.__syncing_manual_child_amounts) return;
        frm.__syncing_manual_child_amounts = true;
        try {
            const row = locals[cdt][cdn];
            const saleBalance = Math.max(flt(row.sale_balance), 0);
            const writeOffAmount = Math.min(
                Math.max(flt(row.write_off_amount), 0),
                saleBalance
            );

            row.write_off_amount = writeOffAmount;
            if (writeOffAmount > 0) {
                row.payment_amount = saleBalance - writeOffAmount;
                row.balance = 0;
            } else {
                updateChildSaleBalance(frm, cdt, cdn);
            }

            frm.refresh_field("sales");
            updateWriteOffPaymentLock(
                frm.get_field("sales")?.grid?.grid_rows_by_docname?.[cdn]
            );
            await syncParentPaymentAmount(frm);
            await callUpdateSummary(frm);
        } finally {
            frm.__syncing_manual_child_amounts = false;
        }
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
        primary_action_label: __("Add Selected Sale Invoice"),
        async primary_action() {
            const selected = dialog.fields_dict.sale_invoices.grid.get_selected_children();

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one Sale Invoice."));
                return;
            }

            frm.doc.sales = (frm.doc.sales || []).filter(row => row.sale);
            frm.doc.sales.forEach((row, index) => {
                row.idx = index + 1;
            });

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
            await callAllocatePaymentAmount(frm);
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


async function callAllocatePaymentAmount(frm) {
    clearTimeout(frm.__allocate_payment_timer);
    frm.__allocate_payment_timer = null;
    await frm.call("allocate_payment_amount");
    frm.refresh_fields();
    renderSalePaymentSummary(frm);
    ensureSalesGridObserver(frm);
    refreshSalesRowFormatting(frm);
    setTimeout(() => refreshSalesRowFormatting(frm), 300);
}

async function callUpdateSummary(frm) {
    clearTimeout(frm.__update_summary_timer);
    frm.__update_summary_timer = null;
    await frm.call("update_summary");
    frm.refresh_fields();
    renderSalePaymentSummary(frm);
    ensureSalesGridObserver(frm);
    refreshSalesRowFormatting(frm);
    setTimeout(() => refreshSalesRowFormatting(frm), 300);
}

function scheduleAllocatePaymentAmount(frm) {
    clearTimeout(frm.__allocate_payment_timer);
    frm.__allocate_payment_timer = setTimeout(() => {
        frm.__allocate_payment_timer = null;
        callAllocatePaymentAmount(frm);
    }, 150);
}

function scheduleAllocationAfterRowRemoval(frm) {
    clearTimeout(frm.__allocate_payment_timer);
    frm.__allocate_payment_timer = setTimeout(async () => {
        frm.__allocate_payment_timer = null;
        await syncParentPaymentAmount(frm);
        await callAllocatePaymentAmount(frm);
    }, 150);
}

function updateChildSaleBalance(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    row.balance = flt(row.sale_balance) - flt(row.payment_amount) - flt(row.write_off_amount);
    frm.refresh_field("sales");
}

async function syncParentPaymentAmount(frm) {
    const paymentAmount = (frm.doc.sales || []).reduce(
        (total, row) => total + flt(row.payment_amount),
        0
    );
    const defaultCurrency = await getDefaultCurrency(frm);
    const paymentCurrency = frm.doc.currency || defaultCurrency;
    const exchangeRate = flt(frm.doc.exchange_rate);

    if (!frm.doc.payment_type || !paymentCurrency) {
        frappe.throw(__("Please select a Payment Type before entering payment amounts."));
    }
    if (paymentCurrency !== defaultCurrency && exchangeRate <= 0) {
        frappe.throw(__("A valid Exchange Rate is required for {0}.", [paymentCurrency]));
    }

    frm.doc.payment_amount = paymentAmount;
    frm.doc.input_amount = paymentCurrency === defaultCurrency
        ? paymentAmount
        : paymentAmount * exchangeRate;
    frm.refresh_field("payment_amount");
    frm.refresh_field("input_amount");
    renderSalePaymentSummary(frm);
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
                .sales-grid-no-row-actions .grid-row[data-payment-status="paid"] {
                    border-left: 4px solid #28a745;
                }
                .sales-grid-no-row-actions .grid-row[data-payment-status="partial"] {
                    border-left: 4px solid #f0ad4e;
                }
                .sales-grid-no-row-actions .grid-row[data-payment-status="unpaid"] {
                    border-left: 4px solid #dc3545;
                }
                .sales-grid-no-row-actions .grid-row[data-has-write-off="true"]
                    .grid-static-col[data-fieldname="write_off_amount"],
                .sales-grid-no-row-actions .grid-row[data-has-write-off="true"]
                    .grid-static-col[data-fieldname="write_off_amount"] .static-area,
                .sales-grid-no-row-actions .grid-row[data-has-write-off="true"]
                    .grid-static-col[data-fieldname="write_off_amount"] input {
                    color: #dc3545 !important;
                    font-weight: 600;
                }
            </style>
        `);
    }
}

function setupSalesRowIndicators(frm) {
    if (!frm.__sales_row_indicator_bound) {
        frm.__sales_row_indicator_bound = true;
        $(frm.wrapper).on("grid-row-render.sale-payment-status", (event, gridRow) => {
            if (gridRow.grid?.df?.fieldname === "sales") {
                updateSalesRowIndicator(gridRow);
                updateWriteOffPaymentLock(gridRow);
            }
        });
    }

    ensureSalesGridObserver(frm);
    refreshSalesRowFormatting(frm);
    setTimeout(() => refreshSalesRowFormatting(frm), 300);
}

function ensureSalesGridObserver(frm) {
    const wrapper = frm.get_field("sales")?.$wrapper;
    if (frm.__sales_grid_observer || !wrapper?.[0]) return;

    frm.__sales_grid_observer = new MutationObserver(() => {
        clearTimeout(frm.__sales_grid_format_timer);
        frm.__sales_grid_format_timer = setTimeout(
            () => refreshSalesRowFormatting(frm),
            50
        );
    });
    frm.__sales_grid_observer.observe(wrapper[0], {
        childList: true,
        subtree: true,
    });
}

function refreshSalesRowFormatting(frm) {
    const grid = frm.get_field("sales")?.grid;
    (grid?.grid_rows || []).forEach(gridRow => {
        updateSalesRowIndicator(gridRow);
        updateWriteOffPaymentLock(gridRow);
    });
}

function updateSalesRowIndicator(gridRow) {
    const row = gridRow.doc;
    const saleBalance = flt(row.sale_balance);
    const allocatedAmount = flt(row.payment_amount) + flt(row.write_off_amount);
    const balance = flt(row.balance);
    let status = "unpaid";

    if (row.sale && saleBalance > 0 && balance <= 0) {
        status = "paid";
    } else if (row.sale && allocatedAmount > 0) {
        status = "partial";
    }

    gridRow.wrapper.attr("data-payment-status", row.sale ? status : null);
}

function updateWriteOffPaymentLock(gridRow) {
    if (!gridRow) return;
    const hasWriteOff = flt(gridRow.doc.write_off_amount) > 0;
    gridRow.wrapper.attr("data-has-write-off", hasWriteOff ? "true" : null);
    const paymentField = gridRow.on_grid_fields_dict?.payment_amount;
    if (paymentField && cint(paymentField.df.read_only) !== cint(hasWriteOff)) {
        gridRow.toggle_editable("payment_amount", !hasWriteOff);
    }
}

function renderSalePaymentSummary(frm) {
    const field = frm.get_field("html_template_sale_payment_summary");
    if (field) {
        field.$wrapper.html(frappe.render_template("payment_summary", { doc: frm.doc }));
    }
    renderAmountToPayDisplay(frm);
}

async function renderAmountToPayDisplay(frm) {
    const field = frm.get_field("html_amount_to_pay");
    if (!field) return;

    const defaultCurrency = await getDefaultCurrency(frm);
    const paymentCurrency = frm.doc.currency || defaultCurrency;
    const defaultAmount = flt(frm.doc.amount_to_pay);
    const exchangeRate = flt(frm.doc.exchange_rate) || 1;
    const amounts = [{
        label: __("Amount to Pay"),
        currency: defaultCurrency,
        amount: defaultAmount,
        accent: "primary",
    }];

    if (paymentCurrency && paymentCurrency !== defaultCurrency) {
        amounts.push({
            label: __("Amount in Payment Currency"),
            currency: paymentCurrency,
            amount: defaultAmount * exchangeRate,
            accent: "success",
        });
    }

    await Promise.all(amounts.map(async item => {
        item.precision = await getCurrencyPrecision(frm, item.currency);
    }));

    const columnClass = amounts.length === 1 ? "col-12" : "col-md-6";
    const html = amounts.map(item => {
        const currency = frappe.utils.escape_html(item.currency || "");
        return `<div class="${columnClass} mb-2">
            <div class="border rounded p-3 h-100 shadow-sm border-${item.accent}">
                <div class="small text-muted mb-1">${item.label}</div>
                <div class="d-flex align-items-center justify-content-between">
                    <strong class="h4 mb-0 text-${item.accent}">${format_currency(item.amount, item.currency, item.precision)}</strong>
                    <span class="badge badge-light">${currency}</span>
                </div>
            </div>
        </div>`;
    }).join("");

    field.$wrapper.html(`<div class="row">${html}</div>`);
}

async function getDefaultCurrency(frm) {
    if (!frm.__default_currency_promise) {
        frm.__default_currency_promise = frappe.db.get_single_value(
            "Business Information",
            "default_currency"
        );
    }
    return frm.__default_currency_promise;
}

async function getCurrencyPrecision(frm, currency) {
    if (!currency) return undefined;

    frm.__currency_precision_promises ||= {};
    if (!frm.__currency_precision_promises[currency]) {
        frm.__currency_precision_promises[currency] = frappe.db
            .get_value("Currency", currency, "custom_precision")
            .then(result => {
                const precision = result.message?.custom_precision;
                return precision === null || precision === undefined || precision === ""
                    ? undefined
                    : cint(precision);
            });
    }

    return frm.__currency_precision_promises[currency];
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
