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

AGING_BUCKETS = (
	("current", "Current (0 Days)"),
	("days_1_30", "1-30 Days"),
	("days_31_60", "31-60 Days"),
	("days_61_90", "61-90 Days"),
	("days_91_120", "91-120 Days"),
	("days_over_120", "120+ Days"),
)


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	columns = get_columns()
	data, totals = get_data(filters)
	chart = get_chart(totals, filters.get("chart_type"))
	report_summary = get_report_summary(totals)

	return columns, data, None, chart, report_summary


def validate_filters(filters: frappe._dict) -> None:
	if not filters.get("start_date") or not filters.get("end_date"):
		frappe.throw(_("Start Date and End Date are required."))

	filters.start_date = getdate(filters.start_date)
	filters.end_date = getdate(filters.end_date)

	if filters.start_date > filters.end_date:
		frappe.throw(_("Start Date cannot be after End Date."))


def get_columns() -> list[dict]:
	columns = [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Data",
			"width": 300,
		},
		{
			"label": _("Customer Group"),
			"fieldname": "customer_group",
			"fieldtype": "Data",
			"width": 150,
		},
	]

	columns.extend(
		{
			"label": _(label),
			"fieldname": fieldname,
			"fieldtype": "Currency",
			"width": 135,
		}
		for fieldname, label in AGING_BUCKETS
	)
	columns.append(
		{
			"label": _("Total Outstanding"),
			"fieldname": "total_outstanding",
			"fieldtype": "Currency",
			"width": 160,
		}
	)

	return columns


def get_data(filters: frappe._dict) -> tuple[list[dict], dict]:
	allowed_outlets = [outlet for outlet in get_current_employee_outlets() if outlet]
	if not allowed_outlets:
		return [], get_empty_totals()

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

	if filters.get("customer_group"):
		conditions.append("customer.customer_group = %(customer_group)s")
		query_filters["customer_group"] = filters.customer_group

	if filters.get("customer"):
		conditions.append("gle.party = %(customer)s")
		query_filters["customer"] = filters.customer

	ledger_rows = frappe.db.sql(
		f"""
			select
				gle.party as customer_code,
				coalesce(
					customer.customer_name,
					max(nullif(gle.party_name, '')),
					gle.party
				) as customer_name,
				customer.customer_group,
				gle.posting_date,
				sum(coalesce(gle.debit_amount, 0)) as debit_amount,
				sum(
					case when coalesce(gle.transaction_type, '') != 'Write Off'
						then coalesce(gle.credit_amount, 0)
						else 0
					end
				) as credit_amount,
				sum(
					case when gle.transaction_type = 'Write Off'
						then coalesce(gle.credit_amount, 0)
						else 0
					end
				) as write_off_amount
			from `tabGL Entry` gle
			left join `tabCustomer` customer on customer.name = gle.party
			where
				gle.account_type = 'Receivable'
				and gle.party_type = 'Customer'
				and coalesce(gle.is_cancelled, 0) = 0
				and gle.party is not null
				and gle.party != ''
				and gle.posting_date <= %(end_date)s
				and {' and '.join(conditions)}
			group by
				gle.party,
				customer.customer_name,
				customer.customer_group,
				gle.posting_date
			order by
				gle.party,
				gle.posting_date
		""",
		query_filters,
		as_dict=True,
	)

	data, totals = build_aging_data(ledger_rows, filters)
	if data:
		data.extend([{}, get_total_row(totals)])

	return data, totals


def build_aging_data(ledger_rows: list[dict], filters: frappe._dict) -> tuple[list[dict], dict]:
	customers = {}
	totals = get_empty_totals()

	for ledger_row in ledger_rows:
		customer_code = ledger_row.get("customer_code")
		customer = customers.setdefault(
			customer_code,
			{
				"customer_code": customer_code,
				"customer_name": ledger_row.get("customer_name") or customer_code,
				"customer_group": ledger_row.get("customer_group"),
				"outstanding_debits": [],
				"unapplied_credit": 0.0,
			},
		)

		debit_amount = flt(ledger_row.get("debit_amount"))
		credit_amount = flt(ledger_row.get("credit_amount"))
		write_off_amount = flt(ledger_row.get("write_off_amount"))
		posting_date = getdate(ledger_row.get("posting_date"))

		if posting_date < filters.start_date:
			totals["opening_balance"] += debit_amount - credit_amount - write_off_amount
		else:
			totals["debit_amount"] += debit_amount
			totals["credit_amount"] += credit_amount
			totals["write_off_amount"] += write_off_amount

		apply_to_customer_aging(
			customer,
			posting_date,
			debit_amount - credit_amount - write_off_amount,
		)

	data = []
	for customer in customers.values():
		row = get_customer_aging_row(customer, filters.end_date)
		if abs(row["total_outstanding"]) > 0.000001:
			data.append(row)
			for fieldname, _label in AGING_BUCKETS:
				totals[fieldname] += row[fieldname]

	sort_field = {
		"customer_code": "customer_code",
		"customer_name": "customer_name",
	}.get(filters.get("sort_by"), "customer_name")
	data.sort(
		key=lambda row: ((row.get(sort_field) or "").casefold(), row.get("customer_code") or ""),
		reverse=filters.get("sort_order") == "desc",
	)

	totals["closing_balance"] = (
		totals["opening_balance"]
		+ totals["debit_amount"]
		- totals["credit_amount"]
		- totals["write_off_amount"]
	)
	totals["total_outstanding"] = sum(
		totals[fieldname] for fieldname, _label in AGING_BUCKETS
	)

	return data, totals


def apply_to_customer_aging(customer: dict, posting_date, net_amount: float) -> None:
	if net_amount > 0:
		applied_advance = min(net_amount, customer["unapplied_credit"])
		net_amount -= applied_advance
		customer["unapplied_credit"] -= applied_advance
		if net_amount:
			customer["outstanding_debits"].append(
				{"posting_date": posting_date, "amount": net_amount}
			)
	elif net_amount < 0:
		credit_to_apply = abs(net_amount)
		for debit in customer["outstanding_debits"]:
			if not credit_to_apply:
				break

			applied_credit = min(debit["amount"], credit_to_apply)
			debit["amount"] -= applied_credit
			credit_to_apply -= applied_credit

		customer["unapplied_credit"] += credit_to_apply


def get_customer_aging_row(customer: dict, end_date) -> dict:
	row = {
		"customer_code": customer["customer_code"],
		"customer_name": customer["customer_name"],
		"customer": f"{customer['customer_code']} - {customer['customer_name']}",
		"customer_group": customer["customer_group"],
		**{fieldname: 0.0 for fieldname, _label in AGING_BUCKETS},
	}

	for debit in customer["outstanding_debits"]:
		amount = flt(debit.get("amount"))
		if not amount:
			continue

		fieldname = get_aging_bucket(date_diff(end_date, debit.get("posting_date")))
		row[fieldname] += amount

	row["total_outstanding"] = sum(row[fieldname] for fieldname, _label in AGING_BUCKETS)
	return row


def get_aging_bucket(age: int) -> str:
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


def get_empty_totals() -> dict:
	return {
		"opening_balance": 0.0,
		"debit_amount": 0.0,
		"credit_amount": 0.0,
		"write_off_amount": 0.0,
		"closing_balance": 0.0,
		"total_outstanding": 0.0,
		**{fieldname: 0.0 for fieldname, _label in AGING_BUCKETS},
	}


def get_total_row(totals: dict) -> dict:
	return {
		"is_total": 1,
		"customer": _("Total"),
		**{fieldname: totals[fieldname] for fieldname, _label in AGING_BUCKETS},
		"total_outstanding": totals["total_outstanding"],
	}


def get_chart(totals: dict, chart_type=None) -> dict | None:
	chart_values = [totals[fieldname] for fieldname, _label in AGING_BUCKETS]
	if not any(chart_values):
		return None

	chart_type = {
		"percentage": "percentage",
		"bar": "bar",
		"pie": "pie",
	}.get(chart_type, "percentage")

	return {
		"data": {
			"labels": [_(label) for _fieldname, label in AGING_BUCKETS],
			"datasets": [
				{
					"name": _("Outstanding Receivable"),
					"values": chart_values,
				}
			],
		},
		"title": _("Receivable Aging"),
		"type": chart_type,
		"colors": AGING_CHART_COLORS,
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
			"label": _("Debit"),
			"value": totals["debit_amount"],
			"datatype": "Currency",
		},
		{"type": "separator", "value": "-"},
		{
			"label": _("Credit"),
			"value": totals["credit_amount"],
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
