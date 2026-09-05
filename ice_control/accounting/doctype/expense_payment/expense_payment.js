// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Expense Payment", {
	async onload(frm) {
		rememberExpensePaymentContextValues(frm);

		frm.set_query("expense", "expenses", (doc, cdt, cdn) => {
			const selectedExpenses = (doc.expenses || [])
				.filter(row => row.name !== cdn && row.expense)
				.map(row => row.expense);
			const filters = {
				outlet: doc.outlet || "Not Set",
				vendor: doc.vendor || "Not Set",
				balance: [">", 0],
				posting_date: ["<=", doc.posting_date],
				docstatus: 1,
			};

			if (selectedExpenses.length) {
				filters.name = ["not in", selectedExpenses];
			}

			return { filters };
		});

		await addExpenseFromRoute(frm);
	},

	posting_date(frm) {
		confirmExpenseRemovalOnPostingDateChange(frm);
	},

	refresh(frm) {
		updateExchangeRateDisplay(frm);
		styleExpensePaymentInputAmountField(frm);
		renderExpensePaymentSummary(frm);
		hideExpenseGridDuplicateAction(frm);
		setTimeout(() => setupExpenseRowIndicators(frm), 500);

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Select Expense"), () => {
				openExpenseDialog(frm);
			});
		}
	},

	vendor(frm) {
		confirmExpenseClearOnContextChange(frm, "vendor");
	},

	outlet(frm) {
		getPaymentTypeDefaultAccount(frm);
		confirmExpenseClearOnContextChange(frm, "outlet");
	},

	async payment_type(frm) {
		await Promise.all([
			getPaymentTypeDefaultAccount(frm),
			updateExchangeRateFromPaymentType(frm),
		]);
	},

	exchange_rate(frm) {
		updateExchangeRateDisplay(frm);
		renderAmountToPayDisplay(frm);
	},

	currency(frm) {
		renderAmountToPayDisplay(frm);
	},

	amount_to_pay(frm) {
		renderAmountToPayDisplay(frm);
	},

	async input_amount(frm) {
		if (!frm.doc.payment_type) {
			frappe.throw(__("Please select Payment Type."));
		}
		await callAllocatePaymentAmount(frm);
	},
});

function rememberExpensePaymentContextValues(frm) {
	frm.__expense_payment_context_values = {
		vendor: frm.doc.vendor || "",
		outlet: frm.doc.outlet || "",
		posting_date: frm.doc.posting_date || "",
	};
}

function confirmExpenseClearOnContextChange(frm, fieldname) {
	if (frm.__reverting_expense_payment_context) return;

	frm.__expense_payment_context_values ||= {};
	const previousValue = frm.__expense_payment_context_values[fieldname] || "";
	const currentValue = frm.doc[fieldname] || "";

	if (previousValue === currentValue) {
		getVendorExpenseBalance(frm);
		return;
	}

	const clearExpenses = () => {
		frm.__expense_payment_context_values[fieldname] = currentValue;
		frm.clear_table("expenses");
		frm.doc.input_amount = 0;
		frm.refresh_field("expenses");
		frm.refresh_field("input_amount");
		calculateExpenseTotals(frm);
		getVendorExpenseBalance(frm);
	};
	const hasExpenses = (frm.doc.expenses || []).some(row => row.expense);

	if (!hasExpenses) {
		clearExpenses();
		return;
	}

	const fieldLabel = frm.get_field(fieldname)?.df.label || fieldname;
	frappe.confirm(
		__("Changing {0} will clear the Expenses table. Do you want to continue?", [
			__(fieldLabel),
		]),
		clearExpenses,
		() => {
			frm.__reverting_expense_payment_context = true;
			Promise.resolve(frm.set_value(fieldname, previousValue)).finally(() => {
				frm.__reverting_expense_payment_context = false;
			});
		}
	);
}

function confirmExpenseRemovalOnPostingDateChange(frm) {
	if (frm.__reverting_expense_payment_context) return;

	frm.__expense_payment_context_values ||= {};
	const previousValue = frm.__expense_payment_context_values.posting_date || "";
	const currentValue = frm.doc.posting_date || "";

	if (previousValue === currentValue) {
		getVendorExpenseBalance(frm);
		return;
	}

	const invalidExpenses = (frm.doc.expenses || []).filter(row => (
		row.expense
		&& row.expense_date
		&& currentValue
		&& frappe.datetime.get_diff(row.expense_date, currentValue) > 0
	));
	const applyPostingDateChange = async () => {
		frm.__expense_payment_context_values.posting_date = currentValue;

		invalidExpenses.forEach(row => {
			frappe.model.clear_doc(row.doctype, row.name);
		});
		if (invalidExpenses.length) {
			frm.dirty();
			frm.refresh_field("expenses");
		}

		if (invalidExpenses.length && flt(frm.doc.input_amount) > 0) {
			await callAllocatePaymentAmount(frm);
		} else if (invalidExpenses.length) {
			calculateExpenseTotals(frm);
		}
		getVendorExpenseBalance(frm);
	};

	if (!invalidExpenses.length) {
		applyPostingDateChange();
		return;
	}

	frappe.confirm(
		__(
			"The new Posting Date is earlier than {0} Expense(s). "
				+ "Those rows will be removed from the Expenses table. Do you want to continue?",
			[invalidExpenses.length]
		),
		applyPostingDateChange,
		() => {
			frm.__reverting_expense_payment_context = true;
			Promise.resolve(frm.set_value("posting_date", previousValue)).finally(() => {
				frm.__reverting_expense_payment_context = false;
			});
		}
	);
}

async function addExpenseFromRoute(frm) {
	if (!frm.is_new()) return;

	const query = frappe.utils.get_query_params();
	const routeOptions = {
		...(frappe.route_options || {}),
		...query,
	};
	const expenseName = routeOptions.expense;

	if (!expenseName || frm.__expense_route_prefill_started === expenseName) return;
	frm.__expense_route_prefill_started = expenseName;

	try {
		const alreadyAdded = (frm.doc.expenses || []).some(
			row => row.expense === expenseName
		);
		if (alreadyAdded) {
			calculateExpenseTotals(frm);
			return;
		}

		const result = await frappe.db.get_value("Expense", expenseName, [
			"name",
			"docstatus",
			"posting_date",
			"vendor",
			"outlet",
			"total_expense",
			"total_payment",
			"total_write_off",
			"balance",
		]);
		const expense = result.message;

		if (!expense?.name) {
			frappe.msgprint(__("Expense {0} was not found.", [expenseName]));
			return;
		}
		if (cint(expense.docstatus) !== 1) {
			frappe.msgprint(__("Expense {0} must be submitted before payment.", [expenseName]));
			return;
		}
		if (flt(expense.balance) <= 0) {
			frappe.msgprint(__("Expense {0} has no outstanding balance.", [expenseName]));
			return;
		}

		await frm.set_value("outlet", expense.outlet || routeOptions.outlet || "");
		await frm.set_value("vendor", expense.vendor || routeOptions.vendor || "");

		addExpenseRow(frm, expense);
		frm.refresh_field("expenses");
		calculateExpenseTotals(frm);
		getVendorExpenseBalance(frm);
	} finally {
		if (frm.__expense_route_prefill_started === expenseName) {
			frm.__expense_route_prefill_started = null;
		}
	}
}

function addExpenseRow(frm, expense) {
	const row = frm.add_child("expenses");
	Object.assign(row, {
		expense: expense.name,
		expense_date: expense.posting_date,
		expense_amount: expense.total_expense,
		paid_amount: expense.total_payment,
		expense_balance: expense.balance,
		balance: expense.balance,
	});
	return row;
}

async function openExpenseDialog(frm) {
	if (!frm.doc.posting_date || !frm.doc.outlet || !frm.doc.vendor) {
		frappe.msgprint(__("Please select Posting Date, Outlet, and Vendor first."));
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Select Expense"),
		size: "extra-large",
		fields: [
			{
				fieldname: "start_date",
				fieldtype: "Date",
				label: __("Start Date"),
				onchange: () => loadExpenses(frm, dialog),
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "end_date",
				fieldtype: "Date",
				label: __("End Date"),
				default: frm.doc.posting_date,
				onchange: () => loadExpenses(frm, dialog),
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "expenses",
				fieldtype: "Table",
				label: __("Expenses"),
				cannot_add_rows: true,
				cannot_delete_rows: true,
				in_place_edit: true,
				data: [],
				fields: [
					{ fieldname: "name", fieldtype: "Link", options: "Expense", label: __("Expense #"), in_list_view: 1, read_only: 1 },
					{ fieldname: "posting_date", fieldtype: "Date", label: __("Posting Date"), in_list_view: 1, read_only: 1 },
					{ fieldname: "total_expense", fieldtype: "Currency", label: __("Total Expense"), in_list_view: 1, read_only: 1 },
					{ fieldname: "total_payment", fieldtype: "Currency", label: __("Paid Amount"), in_list_view: 1, read_only: 1 },
					{ fieldname: "total_write_off", fieldtype: "Currency", label: __("Write Off"), in_list_view: 1, read_only: 1 },
					{ fieldname: "balance", fieldtype: "Currency", label: __("Balance"), in_list_view: 1, read_only: 1 },
				],
			},
		],
		primary_action_label: __("Add Selected Expense"),
		async primary_action() {
			const selected = dialog.fields_dict.expenses.grid.get_selected_children();

			if (!selected.length) {
				frappe.msgprint(__("Please select at least one Expense."));
				return;
			}

			frm.doc.expenses = (frm.doc.expenses || []).filter(row => row.expense);
			frm.doc.expenses.forEach((row, index) => {
				row.idx = index + 1;
			});

			selected.forEach(expense => addExpenseRow(frm, expense));
			frm.refresh_field("expenses");

			if (flt(frm.doc.input_amount) > 0) {
				await callAllocatePaymentAmount(frm);
			} else {
				calculateExpenseTotals(frm);
			}
			dialog.hide();
		},
	});

	dialog.show();
	await loadExpenses(frm, dialog);
}

async function loadExpenses(frm, dialog) {
	const startDate = dialog.get_value("start_date");
	const endDate = dialog.get_value("end_date");

	if (startDate && endDate && startDate > endDate) {
		frappe.msgprint(__("Start Date cannot be after End Date."));
		return;
	}

	const selectedExpenses = (frm.doc.expenses || [])
		.filter(row => row.expense)
		.map(row => row.expense);
	const filters = [
		["Expense", "docstatus", "=", 1],
		["Expense", "vendor", "=", frm.doc.vendor],
		["Expense", "outlet", "=", frm.doc.outlet],
		["Expense", "posting_date", "<=", frm.doc.posting_date],
		["Expense", "balance", ">", 0],
	];

	if (startDate) {
		filters.push(["Expense", "posting_date", ">=", startDate]);
	}
	if (endDate) {
		filters.push(["Expense", "posting_date", "<=", endDate]);
	}
	if (selectedExpenses.length) {
		filters.push(["Expense", "name", "not in", selectedExpenses]);
	}

	const expenses = await frappe.db.get_list("Expense", {
		fields: [
			"name",
			"posting_date",
			"total_expense",
			"total_payment",
			"total_write_off",
			"balance",
		],
		filters,
		order_by: "posting_date, name",
		limit: 500,
	});
	const table = dialog.fields_dict.expenses;
	table.df.data = expenses;
	table.grid.refresh();
}

frappe.ui.form.on("Expense Payment Invoices", {
	expenses_add(frm, cdt, cdn) {
		if (locals[cdt][cdn].expense) {
			scheduleAllocatePaymentAmount(frm);
		}
	},

	expenses_remove(frm) {
		scheduleAllocationAfterRowRemoval(frm);
	},

	expense(frm) {
		frappe.after_ajax(() => callAllocatePaymentAmount(frm));
	},

	async payment_amount(frm, cdt, cdn) {
		if (frm.__syncing_manual_expense_amounts) return;
		frm.__syncing_manual_expense_amounts = true;
		try {
			updateChildExpenseBalance(frm, cdt, cdn);
			await syncParentPaymentAmount(frm);
			await callUpdateExpenseRecord(frm);
		} finally {
			frm.__syncing_manual_expense_amounts = false;
		}
	},

	async write_off_amount(frm, cdt, cdn) {
		if (frm.__syncing_manual_expense_amounts) return;
		frm.__syncing_manual_expense_amounts = true;
		try {
			const row = locals[cdt][cdn];
			const expenseBalance = Math.max(flt(row.expense_balance), 0);
			const writeOffAmount = Math.min(
				Math.max(flt(row.write_off_amount), 0),
				expenseBalance
			);

			row.write_off_amount = writeOffAmount;
			if (writeOffAmount > 0) {
				row.payment_amount = expenseBalance - writeOffAmount;
				row.balance = 0;
			} else {
				updateChildExpenseBalance(frm, cdt, cdn);
			}

			frm.refresh_field("expenses");
			updateExpenseWriteOffPaymentLock(
				frm.get_field("expenses")?.grid?.grid_rows_by_docname?.[cdn]
			);
			await syncParentPaymentAmount(frm);
			await callUpdateExpenseRecord(frm);
		} finally {
			frm.__syncing_manual_expense_amounts = false;
		}
	},
});

function calculateExpenseTotals(frm) {
	const expenses = (frm.doc.expenses || []).filter(row => row.expense);
	frm.doc.amount_to_pay = expenses.reduce(
		(total, row) => total + flt(row.expense_balance),
		0
	);
	frm.doc.total_payment = expenses.reduce(
		(total, row) => total + flt(row.payment_amount),
		0
	);
	frm.doc.total_write_off = expenses.reduce(
		(total, row) => total + flt(row.write_off_amount),
		0
	);
	frm.doc.balance = frm.doc.amount_to_pay
		- frm.doc.total_payment
		- frm.doc.total_write_off;
	frm.refresh_field("amount_to_pay");
	frm.refresh_field("total_payment");
	frm.refresh_field("total_write_off");
	frm.refresh_field("balance");
	renderExpensePaymentSummary(frm);
}

function renderExpensePaymentSummary(frm) {
	const field = frm.get_field("html_payment_summary");
	if (field) {
		const expenseCount = (frm.doc.expenses || []).filter(row => row.expense).length;
		field.$wrapper.html(frappe.render_template("expense_summary", {
			doc: frm.doc,
			expense_count: expenseCount,
		}));
	}
	renderAmountToPayDisplay(frm);
}

async function renderAmountToPayDisplay(frm) {
	const field = frm.get_field("html_amount_to_pay_display");
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

async function updateExchangeRateFromPaymentType(frm) {
	const paymentType = frm.doc.payment_type;

	if (!paymentType) {
		await frm.set_value({ currency: "", exchange_rate: 0, account_code: "" });
		updateExchangeRateDisplay(frm);
		renderAmountToPayDisplay(frm);
		return;
	}

	const paymentTypeResult = await frappe.db.get_value(
		"Payment Type",
		paymentType,
		"currency"
	);
	if (frm.doc.payment_type !== paymentType) return;

	const currency = paymentTypeResult.message?.currency;
	await frm.set_value("currency", currency || "");
	if (!currency) {
		await frm.set_value("exchange_rate", 0);
		updateExchangeRateDisplay(frm);
		renderAmountToPayDisplay(frm);
		return;
	}

	const exchangeRateResult = await frappe.call({
		method: "ice_control.api.api.get_exchange_rate",
		args: { currency },
	});
	if (frm.doc.payment_type !== paymentType) return;

	const paymentAmount = flt(frm.doc.total_payment);
	await frm.set_value("exchange_rate", exchangeRateResult.message);
	updateExchangeRateDisplay(frm);
	renderAmountToPayDisplay(frm);

	if (flt(frm.doc.input_amount) > 0) {
		frm.doc.input_amount = paymentAmount * (flt(frm.doc.exchange_rate) || 1);
		frm.refresh_field("input_amount");
		await callAllocatePaymentAmount(frm);
	}
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

function styleExpensePaymentInputAmountField(frm) {
	frm.get_field("input_amount")?.$wrapper.addClass("sale-payment-input-amount-card");
}

function hideExpenseGridDuplicateAction(frm) {
	const wrapper = frm.get_field("expenses")?.$wrapper;
	if (!wrapper) return;

	wrapper.addClass("expenses-grid-no-duplicate");
	if (!wrapper.children("style[data-expenses-grid-actions]").length) {
		wrapper.prepend(`
			<style data-expenses-grid-actions>
				.expenses-grid-no-duplicate .grid-duplicate-row,
				.expenses-grid-no-duplicate .grid-duplicate-rows {
					display: none !important;
				}
				.expenses-grid-no-duplicate .grid-row[data-payment-status="paid"] {
					border-left: 4px solid #28a745;
				}
				.expenses-grid-no-duplicate .grid-row[data-payment-status="partial"] {
					border-left: 4px solid #f0ad4e;
				}
				.expenses-grid-no-duplicate .grid-row[data-payment-status="unpaid"] {
					border-left: 4px solid #dc3545;
				}
				.expenses-grid-no-duplicate .grid-row[data-has-write-off="true"]
					.grid-static-col[data-fieldname="write_off_amount"],
				.expenses-grid-no-duplicate .grid-row[data-has-write-off="true"]
					.grid-static-col[data-fieldname="write_off_amount"] .static-area,
				.expenses-grid-no-duplicate .grid-row[data-has-write-off="true"]
					.grid-static-col[data-fieldname="write_off_amount"] input {
					color: #dc3545 !important;
					font-weight: 600;
				}
			</style>
		`);
	}
}

function getVendorExpenseBalance(frm) {
	if (frm.doc.vendor && frm.doc.outlet && frm.doc.posting_date) {
		frm.call("get_vendor_expense_balance");
	} else {
		frm.set_value("current_expense_payable_balance", 0);
	}
}

async function callAllocatePaymentAmount(frm) {
	clearTimeout(frm.__allocate_expense_payment_timer);
	frm.__allocate_expense_payment_timer = null;
	await frm.call("allocate_payment_amount");
	frm.refresh_fields();
	renderExpensePaymentSummary(frm);
	ensureExpenseGridObserver(frm);
	refreshExpenseRowFormatting(frm);
	setTimeout(() => refreshExpenseRowFormatting(frm), 300);
}

async function callUpdateExpenseRecord(frm) {
	clearTimeout(frm.__update_expense_summary_timer);
	frm.__update_expense_summary_timer = null;
	await frm.call("update_expense_record");
	frm.refresh_fields();
	renderExpensePaymentSummary(frm);
	ensureExpenseGridObserver(frm);
	refreshExpenseRowFormatting(frm);
	setTimeout(() => refreshExpenseRowFormatting(frm), 300);
}

function scheduleAllocatePaymentAmount(frm) {
	clearTimeout(frm.__allocate_expense_payment_timer);
	frm.__allocate_expense_payment_timer = setTimeout(() => {
		frm.__allocate_expense_payment_timer = null;
		callAllocatePaymentAmount(frm);
	}, 150);
}

function scheduleAllocationAfterRowRemoval(frm) {
	clearTimeout(frm.__allocate_expense_payment_timer);
	frm.__allocate_expense_payment_timer = setTimeout(async () => {
		frm.__allocate_expense_payment_timer = null;
		await syncParentPaymentAmount(frm);
		await callAllocatePaymentAmount(frm);
	}, 150);
}

function updateChildExpenseBalance(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	row.balance = flt(row.expense_balance)
		- flt(row.payment_amount)
		- flt(row.write_off_amount);
	frm.refresh_field("expenses");
}

async function syncParentPaymentAmount(frm) {
	const paymentAmount = (frm.doc.expenses || []).reduce(
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

	frm.doc.total_payment = paymentAmount;
	frm.doc.input_amount = paymentCurrency === defaultCurrency
		? paymentAmount
		: paymentAmount * exchangeRate;
	frm.refresh_field("total_payment");
	frm.refresh_field("input_amount");
	renderExpensePaymentSummary(frm);
}

function setupExpenseRowIndicators(frm) {
	if (!frm.__expense_row_indicator_bound) {
		frm.__expense_row_indicator_bound = true;
		$(frm.wrapper).on("grid-row-render.expense-payment-status", (event, gridRow) => {
			if (gridRow.grid?.df?.fieldname === "expenses") {
				updateExpenseRowIndicator(gridRow);
				updateExpenseWriteOffPaymentLock(gridRow);
			}
		});
	}

	ensureExpenseGridObserver(frm);
	refreshExpenseRowFormatting(frm);
	setTimeout(() => refreshExpenseRowFormatting(frm), 300);
}

function ensureExpenseGridObserver(frm) {
	const wrapper = frm.get_field("expenses")?.$wrapper;
	if (frm.__expense_grid_observer || !wrapper?.[0]) return;

	frm.__expense_grid_observer = new MutationObserver(() => {
		clearTimeout(frm.__expense_grid_format_timer);
		frm.__expense_grid_format_timer = setTimeout(
			() => refreshExpenseRowFormatting(frm),
			50
		);
	});
	frm.__expense_grid_observer.observe(wrapper[0], {
		childList: true,
		subtree: true,
	});
}

function refreshExpenseRowFormatting(frm) {
	const grid = frm.get_field("expenses")?.grid;
	(grid?.grid_rows || []).forEach(gridRow => {
		updateExpenseRowIndicator(gridRow);
		updateExpenseWriteOffPaymentLock(gridRow);
	});
}

function updateExpenseRowIndicator(gridRow) {
	const row = gridRow.doc;
	const expenseBalance = flt(row.expense_balance);
	const allocatedAmount = flt(row.payment_amount) + flt(row.write_off_amount);
	const balance = flt(row.balance);
	let status = "unpaid";

	if (row.expense && expenseBalance > 0 && balance <= 0) {
		status = "paid";
	} else if (row.expense && allocatedAmount > 0) {
		status = "partial";
	}
	gridRow.wrapper.attr("data-payment-status", row.expense ? status : null);
}

function updateExpenseWriteOffPaymentLock(gridRow) {
	if (!gridRow) return;
	const hasWriteOff = flt(gridRow.doc.write_off_amount) > 0;
	gridRow.wrapper.attr("data-has-write-off", hasWriteOff ? "true" : null);
	const paymentField = gridRow.on_grid_fields_dict?.payment_amount;
	if (paymentField && cint(paymentField.df.read_only) !== cint(hasWriteOff)) {
		gridRow.toggle_editable("payment_amount", !hasWriteOff);
	}
}

async function getPaymentTypeDefaultAccount(frm) {
	const paymentType = frm.doc.payment_type;
	const outlet = frm.doc.outlet;
	if (!paymentType || !outlet) {
		await frm.set_value("account_code", "");
		return;
	}

	const result = await frappe.call({
		method: "ice_control.api.api.get_payment_type_default_account",
		args: { payment_type: paymentType, outlet },
	});
	if (frm.doc.payment_type === paymentType && frm.doc.outlet === outlet) {
		await frm.set_value("account_code", result.message?.default_account || "");
	}
}
