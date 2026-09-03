# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from ice_control.api.utils import get_current_employee_outlets


ROOT_TYPE_ORDER = {
	"Asset": 0,
	"Liabilities": 1,
	"Equity": 2,
	"Income": 3,
	"Expenses": 4,
}


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	data, totals = get_data(filters)
	return get_columns(), data, None, None, get_report_summary(totals)


def validate_filters(filters: frappe._dict) -> None:
	if not filters.get("start_date") or not filters.get("end_date"):
		frappe.throw(_("Start Date and End Date are required."))

	filters.start_date = getdate(filters.start_date)
	filters.end_date = getdate(filters.end_date)

	if filters.start_date > filters.end_date:
		frappe.throw(_("Start Date cannot be after End Date."))


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Account Code"),
			"fieldname": "account_code",
			"fieldtype": "Data",
			"width": 210,
		},
		{
			"label": _("Account Name"),
			"fieldname": "account_name",
			"fieldtype": "Data",
			"width": 250,
		},
		{
			"label": _("Account Type"),
			"fieldname": "account_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Opening Debit"),
			"fieldname": "opening_debit",
			"fieldtype": "Currency",
			"width": 135,
		},
		{
			"label": _("Opening Credit"),
			"fieldname": "opening_credit",
			"fieldtype": "Currency",
			"width": 135,
		},
		{
			"label": _("Debit"),
			"fieldname": "debit_amount",
			"fieldtype": "Currency",
			"width": 125,
		},
		{
			"label": _("Credit"),
			"fieldname": "credit_amount",
			"fieldtype": "Currency",
			"width": 125,
		},
		{
			"label": _("Closing Debit"),
			"fieldname": "closing_debit",
			"fieldtype": "Currency",
			"width": 135,
		},
		{
			"label": _("Closing Credit"),
			"fieldname": "closing_credit",
			"fieldtype": "Currency",
			"width": 135,
		},
	]


def get_data(filters: frappe._dict) -> tuple[list[dict], dict]:
	allowed_outlets = sorted({outlet for outlet in get_current_employee_outlets() if outlet})
	if not allowed_outlets:
		return [], get_totals({})

	if filters.get("outlet") and filters.outlet not in allowed_outlets:
		frappe.throw(
			_("You do not have permission to access Outlet {0}.").format(
				frappe.bold(filters.outlet)
			),
			frappe.PermissionError,
		)

	direct_balances = get_direct_balances(filters, allowed_outlets)
	accounts = get_accounts(filters, allowed_outlets, set(direct_balances))
	if not accounts:
		return [], get_totals(direct_balances)

	roll_up_balances(accounts, direct_balances)
	data = build_rows(
		accounts,
		show_empty=cint(filters.get("show_accounts_without_transactions")),
	)
	totals = get_totals(direct_balances)

	data.extend(
		[
			{},
			{
				"account_code": _("Total"),
				"opening_debit": totals["opening_debit"],
				"opening_credit": totals["opening_credit"],
				"debit_amount": totals["debit_amount"],
				"credit_amount": totals["credit_amount"],
				"closing_debit": totals["closing_debit"],
				"closing_credit": totals["closing_credit"],
				"is_total": 1,
			},
		]
	)

	return data, totals


def get_direct_balances(filters: frappe._dict, allowed_outlets: list[str]) -> dict[str, dict]:
	conditions = [
		"gle.outlet in %(allowed_outlets)s",
		"coalesce(gle.is_cancelled, 0) = 0",
		"gle.posting_date <= %(end_date)s",
	]
	query_filters = {
		"allowed_outlets": tuple(allowed_outlets),
		"start_date": filters.start_date,
		"end_date": filters.end_date,
	}

	if filters.get("outlet"):
		conditions.append("gle.outlet = %(outlet)s")
		query_filters["outlet"] = filters.outlet

	rows = frappe.db.sql(
		f"""
			select
				gle.account,
				sum(
					case when gle.posting_date < %(start_date)s
						then coalesce(gle.debit_amount, 0) - coalesce(gle.credit_amount, 0)
						else 0
					end
				) as opening_balance,
				sum(
					case when gle.posting_date between %(start_date)s and %(end_date)s
						then coalesce(gle.debit_amount, 0)
						else 0
					end
				) as debit_amount,
				sum(
					case when gle.posting_date between %(start_date)s and %(end_date)s
						then coalesce(gle.credit_amount, 0)
						else 0
					end
				) as credit_amount,
				sum(
					case when gle.posting_date between %(start_date)s and %(end_date)s
						then 1
						else 0
					end
				) as transaction_count
			from `tabGL Entry` gle
			where {' and '.join(conditions)}
				and gle.account is not null
				and gle.account != ''
			group by gle.account
		""",
		query_filters,
		as_dict=True,
	)

	balances = {}
	for row in rows:
		opening_balance = flt(row.opening_balance)
		debit_amount = flt(row.debit_amount)
		credit_amount = flt(row.credit_amount)
		closing_balance = opening_balance + debit_amount - credit_amount
		opening_debit, opening_credit = split_balance(opening_balance)
		closing_debit, closing_credit = split_balance(closing_balance)

		balances[row.account] = {
			"opening_debit": opening_debit,
			"opening_credit": opening_credit,
			"debit_amount": debit_amount,
			"credit_amount": credit_amount,
			"closing_debit": closing_debit,
			"closing_credit": closing_credit,
			"transaction_count": cint(row.transaction_count),
			"has_activity": bool(
				opening_debit
				or opening_credit
				or debit_amount
				or credit_amount
			),
		}

	return balances


def get_accounts(
	filters: frappe._dict, allowed_outlets: list[str], active_account_names: set[str]
) -> list[dict]:
	accounts = frappe.db.sql(
		"""
			select
				name,
				account_code,
				account_name,
				account_type,
				root_type,
				parent_chart_of_account,
				coalesce(is_group, 0) as is_group,
				coalesce(outlet, '') as outlet,
				coalesce(lft, 0) as lft
			from `tabChart of Account`
			order by lft, account_code, account_name
		""",
		as_dict=True,
	)
	if not accounts:
		return []

	accounts_by_name = {account.name: account for account in accounts}
	visible_outlets = {filters.outlet} if filters.get("outlet") else set(allowed_outlets)
	included_names = {
		account.name
		for account in accounts
		if not account.outlet or account.outlet in visible_outlets
	}
	included_names.update(
		account_name for account_name in active_account_names if account_name in accounts_by_name
	)

	# Preserve every ancestor required to display permitted and active accounts as a tree.
	for account_name in list(included_names):
		parent_name = accounts_by_name[account_name].parent_chart_of_account
		visited = set()
		while parent_name in accounts_by_name and parent_name not in visited:
			visited.add(parent_name)
			included_names.add(parent_name)
			parent_name = accounts_by_name[parent_name].parent_chart_of_account

	return [account for account in accounts if account.name in included_names]


def roll_up_balances(accounts: list[dict], direct_balances: dict[str, dict]) -> None:
	accounts_by_name = {account.name: account for account in accounts}
	children = defaultdict(list)

	for account in accounts:
		if account.parent_chart_of_account in accounts_by_name:
			children[account.parent_chart_of_account].append(account.name)

	for child_names in children.values():
		child_names.sort(key=lambda name: get_account_sort_key(accounts_by_name[name]))

	calculated = set()
	calculating = set()

	def calculate(account_name: str) -> dict:
		account = accounts_by_name[account_name]
		if account_name in calculated:
			return account
		if account_name in calculating:
			# Do not let a malformed circular account tree break the report.
			return account

		calculating.add(account_name)
		direct = direct_balances.get(account_name, {})
		for fieldname in get_balance_fieldnames():
			account[fieldname] = flt(direct.get(fieldname))
		account.transaction_count = cint(direct.get("transaction_count"))
		account.has_activity = bool(direct.get("has_activity"))

		for child_name in children.get(account_name, []):
			child = calculate(child_name)
			for fieldname in get_balance_fieldnames():
				account[fieldname] += flt(child.get(fieldname))
			account.transaction_count += cint(child.get("transaction_count"))
			account.has_activity = account.has_activity or bool(child.get("has_activity"))

		calculating.discard(account_name)
		calculated.add(account_name)
		return account

	for account in accounts:
		calculate(account.name)


def build_rows(accounts: list[dict], show_empty: bool) -> list[dict]:
	accounts_by_name = {account.name: account for account in accounts}
	children = defaultdict(list)
	roots = []

	for account in accounts:
		if account.parent_chart_of_account in accounts_by_name:
			children[account.parent_chart_of_account].append(account.name)
		else:
			roots.append(account.name)

	for child_names in children.values():
		child_names.sort(key=lambda name: get_account_sort_key(accounts_by_name[name]))
	roots.sort(key=lambda name: get_account_sort_key(accounts_by_name[name]))

	data = []
	visited = set()

	def add_account(account_name: str, indent: int) -> None:
		if account_name in visited:
			return
		visited.add(account_name)

		account = accounts_by_name[account_name]
		if not show_empty and not account.has_activity:
			return

		parent = accounts_by_name.get(account.parent_chart_of_account)
		row = {
			"account": account.name,
			"account_code": account.account_code or account.name,
			"account_name": account.account_name,
			"account_type": account.account_type or account.root_type,
			"root_type": account.root_type,
			"parent_account": (parent.account_code or parent.name) if parent else None,
			"indent": indent,
			"is_group": cint(account.is_group or bool(children.get(account_name))),
		}
		for fieldname in get_balance_fieldnames():
			row[fieldname] = flt(account.get(fieldname))
		data.append(row)

		for child_name in children.get(account_name, []):
			add_account(child_name, indent + 1)

	for root_name in roots:
		add_account(root_name, 0)

	# Include malformed/cyclic orphan records without losing report data.
	for account in sorted(accounts, key=get_account_sort_key):
		if account.name not in visited:
			add_account(account.name, 0)

	return data


def get_account_sort_key(account: dict) -> tuple:
	return (
		ROOT_TYPE_ORDER.get(account.root_type, len(ROOT_TYPE_ORDER)),
		0 if cint(account.lft) else 1,
		cint(account.lft),
		str(account.account_code or ""),
		str(account.account_name or ""),
	)


def get_balance_fieldnames() -> tuple[str, ...]:
	return (
		"opening_debit",
		"opening_credit",
		"debit_amount",
		"credit_amount",
		"closing_debit",
		"closing_credit",
	)


def split_balance(balance: float) -> tuple[float, float]:
	balance = flt(balance)
	return (balance, 0.0) if balance >= 0 else (0.0, abs(balance))


def get_totals(direct_balances: dict[str, dict]) -> dict:
	totals = {fieldname: 0.0 for fieldname in get_balance_fieldnames()}
	for balance in direct_balances.values():
		for fieldname in totals:
			totals[fieldname] += flt(balance.get(fieldname))

	totals["opening_difference"] = totals["opening_debit"] - totals["opening_credit"]
	totals["period_difference"] = totals["debit_amount"] - totals["credit_amount"]
	totals["closing_difference"] = totals["closing_debit"] - totals["closing_credit"]
	return totals


def get_report_summary(totals: dict) -> list[dict]:
	difference = flt(totals.get("closing_difference"))
	return [
		{
			"label": _("Closing Debit"),
			"value": flt(totals.get("closing_debit")),
			"datatype": "Currency",
			"indicator": "Blue",
		},
		{
			"label": _("Closing Credit"),
			"value": flt(totals.get("closing_credit")),
			"datatype": "Currency",
			"indicator": "Blue",
		},
		{
			"label": _("Difference"),
			"value": difference,
			"datatype": "Currency",
			"indicator": "Green" if abs(difference) < 0.000001 else "Red",
		},
	]
