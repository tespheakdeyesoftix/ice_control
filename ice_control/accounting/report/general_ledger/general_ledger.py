# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

from ice_control.api.utils import get_current_employee_outlets


PARTY_TYPES = {"Customer", "Employee", "Vendor"}


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

	if filters.get("party") and not filters.get("party_type"):
		frappe.throw(_("Party Type is required when Party is selected."))

	if filters.get("party_type") and filters.party_type not in PARTY_TYPES:
		frappe.throw(_("Party Type must be Customer, Vendor, or Employee."))


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Outlet"),
			"fieldname": "outlet",
			"fieldtype": "Link",
			"options": "Outlet",
			"width": 130,
		},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Chart of Account",
			"width": 190,
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"fieldtype": "Data",
			"width": 105,
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 150,
		},
		{
			"label": _("Party Name"),
			"fieldname": "party_name",
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
			"width": 125,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 150,
		},
		{
			"label": _("Against"),
			"fieldname": "against",
			"fieldtype": "Data",
			"width": 160,
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
			"label": _("Balance"),
			"fieldname": "balance",
			"fieldtype": "Currency",
			"width": 135,
		},
		{
			"label": _("Remark"),
			"fieldname": "remark",
			"fieldtype": "Data",
			"width": 220,
		},
	]


def get_data(filters: frappe._dict) -> tuple[list[dict], dict]:
	allowed_outlets = sorted(
		{outlet for outlet in get_current_employee_outlets() if outlet}
	)
	if not allowed_outlets:
		return [], get_totals(0, [])

	if filters.get("outlet") and filters.outlet not in allowed_outlets:
		frappe.throw(
			_("You do not have permission to access Outlet {0}.").format(
				frappe.bold(filters.outlet)
			),
			frappe.PermissionError,
		)

	conditions = [
		"gle.outlet in %(allowed_outlets)s",
		"coalesce(gle.is_cancelled, 0) = 0",
	]
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

	where_clause = " and ".join(conditions)
	opening_balance = flt(
		frappe.db.sql(
			f"""
				select sum(
					coalesce(gle.debit_amount, 0) - coalesce(gle.credit_amount, 0)
				)
				from `tabGL Entry` gle
				where {where_clause}
					and gle.posting_date < %(start_date)s
			""",
			query_filters,
		)[0][0]
	)

	transactions = frappe.db.sql(
		f"""
			select
				gle.posting_date,
				gle.outlet,
				gle.account,
				gle.party_type,
				gle.party,
				gle.party_name,
				gle.voucher_type,
				gle.voucher_no,
				gle.against,
				coalesce(gle.debit_amount, 0) as debit_amount,
				coalesce(gle.credit_amount, 0) as credit_amount,
				gle.remark
			from `tabGL Entry` gle
			where {where_clause}
				and gle.posting_date between %(start_date)s and %(end_date)s
			order by gle.posting_date, gle.creation, gle.name
		""",
		query_filters,
		as_dict=True,
	)

	running_balance = opening_balance
	data = [
		{
			"posting_date": filters.start_date,
			"account": _("Opening Balance"),
			"balance": opening_balance,
			"is_total": 1,
		}
	]

	for transaction in transactions:
		running_balance += flt(transaction.debit_amount) - flt(
			transaction.credit_amount
		)
		transaction.balance = running_balance
		data.append(transaction)

	totals = get_totals(opening_balance, transactions)
	data.append(
		{
			"posting_date": filters.end_date,
			"account": _("Closing Balance"),
			"debit_amount": totals["debit_amount"],
			"credit_amount": totals["credit_amount"],
			"balance": totals["closing_balance"],
			"is_total": 1,
		}
	)

	return data, totals


def get_totals(opening_balance: float, transactions: list[dict]) -> dict:
	total_debit = sum(flt(row.get("debit_amount")) for row in transactions)
	total_credit = sum(flt(row.get("credit_amount")) for row in transactions)

	return {
		"opening_balance": opening_balance,
		"debit_amount": total_debit,
		"credit_amount": total_credit,
		"closing_balance": opening_balance + total_debit - total_credit,
	}


def get_report_summary(totals: dict) -> list[dict]:
	closing_balance = totals["closing_balance"]
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
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"label": _("Closing"),
			"value": closing_balance,
			"datatype": "Currency",
			"indicator": "Green" if closing_balance >= 0 else "Red",
		},
	]
