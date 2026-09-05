# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from ice_control.api.utils import get_current_employee_outlets


CASH_ACCOUNT_TYPE = "Cash"
MAX_CHART_DAYS = 31


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	data, totals = get_data(filters)
	chart = get_chart(data)
	return get_columns(), data, None, chart, get_report_summary(totals)


def validate_filters(filters: frappe._dict) -> None:
	if not filters.get("outlet"):
		frappe.throw(_("Outlet is required."))

	if not filters.get("start_date") or not filters.get("end_date"):
		frappe.throw(_("Start Date and End Date are required."))

	filters.start_date = getdate(filters.start_date)
	filters.end_date = getdate(filters.end_date)

	if filters.start_date > filters.end_date:
		frappe.throw(_("Start Date cannot be after End Date."))


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 140,
		},
		{
			"label": _("In Flow"),
			"fieldname": "inflow",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"label": _("Out Flow"),
			"fieldname": "outflow",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"label": _("Balance"),
			"fieldname": "balance",
			"fieldtype": "Currency",
			"width": 200,
		},
	]


def get_data(filters: frappe._dict) -> tuple[list[dict], dict]:
	allowed_outlets = sorted({outlet for outlet in get_current_employee_outlets() if outlet})
	if filters.outlet not in allowed_outlets:
		frappe.throw(
			_("You do not have permission to access Outlet {0}.").format(
				frappe.bold(filters.outlet)
			),
			frappe.PermissionError,
		)

	available_accounts = get_cash_accounts(filters.outlet)
	selected_accounts = normalize_selected_accounts(filters.get("account"))
	invalid_accounts = sorted(set(selected_accounts) - set(available_accounts))
	if invalid_accounts:
		frappe.throw(
			_("These Account Codes are not Cash accounts for Outlet {0}: {1}").format(
				frappe.bold(filters.outlet),
				frappe.bold(", ".join(invalid_accounts)),
			)
		)

	accounts = selected_accounts or available_accounts
	if not accounts:
		return build_rows(filters.start_date, filters.end_date, 0, [])

	query_filters = {
		"outlet": filters.outlet,
		"accounts": tuple(accounts),
		"start_date": filters.start_date,
		"end_date": filters.end_date,
	}

	opening_balance = flt(
		frappe.db.sql(
			"""
				select sum(
					coalesce(gle.debit_amount, 0) - coalesce(gle.credit_amount, 0)
				)
				from `tabGL Entry` gle
				where gle.outlet = %(outlet)s
					and gle.account in %(accounts)s
					and coalesce(gle.is_cancelled, 0) = 0
					and gle.posting_date < %(start_date)s
			""",
			query_filters,
		)[0][0]
	)

	daily_flows = frappe.db.sql(
		"""
			select
				gle.posting_date,
				sum(coalesce(gle.debit_amount, 0)) as inflow,
				sum(coalesce(gle.credit_amount, 0)) as outflow
			from `tabGL Entry` gle
			where gle.outlet = %(outlet)s
				and gle.account in %(accounts)s
				and coalesce(gle.is_cancelled, 0) = 0
				and gle.posting_date between %(start_date)s and %(end_date)s
			group by gle.posting_date
			order by gle.posting_date
		""",
		query_filters,
		as_dict=True,
	)

	return build_rows(
		filters.start_date,
		filters.end_date,
		opening_balance,
		daily_flows,
	)


def get_cash_accounts(outlet: str) -> list[str]:
	rows = frappe.db.sql(
		"""
			select name
			from `tabChart of Account`
			where account_type = %(account_type)s
				and coalesce(is_group, 0) = 0
				and (
					coalesce(outlet, '') = ''
					or outlet = %(outlet)s
				)
			order by account_code, account_name, name
		""",
		{
			"account_type": CASH_ACCOUNT_TYPE,
			"outlet": outlet,
		},
	)

	return [row[0] for row in rows]


def normalize_selected_accounts(value) -> list[str]:
	if not value:
		return []

	if isinstance(value, str):
		value = [value]

	return list(
		dict.fromkeys(
			str(account).strip()
			for account in value
			if account and str(account).strip()
		)
	)


def build_rows(
	start_date,
	end_date,
	opening_balance: float,
	daily_flows: list[dict],
) -> tuple[list[dict], dict]:
	start_date = getdate(start_date)
	end_date = getdate(end_date)
	flows_by_date = {getdate(row.get("posting_date")): row for row in daily_flows}
	running_balance = flt(opening_balance)
	total_inflow = 0.0
	total_outflow = 0.0
	data = [
		{
			"posting_date": start_date,
			"inflow": None,
			"outflow": None,
			"balance": running_balance,
			"is_opening": 1,
		}
	]

	posting_date = start_date
	while posting_date <= end_date:
		daily_flow = flows_by_date.get(posting_date, {})
		inflow = flt(daily_flow.get("inflow"))
		outflow = flt(daily_flow.get("outflow"))
		total_inflow += inflow
		total_outflow += outflow
		running_balance += inflow - outflow
		data.append(
			{
				"posting_date": posting_date,
				"inflow": inflow,
				"outflow": outflow,
				"balance": running_balance,
			}
		)
		posting_date = add_days(posting_date, 1)

	totals = {
		"opening_balance": flt(opening_balance),
		"total_inflow": total_inflow,
		"total_outflow": total_outflow,
		"closing_balance": running_balance,
	}
	data.extend(
		[
			{},
			{
				"posting_date": end_date,
				"inflow": total_inflow,
				"outflow": total_outflow,
				"balance": running_balance,
				"is_total": 1,
			},
		]
	)

	return data, totals


def get_report_summary(totals: dict) -> list[dict]:
	closing_balance = totals["closing_balance"]
	return [
		{
			"label": _("Opening Balance"),
			"value": totals["opening_balance"],
			"datatype": "Currency",
		},
	 
		{
			"label": _("Total In Flow"),
			"value": totals["total_inflow"],
			"datatype": "Currency",
		},
	 
		{
			"label": _("Total Out Flow"),
			"value": totals["total_outflow"],
			"datatype": "Currency",
		},
		 
		{
			"label": _("Closing Balance"),
			"value": closing_balance,
			"datatype": "Currency",
			"indicator": "Green" if closing_balance >= 0 else "Red",
		},
	]


def get_chart(data: list[dict]) -> dict | None:
	daily_rows = [
		row
		for row in data
		if row.get("posting_date")
		and not row.get("is_opening")
		and not row.get("is_total")
	]

	if len(daily_rows) > MAX_CHART_DAYS:
		return None

	return {
		"data": {
			"labels": [str(getdate(row["posting_date"])) for row in daily_rows],
			"datasets": [
				{
					"name": _("In Flow"),
					"values": [flt(row.get("inflow")) for row in daily_rows],
				},
				{
					"name": _("Out Flow"),
					"values": [flt(row.get("outflow")) for row in daily_rows],
				},
			],
		},
		"title": _("Cash In Flow and Out Flow"),
		"type": "bar",
		"colors": ["#28a745", "#e24c4b"],
		"barOptions": {"stacked": False},
	}
