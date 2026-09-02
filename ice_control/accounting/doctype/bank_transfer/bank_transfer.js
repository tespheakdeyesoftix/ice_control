frappe.ui.form.on("Bank Transfer", {
    setup(frm) {
        set_transfer_from_query(frm);
        set_transfer_to_query(frm);
    },
    refresh(frm) {
        update_exchange_rate_display(frm);
        load_available_amount_to_transfer(frm);
        style_input_amount_field(frm);
    },
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
	outlet(frm) {
		set_transfer_from_query(frm);
		set_transfer_to_query(frm);
		load_available_amount_to_transfer(frm);
	},
	transfer_from(frm) {
		load_available_amount_to_transfer(frm);
	},
	posting_date(frm) {
		load_available_amount_to_transfer(frm);
	},
	transfer_type(frm) {
		set_transfer_from_query(frm);
		set_transfer_to_query(frm);
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
                render_available_amount_to_transfer(frm);
            },
        });
	},
    input_amount(frm){
        update_amount(frm)
    },
    exchange_rate(frm){
        update_amount(frm);
        update_exchange_rate_display(frm);
        render_available_amount_to_transfer(frm);
    }
});

function set_transfer_from_query(frm) {
    set_account_link_filters(frm, "transfer_from", ["Cash", "Bank"]);
}

function set_transfer_to_query(frm) {
    set_account_link_filters(
        frm,
        "transfer_to",
        ["Cash", "Bank", "Owner Withdraw"]
    );
}

function set_account_link_filters(frm, fieldname, default_account_types) {
    const bank_transfer = frm.doc.transfer_type === "Bank Transfer";
    const cash_transfer_from = fieldname === "transfer_from"
        && frm.doc.transfer_type === "Cash Transfer";
    const owner_withdrawal_to = fieldname === "transfer_to"
        && frm.doc.transfer_type === "Owner Withdrawal";
    let account_type_filter = [
        "Chart of Account",
        "account_type",
        "in",
        default_account_types
    ];

    if (bank_transfer) {
        account_type_filter = ["Chart of Account", "account_type", "IN", ["Bank","Cash"]];
    } else if (cash_transfer_from) {
        account_type_filter = ["Chart of Account", "account_type", "=", "Cash"];
    } else if (owner_withdrawal_to) {
        account_type_filter = [
            "Chart of Account",
            "account_type",
            "=",
            "Owner Withdraw"
        ];
    }

    const filters = [
        ["Chart of Account", "is_group", "=", 0],
        account_type_filter,
        ["Chart of Account", "outlet", "in", ["", frm.doc.outlet || ""]]
    ];

    frm.set_df_property(fieldname, "link_filters", JSON.stringify(filters));
}

function update_exchange_rate_display(frm) {
    const field = frm.get_field("html_exchange_rate_display");
    const exchange_rate = flt(frm.doc.exchange_rate);

    if (!field || exchange_rate <= 0 || exchange_rate === 1) {
        field?.$wrapper.empty().hide();
        return;
    }

    const display_rate = 1 / exchange_rate;

    field.$wrapper
        .html(`
            <div class="alert alert-info mb-2 d-flex justify-content-start align-items-center text-left" role="alert">
                <strong>${__("Exchange Rate")}:</strong>
                <span class="ml-1 text-left" style="text-align: left !important;">${frappe.format(display_rate, { fieldtype: "Currency" })}</span>
            </div>
        `)
        .show();
}

async function load_available_amount_to_transfer(frm) {
    const field = frm.get_field("html_available_amount_to_transfer");
    if (!field) return;

    if (frm.doc.docstatus !== 0) {
        await render_available_amount_to_transfer(frm);
        return;
    }

    const request_key = [
        frm.doc.transfer_from || "",
        frm.doc.outlet || "",
        frm.doc.posting_date || ""
    ].join("|");
    frm.__available_amount_request_key = request_key;

    if (!frm.doc.transfer_from) {
        await frm.set_value("available_amount_to_transfer", 0);
        field.$wrapper.empty().hide();
        return;
    }

    const response = await frappe.call({
        method: "ice_control.api.accounting.get_account_balance",
        args: {
            account_code: frm.doc.transfer_from,
            outlet: frm.doc.outlet || null,
            date: frm.doc.posting_date || null
        }
    });

    if (frm.__available_amount_request_key !== request_key) return;

    await frm.set_value(
        "available_amount_to_transfer",
        flt(response.message)
    );
    await render_available_amount_to_transfer(frm);
}

async function render_available_amount_to_transfer(frm) {
    const field = frm.get_field("html_available_amount_to_transfer");
    if (!field || !frm.doc.transfer_from) {
        field?.$wrapper.empty().hide();
        return;
    }

    const default_currency = await get_bank_transfer_default_currency(frm);
    const transfer_currency = frm.doc.currency || default_currency;
    const default_amount = flt(frm.doc.available_amount_to_transfer);
    const exchange_rate = flt(frm.doc.exchange_rate) || 1;
    const amounts = [{
        label: __("Available Amount to Transfer"),
        currency: default_currency,
        amount: default_amount,
        accent: "primary"
    }];

    if (transfer_currency && transfer_currency !== default_currency) {
        amounts.push({
            label: __("Amount in Transfer Currency"),
            currency: transfer_currency,
            amount: default_amount * exchange_rate,
            accent: "success"
        });
    }

    await Promise.all(amounts.map(async item => {
        item.precision = await get_bank_transfer_currency_precision(
            frm,
            item.currency
        );
    }));

    const column_class = amounts.length === 1 ? "col-12" : "col-md-6";
    const html = amounts.map(item => {
        const currency = frappe.utils.escape_html(item.currency || "");
        return `<div class="${column_class} mb-2">
            <div class="border rounded p-3 h-100 shadow-sm border-${item.accent}">
                <div class="small text-muted mb-1">${item.label}</div>
                <div class="d-flex align-items-center justify-content-between">
                    <strong class="h4 mb-0 text-${item.accent}">${format_currency(item.amount, item.currency, item.precision)}</strong>
                    <span class="badge badge-light">${currency}</span>
                </div>
            </div>
        </div>`;
    }).join("");

    field.$wrapper.html(`<div class="row">${html}</div>`).show();
}

async function get_bank_transfer_default_currency(frm) {
    if (!frm.__default_currency_promise) {
        frm.__default_currency_promise = frappe.db.get_single_value(
            "Business Information",
            "default_currency"
        );
    }
    return frm.__default_currency_promise;
}

async function get_bank_transfer_currency_precision(frm, currency) {
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

function style_input_amount_field(frm) {
    frm.get_field("input_amount")?.$wrapper.addClass(
        "sale-payment-input-amount-card"
    );
}

function update_amount(frm){
      frm.set_value("amount",frm.doc.input_amount/frm.doc.exchange_rate)
        frm.refresh_field('amount');
}
