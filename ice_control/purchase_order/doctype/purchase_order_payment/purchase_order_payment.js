// Copyright (c) 2025, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Order Payment", {
     async onload(frm) {
        rememberPurchaseOrderContextValues(frm);

        frm.set_query("purchase_order", "purchase_orders", function (doc, cdt, cdn) {
            const selectedPurchaseOrders = (doc.purchase_orders || [])
                .filter(row => row.name !== cdn && row.purchase_order)
                .map(row => row.purchase_order);

             let purchase_order_filter = {}
            if(frm.doc.outlet){
                purchase_order_filter = {
                    "party_type": doc.party_type || 'Not Set',
                    "party": doc.party || 'Not Set',
                    "outlet": doc.outlet || 'Not Set',
                    "balance": [">", 0],
                    "posting_date": ["<=", doc.posting_date],
                    "docstatus": 1
                };    
            }
            else{
                purchase_order_filter = {
                    "party_type": doc.party_type || 'Not Set',
                    "party": doc.party || 'Not Set',
                    "balance": [">", 0],
                    "posting_date": ["<=", doc.posting_date],
                    "docstatus": 1
                };    
            } 
            if (selectedPurchaseOrders.length) {
                purchase_order_filter.name = ["not in", selectedPurchaseOrders]
            }
            return {
                "filters": purchase_order_filter,
            };
        });

        await addPurchaseOrderFromRoute(frm);
    },
    posting_date(frm){
        confirmPurchaseOrderRemovalOnPostingDateChange(frm)
    },
	refresh(frm) {
		updateExchangeRateDisplay(frm)
        stylePurchaseOrderPaymentInputAmountField(frm)
        renderPurchaseOrderPaymentSummary(frm)
        hidePurchaseOrderGridDuplicateAction(frm)
        setTimeout(() => {
            setupPurchaseOrderRowIndicators(frm);
        }, 500);

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Select Purchase Order"), () => {
                openPurchaseOrderDialog(frm)
            })
        }
	},
    party_type(frm){
        frm.set_value("party", "");
        frm.refresh_field("party")
    },
    party(frm) {
        confirmPurchaseOrderClearOnContextChange(frm, "party")
    },
    outlet(frm) {
        get_payment_type_default_account(frm)
        confirmPurchaseOrderClearOnContextChange(frm, "outlet")
    },
    payment_type(frm) {
        get_payment_type_default_account(frm)
        frappe.call({
        method: 'ice_control.api.api.get_exchange_rate',
        args: {
            "currency": frm.doc.currency
        },
        callback: async (r) => {
            const paymentAmount = flt(frm.doc.payment_amount);
            await frm.set_value("exchange_rate", r.message);
            updateExchangeRateDisplay(frm)
            renderAmountToPayDisplay(frm)
            if ((frm.doc.input_amount || 0) > 0) {
                const exchangeRate = flt(frm.doc.exchange_rate) || 1;
                frm.doc.input_amount = paymentAmount * exchangeRate;
                frm.refresh_field("input_amount");
                await callAllocatePaymentAmount(frm);
            }
        }
        })
    },
    exchange_rate(frm) {
        updateExchangeRateDisplay(frm)
        renderAmountToPayDisplay(frm)
    },
    currency(frm) {
        renderAmountToPayDisplay(frm)
    },
    amount_to_pay(frm) {
        renderAmountToPayDisplay(frm)
    },
    async input_amount(frm) {
        if (!frm.doc.payment_type) {
            frappe.throw(__("Please select payment type"))
        }
        if (frm._from_set_value) return;
        await callAllocatePaymentAmount(frm);
    },
});

function rememberPurchaseOrderContextValues(frm) {
    frm.__purchase_order_context_values = {
        party: frm.doc.party || "",
        outlet: frm.doc.outlet || "",
        posting_date: frm.doc.posting_date || "",
    };
}

function confirmPurchaseOrderClearOnContextChange(frm, fieldname) {
    if (frm.__reverting_purchase_order_context) return;

    frm.__purchase_order_context_values ||= {};
    const previousValue = frm.__purchase_order_context_values[fieldname] || "";
    const currentValue = frm.doc[fieldname] || "";

    if (previousValue === currentValue) {
        getPartyAccountPayableBalance(frm);
        return;
    }

    const clearPurchaseOrders = () => {
        frm.__purchase_order_context_values[fieldname] = currentValue;
        frm.clear_table("purchase_orders");
        frm.refresh_field("purchase_orders");
        calculate_totals(frm);
        getPartyAccountPayableBalance(frm);
    };
    const hasPurchaseOrders = (frm.doc.purchase_orders || []).some(
        row => row.purchase_order
    );

    if (!hasPurchaseOrders) {
        clearPurchaseOrders();
        return;
    }

    const fieldLabel = frm.get_field(fieldname)?.df.label || fieldname;
    frappe.confirm(
        __("Changing {0} will clear the Purchase Orders table. Do you want to continue?", [__(fieldLabel)]),
        clearPurchaseOrders,
        () => {
            frm.__reverting_purchase_order_context = true;
            Promise.resolve(frm.set_value(fieldname, previousValue)).finally(() => {
                frm.__reverting_purchase_order_context = false;
            });
        }
    );
}

function confirmPurchaseOrderRemovalOnPostingDateChange(frm) {
    if (frm.__reverting_purchase_order_context) return;

    frm.__purchase_order_context_values ||= {};
    const previousValue = frm.__purchase_order_context_values.posting_date || "";
    const currentValue = frm.doc.posting_date || "";

    if (previousValue === currentValue) {
        getPartyAccountPayableBalance(frm);
        return;
    }

    const invalidPurchaseOrders = (frm.doc.purchase_orders || []).filter(row => (
        row.purchase_order
        && row.posting_date
        && currentValue
        && frappe.datetime.get_diff(row.posting_date, currentValue) > 0
    ));
    const applyPostingDateChange = async () => {
        frm.__purchase_order_context_values.posting_date = currentValue;

        invalidPurchaseOrders.forEach(row => {
            frappe.model.clear_doc(row.doctype, row.name);
        });
        if (invalidPurchaseOrders.length) {
            frm.dirty();
            frm.refresh_field("purchase_orders");
        }

        update_allocated_payment_date(frm);
        if (invalidPurchaseOrders.length && flt(frm.doc.input_amount) > 0) {
            await callAllocatePaymentAmount(frm);
        } else if (invalidPurchaseOrders.length) {
            calculate_totals(frm);
        }
        getPartyAccountPayableBalance(frm);
    };

    if (!invalidPurchaseOrders.length) {
        applyPostingDateChange();
        return;
    }

    frappe.confirm(
        __(
            "The new Posting Date is earlier than {0} Purchase Order(s). "
                + "Those rows will be removed from the Purchase Orders table. Do you want to continue?",
            [invalidPurchaseOrders.length]
        ),
        applyPostingDateChange,
        () => {
            frm.__reverting_purchase_order_context = true;
            Promise.resolve(frm.set_value("posting_date", previousValue)).finally(() => {
                frm.__reverting_purchase_order_context = false;
            });
        }
    );
}

async function addPurchaseOrderFromRoute(frm) {
    if (!frm.is_new() || frm.__purchase_order_route_prefill_started) return;

    const query = new URLSearchParams(window.location.search);
    const purchaseOrderName = query.get("purchase_order")
        || frappe.route_options?.purchase_order;

    if (!purchaseOrderName) return;
    frm.__purchase_order_route_prefill_started = true;

    const alreadyAdded = (frm.doc.purchase_orders || []).some(
        row => row.purchase_order === purchaseOrderName
    );
    if (alreadyAdded) return;

    const result = await frappe.db.get_value("Purchase Orders", purchaseOrderName, [
        "name",
        "docstatus",
        "posting_date",
        "party_type",
        "party",
        "outlet",
        "total_cost",
        "total_payment",
        "balance",
    ]);
    const purchaseOrder = result.message;

    if (!purchaseOrder?.name) {
        frappe.msgprint(__("Purchase Order {0} was not found.", [purchaseOrderName]));
        return;
    }
    if (cint(purchaseOrder.docstatus) !== 1) {
        frappe.msgprint(__("Purchase Order {0} must be submitted before payment.", [purchaseOrderName]));
        return;
    }

    await frm.set_value("party_type", purchaseOrder.party_type);
    await frm.set_value("outlet", purchaseOrder.outlet);
    await frm.set_value("party", purchaseOrder.party);

    const row = frm.add_child("purchase_orders");
    Object.assign(row, {
        purchase_order: purchaseOrder.name,
        party_type: purchaseOrder.party_type,
        party: purchaseOrder.party,
        outlet: purchaseOrder.outlet,
        payment_date: frm.doc.posting_date,
        posting_date: purchaseOrder.posting_date,
        purchase_amount: purchaseOrder.total_cost,
        paid_amount: purchaseOrder.total_payment,
        purchase_order_balance: purchaseOrder.balance,
        balance: purchaseOrder.balance,
        exchange_rate: frm.doc.exchange_rate,
    });

    frm.refresh_field("purchase_orders");
    calculate_totals(frm);
    getPartyAccountPayableBalance(frm);
}

async function openPurchaseOrderDialog(frm) {
    if (!frm.doc.posting_date || !frm.doc.outlet || !frm.doc.party_type || !frm.doc.party) {
        frappe.msgprint(__("Please select Posting Date, Outlet, Party Type, and Party first."));
        return;
    }

    const dialog = new frappe.ui.Dialog({
        title: __("Select Purchase Order"),
        size: "extra-large",
        fields: [
            {
                fieldname: "start_date",
                fieldtype: "Date",
                label: __("Start Date"),
                onchange: () => loadPurchaseOrders(frm, dialog),
            },
            { fieldtype: "Column Break" },
            {
                fieldname: "end_date",
                fieldtype: "Date",
                label: __("End Date"),
                default: frm.doc.posting_date,
                onchange: () => loadPurchaseOrders(frm, dialog),
            },
            { fieldtype: "Section Break" },
            {
                fieldname: "purchase_orders",
                fieldtype: "Table",
                label: __("Purchase Orders"),
                cannot_add_rows: true,
                cannot_delete_rows: true,
                in_place_edit: true,
                data: [],
                fields: [
                    { fieldname: "name", fieldtype: "Link", options: "Purchase Orders", label: __("Purchase Order #"), in_list_view: 1, read_only: 1 },
                    { fieldname: "posting_date", fieldtype: "Date", label: __("Posting Date"), in_list_view: 1, read_only: 1 },
                    { fieldname: "total_cost", fieldtype: "Currency", label: __("Total Cost"), in_list_view: 1, read_only: 1 },
                    { fieldname: "total_payment", fieldtype: "Currency", label: __("Paid Amount"), in_list_view: 1, read_only: 1 },
                    { fieldname: "balance", fieldtype: "Currency", label: __("Balance"), in_list_view: 1, read_only: 1 },
                ],
            },
        ],
        primary_action_label: __("Add Selected Purchase Order"),
        async primary_action() {
            const selected = dialog.fields_dict.purchase_orders.grid.get_selected_children();

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one Purchase Order."));
                return;
            }

            frm.doc.purchase_orders = (frm.doc.purchase_orders || []).filter(row => row.purchase_order);
            frm.doc.purchase_orders.forEach((row, index) => {
                row.idx = index + 1;
            });

            selected.forEach(purchaseOrder => {
                const row = frm.add_child("purchase_orders");
                row.purchase_order = purchaseOrder.name;
                row.party_type = frm.doc.party_type;
                row.party = frm.doc.party;
                row.outlet = frm.doc.outlet;
                row.payment_date = frm.doc.posting_date;
                row.posting_date = purchaseOrder.posting_date;
                row.purchase_amount = purchaseOrder.total_cost;
                row.paid_amount = purchaseOrder.total_payment;
                row.purchase_order_balance = purchaseOrder.balance;
                row.balance = purchaseOrder.balance;
                row.exchange_rate = frm.doc.exchange_rate;
            });

            frm.refresh_field("purchase_orders");
            if ((frm.doc.input_amount || 0) > 0) {
                await callAllocatePaymentAmount(frm);
            } else {
                calculate_totals(frm);
            }
            dialog.hide();
        },
    });

    dialog.show();
    await loadPurchaseOrders(frm, dialog);
}

async function loadPurchaseOrders(frm, dialog) {
    const startDate = dialog.get_value("start_date");
    const endDate = dialog.get_value("end_date");

    if (startDate && endDate && startDate > endDate) {
        frappe.msgprint(__("Start Date cannot be after End Date."));
        return;
    }

    const selectedPurchaseOrders = (frm.doc.purchase_orders || [])
        .filter(row => row.purchase_order)
        .map(row => row.purchase_order);
    const filters = [
        ["Purchase Orders", "docstatus", "=", 1],
        ["Purchase Orders", "party_type", "=", frm.doc.party_type],
        ["Purchase Orders", "party", "=", frm.doc.party],
        ["Purchase Orders", "outlet", "=", frm.doc.outlet],
        ["Purchase Orders", "posting_date", "<=", frm.doc.posting_date],
        ["Purchase Orders", "balance", ">", 0],
    ];

    if (startDate) {
        filters.push(["Purchase Orders", "posting_date", ">=", startDate]);
    }
    if (endDate) {
        filters.push(["Purchase Orders", "posting_date", "<=", endDate]);
    }
    if (selectedPurchaseOrders.length) {
        filters.push(["Purchase Orders", "name", "not in", selectedPurchaseOrders]);
    }

    const purchaseOrders = await frappe.db.get_list("Purchase Orders", {
        fields: ["name", "posting_date", "total_cost", "total_payment", "balance"],
        filters,
        order_by: "posting_date",
        limit: 500,
    });
    const table = dialog.fields_dict.purchase_orders;
    table.df.data = purchaseOrders;
    table.grid.refresh();
}

///child table in purchase order payment
frappe.ui.form.on("Purchase Order Payment Invoices", {
    pay(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        frappe.model.set_value(
            cdt,
            cdn,
            "payment_amount",
            row.purchase_order_balance || 0
        );
    },
    purchase_orders_add(frm, cdt, cdn) {
        if (locals[cdt][cdn].purchase_order) {
            scheduleAllocatePaymentAmount(frm);
        }
    },
    purchase_orders_remove(frm) {
        scheduleAllocationAfterRowRemoval(frm);
    },
    purchase_order(frm) {
        frappe.after_ajax(() => callAllocatePaymentAmount(frm));
    },
    async payment_amount(frm, cdt, cdn) {
        if (frm.__syncing_manual_child_amounts) return;
        frm.__syncing_manual_child_amounts = true;
        try {
            updateChildPurchaseOrderBalance(frm, cdt, cdn);
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
            const purchaseOrderBalance = Math.max(
                flt(row.purchase_order_balance),
                0
            );
            const writeOffAmount = Math.min(
                Math.max(flt(row.write_off_amount), 0),
                purchaseOrderBalance
            );

            row.write_off_amount = writeOffAmount;
            if (writeOffAmount > 0) {
                row.payment_amount = purchaseOrderBalance - writeOffAmount;
                row.balance = 0;
            } else {
                updateChildPurchaseOrderBalance(frm, cdt, cdn);
            }

            frm.refresh_field("purchase_orders");
            updatePurchaseOrderWriteOffPaymentLock(
                frm.get_field("purchase_orders")?.grid?.grid_rows_by_docname?.[cdn]
            );
            await syncParentPaymentAmount(frm);
            await callUpdateSummary(frm);
        } finally {
            frm.__syncing_manual_child_amounts = false;
        }
    },
});

function calculate_totals(frm) {
    const total_amount_to_pay = frm.doc.purchase_orders.reduce((sum, s) => sum + (s.purchase_order_balance || 0), 0);
    const total_write_off_amount = frm.doc.purchase_orders.reduce((sum, s) => sum + (s.write_off_amount || 0), 0);
    const payment_amount = frm.doc.purchase_orders.reduce((sum, s) => sum + (s.payment_amount || 0), 0);
    const total_invoices = frm.doc.purchase_orders.filter(r => r.purchase_order).length;
    const balance = total_amount_to_pay - (payment_amount + total_write_off_amount)
    frm.set_value("payment_amount", payment_amount);
    frm.set_value("total_invoices", total_invoices);
    frm.set_value("amount_to_pay", total_amount_to_pay);
    frm.set_value("total_write_off_amount", total_write_off_amount);
    frm.set_value("balance", balance);
    renderPurchaseOrderPaymentSummary(frm);
}

function get_unpaid_purchase_orders(frm) {
    if (!frm.doc.party) {
        frm.clear_table("purchase_orders");
        frm.refresh_field("purchase_orders");
        return;
    };
    if (!frm.doc.outlet) return;
    return new Promise((resolve, reject) => {
    frm.call({
        method: "get_unpaid_purchase_orders",
        doc: frm.doc,  
        freeze: true,
        }).then(r => {
            frm.clear_table("purchase_orders");
            (r.message || []).forEach(row => {
                let d = frm.add_child("purchase_orders");
                d.purchase_order = row.name;
                d.outlet = row.outlet;
                d.party_type = row.party_type;
                d.party = row.party;
                d.payment_date = frm.doc.posting_date;
                d.posting_date = row.posting_date;
                d.purchase_order_balance = row.balance;
                d.balance = row.balance;
                d.exchange_rate = frm.doc.exchange_rate
            });
            frm.refresh_field("purchase_orders");
            resolve(r.message || []);
        })
        .catch(err => {
            frm.clear_table("purchase_orders");
            frm.refresh_field("purchase_orders");
            reject(err);
        });
    });
}

function renderPurchaseOrderPaymentSummary(frm) {
    const field = frm.get_field("html_payment_summary");
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
    const field = frm.get_field("html_exchange_rate_display");
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

function stylePurchaseOrderPaymentInputAmountField(frm) {
    frm.get_field("input_amount")?.$wrapper.addClass(
        "sale-payment-input-amount-card"
    );
}

function hidePurchaseOrderGridDuplicateAction(frm) {
    const wrapper = frm.get_field("purchase_orders")?.$wrapper;
    if (!wrapper) return;

    wrapper.addClass("purchase-orders-grid-no-duplicate");

    if (!wrapper.children("style[data-purchase-orders-grid-actions]").length) {
        wrapper.prepend(`
            <style data-purchase-orders-grid-actions>
                .purchase-orders-grid-no-duplicate .grid-duplicate-row,
                .purchase-orders-grid-no-duplicate .grid-duplicate-rows {
                    display: none !important;
                }
                .purchase-orders-grid-no-duplicate .grid-row[data-payment-status="paid"] {
                    border-left: 4px solid #28a745;
                }
                .purchase-orders-grid-no-duplicate .grid-row[data-payment-status="partial"] {
                    border-left: 4px solid #f0ad4e;
                }
                .purchase-orders-grid-no-duplicate .grid-row[data-payment-status="unpaid"] {
                    border-left: 4px solid #dc3545;
                }
                .purchase-orders-grid-no-duplicate .grid-row[data-has-write-off="true"]
                    .grid-static-col[data-fieldname="write_off_amount"],
                .purchase-orders-grid-no-duplicate .grid-row[data-has-write-off="true"]
                    .grid-static-col[data-fieldname="write_off_amount"] .static-area,
                .purchase-orders-grid-no-duplicate .grid-row[data-has-write-off="true"]
                    .grid-static-col[data-fieldname="write_off_amount"] input {
                    color: #dc3545 !important;
                    font-weight: 600;
                }
            </style>
        `);
    }
}

function getPartyAccountPayableBalance(frm) {
    if (frm.doc.party_type && frm.doc.party && frm.doc.outlet && frm.doc.posting_date) {
        frm.call("get_party_account_payable_balance")
    } else {
        frm.set_value("party_payable_balance", 0);
    }
}

async function callAllocatePaymentAmount(frm) {
    clearTimeout(frm.__allocate_payment_timer);
    frm.__allocate_payment_timer = null;
    await frm.call("allocate_payment_amount");
    frm.refresh_fields();
    renderPurchaseOrderPaymentSummary(frm);
    ensurePurchaseOrderGridObserver(frm);
    refreshPurchaseOrderRowFormatting(frm);
    setTimeout(() => refreshPurchaseOrderRowFormatting(frm), 300);
}

async function callUpdateSummary(frm) {
    clearTimeout(frm.__update_summary_timer);
    frm.__update_summary_timer = null;
    await frm.call("update_summary");
    frm.refresh_fields();
    renderPurchaseOrderPaymentSummary(frm);
    ensurePurchaseOrderGridObserver(frm);
    refreshPurchaseOrderRowFormatting(frm);
    setTimeout(() => refreshPurchaseOrderRowFormatting(frm), 300);
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

function updateChildPurchaseOrderBalance(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    row.balance = flt(row.purchase_order_balance)
        - flt(row.payment_amount)
        - flt(row.write_off_amount);
    frm.refresh_field("purchase_orders");
}

async function syncParentPaymentAmount(frm) {
    const paymentAmount = (frm.doc.purchase_orders || []).reduce(
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
    renderPurchaseOrderPaymentSummary(frm);
}

function setupPurchaseOrderRowIndicators(frm) {
    if (!frm.__purchase_order_row_indicator_bound) {
        frm.__purchase_order_row_indicator_bound = true;
        $(frm.wrapper).on("grid-row-render.purchase-order-payment-status", (event, gridRow) => {
            if (gridRow.grid?.df?.fieldname === "purchase_orders") {
                updatePurchaseOrderRowIndicator(gridRow);
                updatePurchaseOrderWriteOffPaymentLock(gridRow);
            }
        });
    }

    ensurePurchaseOrderGridObserver(frm);
    refreshPurchaseOrderRowFormatting(frm);
    setTimeout(() => refreshPurchaseOrderRowFormatting(frm), 300);
}

function ensurePurchaseOrderGridObserver(frm) {
    const wrapper = frm.get_field("purchase_orders")?.$wrapper;
    if (frm.__purchase_order_grid_observer || !wrapper?.[0]) return;

    frm.__purchase_order_grid_observer = new MutationObserver(() => {
        clearTimeout(frm.__purchase_order_grid_format_timer);
        frm.__purchase_order_grid_format_timer = setTimeout(
            () => refreshPurchaseOrderRowFormatting(frm),
            50
        );
    });
    frm.__purchase_order_grid_observer.observe(wrapper[0], {
        childList: true,
        subtree: true,
    });
}

function refreshPurchaseOrderRowFormatting(frm) {
    const grid = frm.get_field("purchase_orders")?.grid;
    (grid?.grid_rows || []).forEach(gridRow => {
        updatePurchaseOrderRowIndicator(gridRow);
        updatePurchaseOrderWriteOffPaymentLock(gridRow);
    });
}

function updatePurchaseOrderRowIndicator(gridRow) {
    const row = gridRow.doc;
    const purchaseOrderBalance = flt(row.purchase_order_balance);
    const allocatedAmount = flt(row.payment_amount) + flt(row.write_off_amount);
    const balance = flt(row.balance);
    let status = "unpaid";

    if (row.purchase_order && purchaseOrderBalance > 0 && balance <= 0) {
        status = "paid";
    } else if (row.purchase_order && allocatedAmount > 0) {
        status = "partial";
    }

    gridRow.wrapper.attr("data-payment-status", row.purchase_order ? status : null);
}

function updatePurchaseOrderWriteOffPaymentLock(gridRow) {
    if (!gridRow) return;
    const hasWriteOff = flt(gridRow.doc.write_off_amount) > 0;
    gridRow.wrapper.attr("data-has-write-off", hasWriteOff ? "true" : null);
    const paymentField = gridRow.on_grid_fields_dict?.payment_amount;
    if (paymentField && cint(paymentField.df.read_only) !== cint(hasWriteOff)) {
        gridRow.toggle_editable("payment_amount", !hasWriteOff);
    }
}

function update_allocated_payment_date(frm) {
    if ((frm.doc.purchase_orders || []).length > 0) {
        frm.doc.purchase_orders.forEach(r => {
            r.payment_date = frm.doc.posting_date;
        });
        frm.refresh_field("purchase_orders");
    }
}

async function get_payment_type_default_account(frm){
    if(frm.doc.payment_type && frm.doc.outlet){
        frappe.call({
            method: 'ice_control.api.api.get_payment_type_default_account',
            args: {
                "payment_type": frm.doc.payment_type,
                "outlet": frm.doc.outlet
            },
            callback: (r) => {
                frm.set_value("account_paid_from", r.message.default_account);
                frm.refresh_field("purchase_products");
            }
        })
    }
}