# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate

from ice_control.api.utils import get_current_employee_outlets


AGING_CHART_COLORS = [
	"#d6ecff",
	"#b8d8f0",
	"#ffe6a7",
	"#ffc857",
	"#f28c45",
	"#d64545",
]

PARTY_TYPES = {"Customer", "Employee", "Vendor"}


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	columns = get_columns()
	data, totals, chart = get_data(filters)
	report_summary = get_report_summary(totals)

	return columns, data, None, chart, report_summary


def validate_filters(filters: frappe._dict) -> None:
	if not filters.get("start_date") or not filters.get("end_date"):
		frappe.throw(_("Start Date and End Date are required."))

	filters.start_date = getdate(filters.start_date)
	filters.end_date = getdate(filters.end_date)

	if filters.start_date > filters.end_date:
		frappe.throw(_("Start Date cannot be after End Date."))

	if filters.get("party") and not filters.get("party_type"):
		frappe.throw(_("Party Type is required when Party is selected."))

	if filters.get("party_type") and filters.party_type not in PARTY_TYPES:
		frappe.throw(_("Party Type must be Customer, Vendor, or Employee."))


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Data",
			"width": 300,
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Opening Balance"),
			"fieldname": "opening_balance",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Debit"),
			"fieldname": "debit_amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Credit"),
			"fieldname": "credit_amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Write Off"),
			"fieldname": "write_off_amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Closing Balance"),
			"fieldname": "closing_balance",
			"fieldtype": "Currency",
			"width": 150,
		},
	]


def get_data(filters: frappe._dict) -> tuple[list[dict], dict, dict | None]:
	allowed_outlets = sorted(
		{outlet for outlet in get_current_employee_outlets() if outlet}
	)
	if not allowed_outlets:
		return [], get_totals([]), None

	if filters.get("outlet") and filters.outlet not in allowed_outlets:
		frappe.throw(
			_("You do not have permission to access Outlet {0}.").format(
				frappe.bold(filters.outlet)
			),
			frappe.PermissionError,
		)

	conditions = ["gle.outlet in %(allowed_outlets)s"]
	query_filters = {
		"allowed_outlets": tuple(allowed_outlets),
		"start_date": filters.start_date,
		"end_date": filters.end_date,
	}

	if filters.get("outlet"):
		conditions.append("gle.outlet = %(outlet)s")
		query_filters["outlet"] = filters.outlet

	if filters.get("party_type"):
		conditions.append("gle.party_type = %(party_type)s")
		query_filters["party_type"] = filters.party_type

	if filters.get("party"):
		conditions.append("gle.party = %(party)s")
		query_filters["party"] = filters.party

	sort_field = {
		"party_code": "gle.party",
		"party_name": "party_name",
	}.get(filters.get("sort_by"), "party_name")
	sort_direction = "desc" if filters.get("sort_order") == "desc" else "asc"

	data = frappe.db.sql(
		f"""
			select
				gle.party_type,
				gle.party as party_code,
				coalesce(max(nullif(gle.party_name, '')), gle.party) as party_name,
				concat(
					gle.party,
					' - ',
					coalesce(max(nullif(gle.party_name, '')), gle.party)
				) as party,
				sum(
					case when gle.posting_date < %(start_date)s
						then coalesce(gle.credit_amount, 0) - coalesce(gle.debit_amount, 0)
						else 0
					end
				) as opening_balance,
				sum(
					case when gle.posting_date between %(start_date)s and %(end_date)s
						and coalesce(gle.transaction_type, '') != 'Write Off'
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
						and gle.transaction_type = 'Write Off'
						then coalesce(gle.debit_amount, 0)
						else 0
					end
				) as write_off_amount,
				sum(
					coalesce(gle.credit_amount, 0) - coalesce(gle.debit_amount, 0)
				) as closing_balance
			from `tabGL Entry` gle
			where
				gle.account_type = 'Payable'
				and coalesce(gle.is_cancelled, 0) = 0
				and gle.party_type in ('Customer', 'Employee', 'Vendor')
				and gle.party is not null
				and gle.party != ''
				and gle.posting_date <= %(end_date)s
				and {' and '.join(conditions)}
			group by
				gle.party_type,
				gle.party
			having
				abs(opening_balance) > 0.000001
				or abs(debit_amount) > 0.000001
				or abs(credit_amount) > 0.000001
				or abs(write_off_amount) > 0.000001
				or abs(closing_balance) > 0.000001
			order by
				{sort_field} {sort_direction},
				gle.party_type {sort_direction},
				gle.party {sort_direction}
		""",
		query_filters,
		as_dict=True,
	)

	totals = get_totals(data)
	aging_rows = get_aging_rows(conditions, query_filters)
	chart = get_aging_chart(aging_rows, filters.end_date, filters.get("chart_type"))

	data.extend(
		[
			{},
			{
				"is_total": 1,
				"party": _("Total"),
				"opening_balance": totals["opening_balance"],
				"debit_amount": totals["debit_amount"],
				"credit_amount": totals["credit_amount"],
				"write_off_amount": totals["write_off_amount"],
				"closing_balance": totals["closing_balance"],
			},
		]
	)

	return data, totals, chart


def get_totals(data: list[dict]) -> dict:
	total_opening = sum(flt(row.get("opening_balance")) for row in data)
	total_debit = sum(flt(row.get("debit_amount")) for row in data)
	total_credit = sum(flt(row.get("credit_amount")) for row in data)
	total_write_off = sum(flt(row.get("write_off_amount")) for row in data)

	return {
		"opening_balance": total_opening,
		"debit_amount": total_debit,
		"credit_amount": total_credit,
		"write_off_amount": total_write_off,
		"closing_balance": total_opening + total_credit - total_debit - total_write_off,
	}


def get_report_summary(totals: dict) -> list[dict]:
	balance = totals["closing_balance"]

	return [
		{
			"label": _("Opening"),
			"value": totals["opening_balance"],
			"datatype": "Currency",
		},
		{"type": "separator", "value": "+"},
		{
			"label": _("Credit"),
			"value": totals["credit_amount"],
			"datatype": "Currency",
		},
		{"type": "separator", "value": "-"},
		{
			"label": _("Debit"),
			"value": totals["debit_amount"],
			"datatype": "Currency",
		},
		{"type": "separator", "value": "-"},
		{
			"label": _("Write Off"),
			"value": totals["write_off_amount"],
			"datatype": "Currency",
		},
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"label": _("Balance"),
			"value": balance,
			"datatype": "Currency",
			"indicator": "Green" if balance >= 0 else "Red",
		},
	]


def get_aging_rows(conditions: list[str], query_filters: dict) -> list[dict]:
	return frappe.db.sql(
		f"""
			select
				gle.party_type,
				gle.party,
				gle.posting_date,
				sum(coalesce(gle.debit_amount, 0)) as debit_amount,
				sum(coalesce(gle.credit_amount, 0)) as credit_amount
			from `tabGL Entry` gle
			where
				gle.account_type = 'Payable'
				and coalesce(gle.is_cancelled, 0) = 0
				and gle.party_type in ('Customer', 'Employee', 'Vendor')
				and gle.party is not null
				and gle.party != ''
				and gle.posting_date <= %(end_date)s
				and {' and '.join(conditions)}
			group by
				gle.party_type,
				gle.party,
				gle.posting_date
			order by
				gle.party_type,
				gle.party,
				gle.posting_date
		""",
		query_filters,
		as_dict=True,
	)


def get_aging_chart(aging_rows: list[dict], end_date, chart_type=None) -> dict | None:
	outstanding_credits = {}
	unapplied_debits = {}

	for row in aging_rows:
		party_key = (row.get("party_type"), row.get("party"))
		net_amount = flt(row.get("credit_amount")) - flt(row.get("debit_amount"))
		party_credits = outstanding_credits.setdefault(party_key, [])

		if net_amount > 0:
			advance = unapplied_debits.get(party_key, 0)
			applied_advance = min(net_amount, advance)
			net_amount -= applied_advance
			unapplied_debits[party_key] = advance - applied_advance

			if net_amount:
				party_credits.append(
					{
						"posting_date": row.get("posting_date"),
						"amount": net_amount,
					}
				)
		elif net_amount < 0:
			debit_to_apply = abs(net_amount)

			for credit in party_credits:
				if not debit_to_apply:
					break

				applied_debit = min(credit["amount"], debit_to_apply)
				credit["amount"] -= applied_debit
				debit_to_apply -= applied_debit

			if debit_to_apply:
				unapplied_debits[party_key] = (
					unapplied_debits.get(party_key, 0) + debit_to_apply
				)

	buckets = {
		"current": 0.0,
		"30": 0.0,
		"60": 0.0,
		"90": 0.0,
		"120": 0.0,
		"over_120": 0.0,
	}

	for party_credits in outstanding_credits.values():
		for credit in party_credits:
			amount = flt(credit.get("amount"))
			if not amount:
				continue

			age = date_diff(end_date, credit.get("posting_date"))
			if age <= 0:
				buckets["current"] += amount
			elif age <= 30:
				buckets["30"] += amount
			elif age <= 60:
				buckets["60"] += amount
			elif age <= 90:
				buckets["90"] += amount
			elif age <= 120:
				buckets["120"] += amount
			else:
				buckets["over_120"] += amount

	chart_values = [
		buckets["current"],
		buckets["30"],
		buckets["60"],
		buckets["90"],
		buckets["120"],
		buckets["over_120"],
	]

	if not any(chart_values):
		return None

	chart_type = {
		"percentage": "percentage",
		"bar": "bar",
		"pie": "pie",
	}.get(chart_type, "percentage")

	return {
		"data": {
			"labels": [
				_("Current (0 Days)"),
				_("1-30 Days"),
				_("31-60 Days"),
				_("61-90 Days"),
				_("91-120 Days"),
				_("120+ Days"),
			],
			"datasets": [
				{
					"name": _("Outstanding Payable"),
					"values": chart_values,
				}
			],
		},
		"title": _("Payable Aging"),
		"type": chart_type,
		"colors": AGING_CHART_COLORS,
	}
