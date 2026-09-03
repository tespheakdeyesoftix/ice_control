# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from ice_control.api.utils import get_current_employee_outlets


BALANCE_SHEET_ROOT_TYPES = ("Asset", "Liabilities", "Equity")
ROOT_TYPE_ORDER = {root_type: index for index, root_type in enumerate(BALANCE_SHEET_ROOT_TYPES)}


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	data, totals = get_data(filters)
	chart = get_chart(totals) if data else None

	return get_columns(), data, None, chart, get_report_summary(totals)


def validate_filters(filters: frappe._dict) -> None:
	if not filters.get("end_date"):
		frappe.throw(_("As of Date is required."))

	filters.end_date = getdate(filters.end_date)


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Data",
			"width": 480,
		},
		{
			"label": _("Account Type"),
			"fieldname": "account_type",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 180,
		},
	]


def get_data(filters: frappe._dict) -> tuple[list[dict], dict]:
	allowed_outlets = sorted({outlet for outlet in get_current_employee_outlets() if outlet})
	if not allowed_outlets:
		return [], get_totals({}, {})

	validate_outlet_access(filters, allowed_outlets)

	direct_balances = get_direct_balances(filters, allowed_outlets)
	earnings = get_accumulated_profit(filters, allowed_outlets)
	accounts = get_accounts(filters, allowed_outlets, set(direct_balances))

	roll_up_balances(accounts, direct_balances)
	earnings_parent = add_accumulated_profit(
		accounts,
		earnings["profit"],
		earnings["transaction_count"],
	)

	show_empty = cint(filters.get("show_accounts_without_transactions"))
	data = build_rows(accounts, show_empty, earnings, earnings_parent)
	totals = get_totals(direct_balances, earnings)
	data.extend(get_total_rows(totals))

	return data, totals


def validate_outlet_access(filters: frappe._dict, allowed_outlets: list[str]) -> None:
	if filters.get("outlet") and filters.outlet not in allowed_outlets:
		frappe.throw(
			_("You do not have permission to access Outlet {0}.").format(
				frappe.bold(filters.outlet)
			),
			frappe.PermissionError,
		)


def get_direct_balances(filters: frappe._dict, allowed_outlets: list[str]) -> dict[str, dict]:
	conditions, query_filters = get_gl_conditions(filters, allowed_outlets)
	rows = frappe.db.sql(
		f"""
			select
				gle.account,
				coa.root_type,
				sum(coalesce(gle.debit_amount, 0)) as debit_amount,
				sum(coalesce(gle.credit_amount, 0)) as credit_amount,
				count(gle.name) as transaction_count
			from `tabGL Entry` gle
			inner join `tabChart of Account` coa on coa.name = gle.account
			where
				coa.root_type in %(balance_sheet_root_types)s
				and {' and '.join(conditions)}
			group by gle.account, coa.root_type
		""",
		{
			**query_filters,
			"balance_sheet_root_types": BALANCE_SHEET_ROOT_TYPES,
		},
		as_dict=True,
	)

	return {
		row.account: {
			"root_type": row.root_type,
			"debit_amount": flt(row.debit_amount),
			"credit_amount": flt(row.credit_amount),
			"transaction_count": cint(row.transaction_count),
		}
		for row in rows
	}


def get_accumulated_profit(filters: frappe._dict, allowed_outlets: list[str]) -> dict:
	conditions, query_filters = get_gl_conditions(filters, allowed_outlets)
	rows = frappe.db.sql(
		f"""
			select
				coa.root_type,
				sum(coalesce(gle.debit_amount, 0)) as debit_amount,
				sum(coalesce(gle.credit_amount, 0)) as credit_amount,
				count(gle.name) as transaction_count
			from `tabGL Entry` gle
			inner join `tabChart of Account` coa on coa.name = gle.account
			where
				coa.root_type in ('Income', 'Expenses')
				and {' and '.join(conditions)}
			group by coa.root_type
		""",
		query_filters,
		as_dict=True,
	)

	income = 0.0
	expense = 0.0
	transaction_count = 0
	for row in rows:
		amount = get_normal_balance(row.root_type, row.debit_amount, row.credit_amount)
		if row.root_type == "Income":
			income += amount
		elif row.root_type == "Expenses":
			expense += amount
		transaction_count += cint(row.transaction_count)

	return {
		"income": income,
		"expense": expense,
		"profit": income - expense,
		"transaction_count": transaction_count,
	}


def get_gl_conditions(
	filters: frappe._dict, allowed_outlets: list[str]
) -> tuple[list[str], dict]:
	conditions = [
		"gle.outlet in %(allowed_outlets)s",
		"coalesce(gle.is_cancelled, 0) = 0",
		"gle.posting_date <= %(end_date)s",
	]
	query_filters = {
		"allowed_outlets": tuple(allowed_outlets),
		"end_date": filters.end_date,
	}

	if filters.get("outlet"):
		conditions.append("gle.outlet = %(outlet)s")
		query_filters["outlet"] = filters.outlet

	return conditions, query_filters


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
			where root_type in %(balance_sheet_root_types)s
			order by
				case root_type
					when 'Asset' then 0
					when 'Liabilities' then 1
					when 'Equity' then 2
					else 3
				end,
				lft,
				account_code,
				account_name
		""",
		{"balance_sheet_root_types": BALANCE_SHEET_ROOT_TYPES},
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

	# Include the entire path to every permitted or active account so the tree remains valid.
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

	calculated = set()
	calculating = set()

	def calculate(account_name: str) -> dict:
		account = accounts_by_name[account_name]
		if account_name in calculated or account_name in calculating:
			return account

		calculating.add(account_name)
		direct = direct_balances.get(account_name, {})
		account.amount = get_normal_balance(
			account.root_type,
			direct.get("debit_amount"),
			direct.get("credit_amount"),
		)
		account.transaction_count = cint(direct.get("transaction_count"))

		for child_name in children.get(account_name, []):
			child = calculate(child_name)
			account.amount += flt(child.get("amount"))
			account.transaction_count += cint(child.get("transaction_count"))

		calculating.discard(account_name)
		calculated.add(account_name)
		return account

	for account in accounts:
		calculate(account.name)


def add_accumulated_profit(
	accounts: list[dict], profit: float, transaction_count: int
) -> str | None:
	"""Add accumulated profit to an Equity root and return its account name."""
	accounts_by_name = {account.name: account for account in accounts}
	equity_roots = [
		account
		for account in accounts
		if account.root_type == "Equity"
		and account.parent_chart_of_account not in accounts_by_name
	]
	if not equity_roots:
		return None

	equity_root = min(equity_roots, key=get_account_sort_key)
	equity_root.amount = flt(equity_root.get("amount")) + flt(profit)
	equity_root.transaction_count = cint(equity_root.get("transaction_count")) + cint(
		transaction_count
	)
	return equity_root.name


def build_rows(
	accounts: list[dict],
	show_empty: bool,
	earnings: dict | None = None,
	earnings_parent: str | None = None,
) -> list[dict]:
	earnings = earnings or {}
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
		if not show_empty and not cint(account.get("transaction_count")):
			return

		parent = accounts_by_name.get(account.parent_chart_of_account)
		data.append(
			{
				"account": account.name,
				"account_type": account.account_type or account.root_type,
				"root_type": account.root_type,
				"parent_account": parent.name if parent else None,
				"amount": flt(account.get("amount")),
				"indent": indent,
				"is_group": cint(account.is_group or bool(children.get(account_name))),
			}
		)

		for child_name in children.get(account_name, []):
			add_account(child_name, indent + 1)

		if account_name == earnings_parent:
			add_accumulated_profit_row(
				data,
				earnings,
				parent_account=account.name,
				indent=indent + 1,
				show_empty=show_empty,
			)

	for root_name in roots:
		add_account(root_name, 0)

	# Do not silently discard malformed or cyclic account records.
	for account in sorted(accounts, key=get_account_sort_key):
		if account.name not in visited:
			add_account(account.name, 0)

	if not earnings_parent:
		add_accumulated_profit_row(data, earnings, show_empty=show_empty)

	return data


def add_accumulated_profit_row(
	data: list[dict],
	earnings: dict,
	*,
	parent_account: str | None = None,
	indent: int = 0,
	show_empty: bool = False,
) -> None:
	if not show_empty and not cint(earnings.get("transaction_count")):
		return

	data.append(
		{
			"account": _("Accumulated Profit / (Loss)"),
			"account_type": _("Equity"),
			"root_type": "Equity",
			"parent_account": parent_account,
			"amount": flt(earnings.get("profit")),
			"indent": indent,
			"is_group": 0,
			"is_accumulated_profit": 1,
		}
	)


def get_account_sort_key(account: dict) -> tuple:
	return (
		ROOT_TYPE_ORDER.get(account.root_type, len(ROOT_TYPE_ORDER)),
		0 if cint(account.lft) else 1,
		cint(account.lft),
		str(account.account_code or ""),
		str(account.account_name or ""),
	)


def get_normal_balance(root_type: str, debit_amount: float, credit_amount: float) -> float:
	if root_type in ("Liabilities", "Equity", "Income"):
		return flt(credit_amount) - flt(debit_amount)
	return flt(debit_amount) - flt(credit_amount)


def get_totals(direct_balances: dict[str, dict], earnings: dict) -> dict:
	totals = {"assets": 0.0, "liabilities": 0.0, "equity": 0.0}
	root_type_fields = {
		"Asset": "assets",
		"Liabilities": "liabilities",
		"Equity": "equity",
	}
	for balance in direct_balances.values():
		fieldname = root_type_fields.get(balance.get("root_type"))
		if fieldname:
			totals[fieldname] += get_normal_balance(
				balance.get("root_type"),
				balance.get("debit_amount"),
				balance.get("credit_amount"),
			)

	totals["accumulated_profit"] = flt(earnings.get("profit"))
	totals["total_equity"] = totals["equity"] + totals["accumulated_profit"]
	totals["liabilities_and_equity"] = totals["liabilities"] + totals["total_equity"]
	totals["difference"] = totals["assets"] - totals["liabilities_and_equity"]
	return totals


def get_total_rows(totals: dict) -> list[dict]:
	return [
		{},
		make_total_row(_("Total Assets"), totals.get("assets")),
		make_total_row(_("Total Liabilities"), totals.get("liabilities")),
		make_total_row(_("Total Equity"), totals.get("total_equity")),
		make_total_row(
			_("Total Liabilities and Equity"),
			totals.get("liabilities_and_equity"),
		),
		make_total_row(_("Balance Difference"), totals.get("difference"), is_difference=1),
	]


def make_total_row(label: str, amount: float, is_difference: int = 0) -> dict:
	return {
		"account": label,
		"amount": flt(amount),
		"is_total": 1,
		"is_difference": is_difference,
	}


def get_report_summary(totals: dict) -> list[dict]:
	difference = flt(totals.get("difference"))
	return [
		{
			"label": _("Total Assets"),
			"value": flt(totals.get("assets")),
			"datatype": "Currency",
			"indicator": "Blue",
		},
		{
			"label": _("Total Liabilities"),
			"value": flt(totals.get("liabilities")),
			"datatype": "Currency",
			"indicator": "Orange",
		},
		{
			"label": _("Total Equity"),
			"value": flt(totals.get("total_equity")),
			"datatype": "Currency",
			"indicator": "Green",
		},
		{
			"label": _("Difference"),
			"value": difference,
			"datatype": "Currency",
			"indicator": "Green" if abs(difference) < 0.000001 else "Red",
		},
	]


def get_chart(totals: dict) -> dict:
	return {
		"data": {
			"labels": [_("Assets"), _("Liabilities"), _("Equity")],
			"datasets": [
				{
					"name": _("Amount"),
					"values": [
						flt(totals.get("assets")),
						flt(totals.get("liabilities")),
						flt(totals.get("total_equity")),
					],
				}
			],
		},
		"title": _("Balance Sheet Composition"),
		"type": "bar",
		"valuesOverPoints": True,
		"colors": ["#2490ef"],
	}
