from __future__ import annotations

from collections import defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_days, add_months, date_diff, flt, get_first_day, getdate, now_datetime, today

from ice_control.api.utils import get_current_employee_outlets


AGING_BUCKETS = (
	("current", "Current"),
	("days_1_30", "1-30"),
	("days_31_60", "31-60"),
	("days_61_90", "61-90"),
	("days_91_120", "91-120"),
	("days_over_120", "120+"),
)
AMOUNT_TOLERANCE = 0.005
RECENT_TRANSACTION_LIMIT = 8
TOP_PAYABLE_LIMIT = 5
TOP_RECEIVABLE_LIMIT = 5


@frappe.whitelist(methods=["GET"])
def get_dashboard_data(
	outlet: str | None = None,
	start_date: str | date | None = None,
	end_date: str | date | None = None,
) -> dict:
	"""Return the complete account dashboard payload in one request."""
	_validate_gl_permission()
	filters = _get_filters(outlet, start_date, end_date)
	allowed_outlets = _get_allowed_outlets(filters.outlet)
	currency = frappe.get_cached_value("Business Information", None, "default_currency") or ""
	outlets = _get_outlet_options(allowed_outlets)

	if not allowed_outlets:
		return _get_empty_dashboard(filters, outlets, currency)

	query_filters = {
		"outlets": tuple([filters.outlet] if filters.outlet else allowed_outlets),
		"start_date": filters.start_date,
		"end_date": filters.end_date,
	}
	period_days = date_diff(filters.end_date, filters.start_date) + 1
	previous_end_date = add_days(filters.start_date, -1)
	previous_start_date = add_days(previous_end_date, -(period_days - 1))
	

	current_snapshot = _get_snapshot_balances(query_filters, filters.end_date)
	previous_snapshot = _get_snapshot_balances(query_filters, previous_end_date)
	current_period = _get_period_totals(query_filters, filters.start_date, filters.end_date)
	previous_period = _get_period_totals(query_filters, previous_start_date, previous_end_date)

	trend_rows = _get_trend_rows(query_filters)
	financial_trend, cash_flow = _build_trends(
		trend_rows,
		filters.start_date,
		filters.end_date,
	)
	receivable_rows = _get_receivable_aging_rows(query_filters)
	receivable_aging, overdue_customers = _build_receivable_aging(
		receivable_rows,
		filters.end_date,
	)
	payable_rows = _get_payable_aging_rows(query_filters)
	payable_aging = _build_payable_aging(payable_rows, filters.end_date)

	return {
		"filters": {
			"outlet": filters.outlet or "",
			"start_date": str(filters.start_date),
			"end_date": str(filters.end_date),
		},
		"outlets": outlets,
		"currency": currency,
		"generated_at": now_datetime().isoformat(),
		"summary": _build_summary(
			current_snapshot,
			previous_snapshot,
			current_period,
			previous_period,
		),
		"financial_trend": financial_trend,
		"cash_flow": cash_flow,
		"receivable_aging": receivable_aging,
		"top_receivables": _get_top_receivables(query_filters),
		"payable_aging": payable_aging,
		"top_payables": _get_top_payables(query_filters),
		"alerts": _get_alerts(query_filters, overdue_customers),
		"recent_transactions": _get_recent_transactions(query_filters),
	}


def _validate_gl_permission() -> None:
	if not frappe.has_permission("GL Entry", "read"):
		frappe.throw(_("You do not have permission to view accounting data."), frappe.PermissionError)


def _get_filters(
	outlet: str | None,
	start_date: str | date | None,
	end_date: str | date | None,
) -> frappe._dict:
	filters = frappe._dict(
		outlet=(outlet or "").strip(),
		start_date=getdate(start_date or get_first_day(today())),
		end_date=getdate(end_date or today()),
	)
	if filters.start_date > filters.end_date:
		frappe.throw(_("Start Date cannot be after End Date."))
	return filters


def _get_allowed_outlets(selected_outlet: str | None) -> list[str]:
	allowed_outlets = sorted({outlet for outlet in get_current_employee_outlets() if outlet})
	if selected_outlet and selected_outlet not in allowed_outlets:
		frappe.throw(
			_("You do not have permission to access Outlet {0}.").format(
				frappe.bold(selected_outlet)
			),
			frappe.PermissionError,
		)
	return allowed_outlets


def _get_outlet_options(allowed_outlets: list[str]) -> list[dict]:
	if not allowed_outlets:
		return []
	return frappe.db.sql(
		"""
			select name as value, coalesce(nullif(outlet_name, ''), name) as label
			from `tabOutlet`
			where name in %(outlets)s and coalesce(enabled, 0) = 1
			order by outlet_name, name
		""",
		{"outlets": tuple(allowed_outlets)},
		as_dict=True,
	)


def _get_snapshot_balances(query_filters: dict, cutoff_date: date) -> dict:
	rows = frappe.db.sql(
		"""
			select
				coalesce(nullif(gle.account_type, ''), coa.account_type) as account_type,
				gle.party_type,
				gle.party,
				sum(coalesce(gle.debit_amount, 0) - coalesce(gle.credit_amount, 0)) as balance
			from `tabGL Entry` gle
			left join `tabChart of Account` coa on coa.name = gle.account
			where gle.outlet in %(outlets)s
				and coalesce(gle.is_cancelled, 0) = 0
				and gle.posting_date <= %(cutoff_date)s
				and coalesce(nullif(gle.account_type, ''), coa.account_type)
					in ('Cash', 'Bank', 'Receivable', 'Payable')
			group by
				coalesce(nullif(gle.account_type, ''), coa.account_type),
				gle.party_type,
				gle.party
		""",
		{**query_filters, "cutoff_date": cutoff_date},
		as_dict=True,
	)
	balances = {"cash_and_bank": 0.0, "receivable": 0.0, "payable": 0.0}
	for row in rows:
		balance = flt(row.get("balance"))
		if row.get("account_type") in ("Cash", "Bank"):
			balances["cash_and_bank"] += balance
		elif row.get("account_type") == "Receivable" and balance > AMOUNT_TOLERANCE:
			balances["receivable"] += balance
		elif row.get("account_type") == "Payable" and balance < -AMOUNT_TOLERANCE:
			balances["payable"] += abs(balance)
	return {fieldname: flt(value) for fieldname, value in balances.items()}


def _get_period_totals(query_filters: dict, start_date: date, end_date: date) -> dict:
	rows = frappe.db.sql(
		"""
			select
				coalesce(sum(case when coa.root_type = 'Income'
					then coalesce(gle.credit_amount, 0) - coalesce(gle.debit_amount, 0)
					else 0 end), 0) as income,
				coalesce(sum(case when coa.root_type = 'Expenses'
					then coalesce(gle.debit_amount, 0) - coalesce(gle.credit_amount, 0)
					else 0 end), 0) as expense,
				coalesce(sum(case when coa.root_type = 'Income' and gle.voucher_type = 'Sale'
					then coalesce(gle.credit_amount, 0) - coalesce(gle.debit_amount, 0)
					else 0 end), 0) as total_sales,
				coalesce(sum(case when gle.voucher_type = 'Sale Payment'
						and coalesce(nullif(gle.account_type, ''), coa.account_type) in ('Cash', 'Bank')
					then coalesce(gle.debit_amount, 0) else 0 end), 0) as collections,
				coalesce(sum(case when gle.voucher_type in ('Purchase Orders', 'Purchase Order Payment')
						and coalesce(nullif(gle.account_type, ''), coa.account_type) in ('Cash', 'Bank')
					then coalesce(gle.credit_amount, 0) else 0 end), 0) as purchase_payments,
				coalesce(sum(case when coalesce(nullif(gle.account_type, ''), coa.account_type) in ('Cash', 'Bank')
					then coalesce(gle.debit_amount, 0) - coalesce(gle.credit_amount, 0)
					else 0 end), 0) as net_cash_movement
			from `tabGL Entry` gle
			left join `tabChart of Account` coa on coa.name = gle.account
			where gle.outlet in %(outlets)s
				and coalesce(gle.is_cancelled, 0) = 0
				and gle.posting_date between %(period_start)s and %(period_end)s
		""",
		{**query_filters, "period_start": start_date, "period_end": end_date},
		as_dict=True,
	)
	row = rows[0] if rows else {}
	income = flt(row.get("income"))
	expense = flt(row.get("expense"))
	return {
		"income": income,
		"expense": expense,
		"profit": income - expense,
		"total_sales": flt(row.get("total_sales")),
		"collections": flt(row.get("collections")),
		"purchase_payments": flt(row.get("purchase_payments")),
		"net_cash_movement": flt(row.get("net_cash_movement")),
	}


def _build_summary(
	current_snapshot: dict,
	previous_snapshot: dict,
	current_period: dict,
	previous_period: dict,
) -> dict:
	
	return {
		"cash_and_bank": _metric(current_snapshot["cash_and_bank"], previous_snapshot["cash_and_bank"]),
		"receivable": _metric(
			current_snapshot["receivable"], previous_snapshot["receivable"], inverse=True
		),
		"payable": _metric(current_snapshot["payable"], previous_snapshot["payable"], inverse=True),
		"net_profit": _metric(current_period["profit"], previous_period["profit"]),
		"total_sales": _metric(current_period["total_sales"], previous_period["total_sales"]),
		"collections": _metric(current_period["collections"], previous_period["collections"]),
		"purchase_payments": _metric(
			current_period["purchase_payments"], previous_period["purchase_payments"], inverse=True
		),
		"expenses": _metric(current_period["expense"], previous_period["expense"], inverse=True),
		"net_cash_movement": flt(current_period["net_cash_movement"]),
	}


def _metric(value: float, previous_value: float, inverse: bool = False) -> dict:
	change = _percentage_change(value, previous_value)
	return {
		"value": flt(value),
		"previous_value": flt(previous_value),
		"change": change,
		"is_positive": None if change is None else (change <= 0 if inverse else change >= 0),
	}


def _percentage_change(value: float, previous_value: float) -> float | None:
	value = flt(value)
	previous_value = flt(previous_value)
	if abs(previous_value) <= AMOUNT_TOLERANCE:
		return None if abs(value) <= AMOUNT_TOLERANCE else 100.0
	return flt(((value - previous_value) / abs(previous_value)) * 100, 1)


def _get_trend_rows(query_filters: dict) -> list[dict]:
	return frappe.db.sql(
		"""
			select
				gle.posting_date,
				coalesce(sum(case when coa.root_type = 'Income'
					then coalesce(gle.credit_amount, 0) - coalesce(gle.debit_amount, 0)
					else 0 end), 0) as income,
				coalesce(sum(case when coa.root_type = 'Expenses'
					then coalesce(gle.debit_amount, 0) - coalesce(gle.credit_amount, 0)
					else 0 end), 0) as expense,
				coalesce(sum(case when coalesce(nullif(gle.account_type, ''), coa.account_type) in ('Cash', 'Bank')
						
					then coalesce(gle.debit_amount, 0) else 0 end), 0) as inflow,
				coalesce(sum(case when coalesce(nullif(gle.account_type, ''), coa.account_type) in ('Cash', 'Bank')
						
					then coalesce(gle.credit_amount, 0) else 0 end), 0) as outflow
			from `tabGL Entry` gle
			left join `tabChart of Account` coa on coa.name = gle.account
			where gle.outlet in %(outlets)s
				and coalesce(gle.is_cancelled, 0) = 0
				and gle.posting_date between %(start_date)s and %(end_date)s
			group by gle.posting_date
			order by gle.posting_date
		""",
		query_filters,
		as_dict=True,
	)


def _build_trends(rows: list[dict], start_date: date, end_date: date) -> tuple[dict, dict]:
	granularity = "day" if date_diff(end_date, start_date) <= 45 else "month"
	buckets = _make_period_buckets(start_date, end_date, granularity)
	for row in rows:
		posting_date = getdate(row.get("posting_date"))
		key = str(posting_date) if granularity == "day" else posting_date.strftime("%Y-%m")
		if key not in buckets:
			continue
		for fieldname in ("income", "expense", "inflow", "outflow"):
			buckets[key][fieldname] += flt(row.get(fieldname))

	labels = list(buckets)
	income = [flt(bucket["income"]) for bucket in buckets.values()]
	expense = [flt(bucket["expense"]) for bucket in buckets.values()]
	inflow = [flt(bucket["inflow"]) for bucket in buckets.values()]
	outflow = [flt(bucket["outflow"]) for bucket in buckets.values()]
	return (
		{
			"granularity": granularity,
			"labels": labels,
			"income": income,
			"expense": expense,
			"profit": [flt(income[index] - expense[index]) for index in range(len(labels))],
		},
		{
			"granularity": granularity,
			"labels": labels,
			"inflow": inflow,
			"outflow": outflow,
			"net": [flt(inflow[index] - outflow[index]) for index in range(len(labels))],
		},
	)


def _make_period_buckets(start_date: date, end_date: date, granularity: str) -> dict:
	buckets = {}
	current = getdate(start_date)
	if granularity == "month":
		current = get_first_day(current)
		while current <= end_date:
			buckets[current.strftime("%Y-%m")] = defaultdict(float)
			current = add_months(current, 1)
	else:
		while current <= end_date:
			buckets[str(current)] = defaultdict(float)
			current = add_days(current, 1)
	return buckets


def _get_receivable_aging_rows(query_filters: dict) -> list[dict]:
	return frappe.db.sql(
		"""
			select
				gle.party,
				gle.posting_date,
				sum(coalesce(gle.debit_amount, 0)) as debit_amount,
				sum(coalesce(gle.credit_amount, 0)) as credit_amount
			from `tabGL Entry` gle
			left join `tabChart of Account` coa on coa.name = gle.account
			where gle.outlet in %(outlets)s
				and coalesce(gle.is_cancelled, 0) = 0
				and coalesce(nullif(gle.account_type, ''), coa.account_type) = 'Receivable'
				and gle.party_type = 'Customer'
				and coalesce(gle.party, '') != ''
				and gle.posting_date <= %(end_date)s
			group by gle.party, gle.posting_date
			order by gle.party, gle.posting_date
		""",
		query_filters,
		as_dict=True,
	)


def _get_payable_aging_rows(query_filters: dict) -> list[dict]:
	return frappe.db.sql(
		"""
			select
				gle.party_type,
				gle.party,
				gle.posting_date,
				sum(coalesce(gle.debit_amount, 0)) as debit_amount,
				sum(coalesce(gle.credit_amount, 0)) as credit_amount
			from `tabGL Entry` gle
			left join `tabChart of Account` coa on coa.name = gle.account
			where gle.outlet in %(outlets)s
				and coalesce(gle.is_cancelled, 0) = 0
				and coalesce(nullif(gle.account_type, ''), coa.account_type) = 'Payable'
				and gle.party_type in ('Customer', 'Employee', 'Vendor')
				and coalesce(gle.party, '') != ''
				and gle.posting_date <= %(end_date)s
			group by gle.party_type, gle.party, gle.posting_date
			order by gle.party_type, gle.party, gle.posting_date
		""",
		query_filters,
		as_dict=True,
	)


def _build_receivable_aging(rows: list[dict], end_date: date) -> tuple[list[dict], set[str]]:
	customers: dict[str, dict] = {}
	for row in rows:
		party = row.get("party")
		customer = customers.setdefault(party, {"debits": [], "unapplied_credit": 0.0})
		net_amount = flt(row.get("debit_amount")) - flt(row.get("credit_amount"))
		if net_amount > 0:
			applied_credit = min(net_amount, customer["unapplied_credit"])
			net_amount -= applied_credit
			customer["unapplied_credit"] -= applied_credit
			if net_amount:
				customer["debits"].append(
					{"posting_date": getdate(row.get("posting_date")), "amount": net_amount}
				)
		elif net_amount < 0:
			credit_to_apply = abs(net_amount)
			for debit in customer["debits"]:
				if credit_to_apply <= AMOUNT_TOLERANCE:
					break
				applied_credit = min(debit["amount"], credit_to_apply)
				debit["amount"] -= applied_credit
				credit_to_apply -= applied_credit
			customer["unapplied_credit"] += credit_to_apply

	totals = {fieldname: 0.0 for fieldname, _label in AGING_BUCKETS}
	overdue_customers = set()
	for party, customer in customers.items():
		for debit in customer["debits"]:
			amount = flt(debit["amount"])
			if amount <= AMOUNT_TOLERANCE:
				continue
			age = date_diff(end_date, debit["posting_date"])
			bucket = _get_aging_bucket(age)
			totals[bucket] += amount
			if age > 30:
				overdue_customers.add(party)

	return (
		[
			{"key": fieldname, "label": _(label), "value": flt(totals[fieldname])}
			for fieldname, label in AGING_BUCKETS
		],
		overdue_customers,
	)


def _build_payable_aging(rows: list[dict], end_date: date) -> list[dict]:
	parties: dict[tuple[str, str], dict] = {}
	for row in rows:
		party_key = (row.get("party_type") or "", row.get("party"))
		party = parties.setdefault(party_key, {"credits": [], "unapplied_debit": 0.0})
		net_amount = flt(row.get("credit_amount")) - flt(row.get("debit_amount"))
		if net_amount > 0:
			applied_debit = min(net_amount, party["unapplied_debit"])
			net_amount -= applied_debit
			party["unapplied_debit"] -= applied_debit
			if net_amount:
				party["credits"].append(
					{"posting_date": getdate(row.get("posting_date")), "amount": net_amount}
				)
		elif net_amount < 0:
			debit_to_apply = abs(net_amount)
			for credit in party["credits"]:
				if debit_to_apply <= AMOUNT_TOLERANCE:
					break
				applied_debit = min(credit["amount"], debit_to_apply)
				credit["amount"] -= applied_debit
				debit_to_apply -= applied_debit
			party["unapplied_debit"] += debit_to_apply

	totals = {fieldname: 0.0 for fieldname, _label in AGING_BUCKETS}
	for party in parties.values():
		for credit in party["credits"]:
			amount = flt(credit["amount"])
			if amount <= AMOUNT_TOLERANCE:
				continue
			age = date_diff(end_date, credit["posting_date"])
			totals[_get_aging_bucket(age)] += amount

	return [
		{"key": fieldname, "label": _(label), "value": flt(totals[fieldname])}
		for fieldname, label in AGING_BUCKETS
	]


def _get_aging_bucket(age: int) -> str:
	if age <= 0:
		return "current"
	if age <= 30:
		return "days_1_30"
	if age <= 60:
		return "days_31_60"
	if age <= 90:
		return "days_61_90"
	if age <= 120:
		return "days_91_120"
	return "days_over_120"


def _get_top_receivables(query_filters: dict) -> list[dict]:
	rows = frappe.db.sql(
		"""
			select
				gle.party_type,
				gle.party,
				coalesce(max(nullif(gle.party_name, '')), gle.party) as party_name,
				sum(coalesce(gle.debit_amount, 0) - coalesce(gle.credit_amount, 0)) as balance
			from `tabGL Entry` gle
			left join `tabChart of Account` coa on coa.name = gle.account
			where gle.outlet in %(outlets)s
				and coalesce(gle.is_cancelled, 0) = 0
				and coalesce(nullif(gle.account_type, ''), coa.account_type) = 'Receivable'
				and gle.party_type = 'Customer'
				and coalesce(gle.party, '') != ''
				and gle.posting_date <= %(end_date)s
			group by gle.party_type, gle.party
			having balance > %(amount_tolerance)s
			order by balance desc
			limit %(limit)s
		""",
		{
			**query_filters,
			"amount_tolerance": AMOUNT_TOLERANCE,
			"limit": TOP_RECEIVABLE_LIMIT,
		},
		as_dict=True,
	)
	return [
		{
			"party_type": row.get("party_type"),
			"party": row.get("party"),
			"party_name": row.get("party_name") or row.get("party"),
			"balance": flt(row.get("balance")),
		}
		for row in rows
	]


def _get_top_payables(query_filters: dict) -> list[dict]:
	rows = frappe.db.sql(
		"""
			select
				gle.party_type,
				gle.party,
				coalesce(max(nullif(gle.party_name, '')), gle.party) as party_name,
				sum(coalesce(gle.credit_amount, 0) - coalesce(gle.debit_amount, 0)) as balance
			from `tabGL Entry` gle
			left join `tabChart of Account` coa on coa.name = gle.account
			where gle.outlet in %(outlets)s
				and coalesce(gle.is_cancelled, 0) = 0
				and coalesce(nullif(gle.account_type, ''), coa.account_type) = 'Payable'
				and coalesce(gle.party, '') != ''
				and gle.posting_date <= %(end_date)s
			group by gle.party_type, gle.party
			having balance > %(amount_tolerance)s
			order by balance desc
			limit %(limit)s
		""",
		{
			**query_filters,
			"amount_tolerance": AMOUNT_TOLERANCE,
			"limit": TOP_PAYABLE_LIMIT,
		},
		as_dict=True,
	)
	return [
		{
			"party_type": row.get("party_type"),
			"party": row.get("party"),
			"party_name": row.get("party_name") or row.get("party"),
			"balance": flt(row.get("balance")),
		}
		for row in rows
	]


def _get_alerts(query_filters: dict, overdue_customers: set[str]) -> list[dict]:
	alerts = []
	pending_sale_count = _get_pending_sale_count(query_filters)
	if pending_sale_count:
		outlets = list(query_filters["outlets"])
		alerts.append(
			{
				"key": "pending_sales",
				"severity": "warning",
				"title": _("Pending sales"),
				"message": _("{0} sale(s) are still in Draft status and need to be closed.").format(
					pending_sale_count
				),
				"route": ["List", "Sale"],
				"route_options": {
					"sale_status": "Draft",
					"posting_date": [
						"between",
						[str(query_filters["start_date"]), str(query_filters["end_date"])],
					],
					"outlet": outlets[0] if len(outlets) == 1 else ["in", outlets],
				},
			}
		)

	unbalanced_count = _get_unbalanced_voucher_count(query_filters)
	if unbalanced_count:
		alerts.append(
			{
				"key": "unbalanced_vouchers",
				"severity": "danger",
				"title": _("Unbalanced vouchers"),
				"message": _("{0} voucher(s) have unequal debit and credit totals.").format(
					unbalanced_count
				),
				"route": ["List", "GL Entry"],
				"route_options": {
					"posting_date": [
						"between",
						[str(query_filters["start_date"]), str(query_filters["end_date"])],
					]
				},
			}
		)

	if overdue_customers:
		alerts.append(
			{
				"key": "overdue_receivables",
				"severity": "warning",
				"title": _("Overdue receivables"),
				"message": _("{0} customer(s) have balances older than 30 days.").format(
					len(overdue_customers)
				),
				"route": ["query-report", "Account Receivable Aging"],
				"route_options": {
					"start_date": str(query_filters["start_date"]),
					"end_date": str(query_filters["end_date"]),
				},
			}
		)

	unclosed_outlets = _get_unclosed_outlets(query_filters)
	if unclosed_outlets:
		alerts.append(
			{
				"key": "unclosed_selling_date",
				"severity": "warning",
				"title": _("Selling date not closed"),
				"message": _("{0} outlet(s) are not closed through the selected end date.").format(
					len(unclosed_outlets)
				),
				"details": unclosed_outlets,
				"route": ["List", "Closed Selling Date"],
			}
		)

	missing_configuration = _get_outlets_missing_accounts(query_filters["outlets"])
	if missing_configuration:
		alerts.append(
			{
				"key": "missing_account_configuration",
				"severity": "danger",
				"title": _("Missing account configuration"),
				"message": _("{0} outlet(s) need default accounting accounts.").format(
					len(missing_configuration)
				),
				"details": missing_configuration,
				"route": ["List", "Outlet"],
			}
		)

	return alerts


def _get_pending_sale_count(query_filters: dict) -> int:
	return frappe.db.count(
		"Sale",
		filters={
			"sale_status": "Draft",
			"outlet": ["in", query_filters["outlets"]],
			"posting_date": [
				"between",
				[query_filters["start_date"], query_filters["end_date"]],
			],
		},
	)


def _get_unbalanced_voucher_count(query_filters: dict) -> int:
	rows = frappe.db.sql(
		"""
			select count(*) as voucher_count
			from (
				select gle.voucher_type, gle.voucher_no
				from `tabGL Entry` gle
				where gle.outlet in %(outlets)s
					and coalesce(gle.is_cancelled, 0) = 0
					and gle.posting_date between %(start_date)s and %(end_date)s
					and coalesce(gle.voucher_type, '') != ''
					and coalesce(gle.voucher_no, '') != ''
				group by gle.voucher_type, gle.voucher_no
				having abs(
					sum(coalesce(gle.debit_amount, 0)) - sum(coalesce(gle.credit_amount, 0))
				) > %(amount_tolerance)s
			) voucher_balances
		""",
		{**query_filters, "amount_tolerance": AMOUNT_TOLERANCE},
		as_dict=True,
	)
	return int(rows[0].get("voucher_count") or 0) if rows else 0


def _get_unclosed_outlets(query_filters: dict) -> list[str]:
	closed_rows = frappe.db.sql(
		"""
			select outlet, max(posting_date) as last_closed_date
			from `tabClosed Selling Date`
			where outlet in %(outlets)s and docstatus = 1
			group by outlet
		""",
		query_filters,
		as_dict=True,
	)
	closed_by_outlet = {
		row.get("outlet"): getdate(row.get("last_closed_date")) for row in closed_rows
	}
	return [
		outlet
		for outlet in query_filters["outlets"]
		if not closed_by_outlet.get(outlet)
		or closed_by_outlet[outlet] < query_filters["end_date"]
	]


def _get_outlets_missing_accounts(outlets: tuple[str, ...]) -> list[str]:
	rows = frappe.db.sql(
		"""
			select name
			from `tabOutlet`
			where name in %(outlets)s
				and (
					coalesce(default_receivable_account, '') = ''
					or coalesce(default_income_account, '') = ''
					or coalesce(default_payable_account, '') = ''
				)
			order by name
		""",
		{"outlets": outlets},
		pluck=True,
	)
	return list(rows)


def _get_recent_transactions(query_filters: dict) -> list[dict]:
	rows = frappe.db.sql(
		"""
			select
				gle.posting_date,
				gle.voucher_type,
				gle.voucher_no,
				max(nullif(gle.party_type, '')) as party_type,
				max(nullif(gle.party, '')) as party,
				coalesce(max(nullif(gle.party_name, '')), max(nullif(gle.party, '')), '') as party_name,
				sum(coalesce(gle.debit_amount, 0)) as total_debit,
				sum(coalesce(gle.credit_amount, 0)) as total_credit,
				max(gle.creation) as created_at
			from `tabGL Entry` gle
			where gle.outlet in %(outlets)s
				and coalesce(gle.is_cancelled, 0) = 0
				and gle.posting_date between %(start_date)s and %(end_date)s
				and coalesce(gle.voucher_type, '') != ''
				and coalesce(gle.voucher_no, '') != ''
			group by gle.posting_date, gle.voucher_type, gle.voucher_no
			order by gle.posting_date desc, created_at desc
			limit %(limit)s
		""",
		{**query_filters, "limit": RECENT_TRANSACTION_LIMIT},
		as_dict=True,
	)
	return [
		{
			"posting_date": str(getdate(row.get("posting_date"))),
			"voucher_type": row.get("voucher_type"),
			"voucher_no": row.get("voucher_no"),
			"party_type": row.get("party_type"),
			"party": row.get("party"),
			"party_name": row.get("party_name") or _("No party"),
			"amount": max(flt(row.get("total_debit")), flt(row.get("total_credit"))),
			"status": _("Posted"),
			"created_at": row.get("created_at").isoformat() if row.get("created_at") else "",
		}
		for row in rows
	]


def _get_empty_dashboard(filters: frappe._dict, outlets: list[dict], currency: str) -> dict:
	financial_trend, cash_flow = _build_trends([], filters.start_date, filters.end_date)
	empty_metric = _metric(0, 0)
	return {
		"filters": {
			"outlet": filters.outlet or "",
			"start_date": str(filters.start_date),
			"end_date": str(filters.end_date),
		},
		"outlets": outlets,
		"currency": currency,
		"generated_at": now_datetime().isoformat(),
		"summary": {
			"cash_and_bank": dict(empty_metric),
			"receivable": dict(empty_metric),
			"payable": dict(empty_metric),
			"net_profit": dict(empty_metric),
			"total_sales": dict(empty_metric),
			"collections": dict(empty_metric),
			"purchase_payments": dict(empty_metric),
			"expenses": dict(empty_metric),
			"net_cash_movement": 0.0,
		},
		"financial_trend": financial_trend,
		"cash_flow": cash_flow,
		"receivable_aging": [
			{"key": fieldname, "label": _(label), "value": 0.0}
			for fieldname, label in AGING_BUCKETS
		],
		"top_receivables": [],
		"payable_aging": [
			{"key": fieldname, "label": _(label), "value": 0.0}
			for fieldname, label in AGING_BUCKETS
		],
		"top_payables": [],
		"alerts": [],
		"recent_transactions": [],
	}
