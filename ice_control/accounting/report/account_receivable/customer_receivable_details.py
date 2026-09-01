# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate

from ice_control.api.utils import get_current_employee_outlets


MAX_TRANSACTIONS = 200


@frappe.whitelist()
def get_customer_receivable_details(customer: str, filters: str | None = None) -> dict:
	frappe.has_permission("Report", "read", doc="Account Receivable", throw=True)
	frappe.has_permission("GL Entry", "read", throw=True)

	filters = _get_filters(filters)
	customer_info = frappe.db.get_value(
		"Customer",
		customer,
		["name", "customer_name", "customer_group", "phone_number_1", "phone_number_2"],
		as_dict=True,
	)
	if not customer_info:
		frappe.throw(_("Customer {0} was not found.").format(frappe.bold(customer)))

	conditions, query_filters = _get_conditions(customer, filters)
	summary = _get_summary(conditions, query_filters)
	transactions, transaction_count = _get_transactions(
		conditions,
		query_filters,
		summary["opening_balance"],
		filters.end_date,
	)
	aging = _get_aging_breakdown(conditions, query_filters, filters.end_date)

	phone_numbers = [
		phone
		for phone in [customer_info.get("phone_number_1"), customer_info.get("phone_number_2")]
		if phone
	]

	return {
		"customer": {
			"code": customer_info.name,
			"name": customer_info.customer_name,
			"group": customer_info.customer_group,
			"phone_number": " / ".join(phone_numbers),
		},
		"filters": {
			"outlet": filters.get("outlet") or _("All Permitted Outlets"),
			"start_date": filters.start_date,
			"end_date": filters.end_date,
		},
		"summary": summary,
		"aging": aging,
		"transactions": transactions,
		"transaction_count": transaction_count,
		"is_truncated": transaction_count > len(transactions),
		"max_transactions": MAX_TRANSACTIONS,
	}


def _get_filters(filters) -> frappe._dict:
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)

	filters = frappe._dict(filters or {})
	if not filters.get("start_date") or not filters.get("end_date"):
		frappe.throw(_("Start Date and End Date are required."))

	filters.start_date = getdate(filters.start_date)
	filters.end_date = getdate(filters.end_date)
	if filters.start_date > filters.end_date:
		frappe.throw(_("Start Date cannot be after End Date."))

	return filters


def _get_conditions(customer: str, filters: frappe._dict) -> tuple[list[str], dict]:
	allowed_outlets = [outlet for outlet in get_current_employee_outlets() if outlet]
	if not allowed_outlets:
		frappe.throw(_("You do not have permission to access any Outlet."), frappe.PermissionError)

	if filters.get("outlet") and filters.outlet not in allowed_outlets:
		frappe.throw(
			_("You do not have permission to access Outlet {0}.").format(
				frappe.bold(filters.outlet)
			),
			frappe.PermissionError,
		)

	conditions = [
		"gle.account_type = 'Receivable'",
		"gle.party_type = 'Customer'",
		"coalesce(gle.is_cancelled, 0) = 0",
		"gle.party = %(customer)s",
		"gle.outlet in %(allowed_outlets)s",
		"gle.posting_date <= %(end_date)s",
	]
	query_filters = {
		"customer": customer,
		"allowed_outlets": tuple(allowed_outlets),
		"start_date": filters.start_date,
		"end_date": filters.end_date,
		"max_transactions": MAX_TRANSACTIONS,
	}

	if filters.get("outlet"):
		conditions.append("gle.outlet = %(outlet)s")
		query_filters["outlet"] = filters.outlet

	return conditions, query_filters


def _get_summary(conditions: list[str], query_filters: dict) -> dict:
	summary = frappe.db.sql(
		f"""
			select
				coalesce(sum(
					case when gle.posting_date < %(start_date)s
						then coalesce(gle.debit_amount, 0) - coalesce(gle.credit_amount, 0)
						else 0
					end
				), 0) as opening_balance,
				coalesce(sum(
					case when gle.posting_date between %(start_date)s and %(end_date)s
						then coalesce(gle.debit_amount, 0)
						else 0
					end
				), 0) as debit_amount,
				coalesce(sum(
					case when gle.posting_date between %(start_date)s and %(end_date)s
						and coalesce(gle.transaction_type, '') != 'Write Off'
						then coalesce(gle.credit_amount, 0)
						else 0
					end
				), 0) as credit_amount,
				coalesce(sum(
					case when gle.posting_date between %(start_date)s and %(end_date)s
						and gle.transaction_type = 'Write Off'
						then coalesce(gle.credit_amount, 0)
						else 0
					end
				), 0) as write_off_amount
			from `tabGL Entry` gle
			where {' and '.join(conditions)}
		""",
		query_filters,
		as_dict=True,
	)[0]

	for fieldname in [
		"opening_balance",
		"debit_amount",
		"credit_amount",
		"write_off_amount",
	]:
		summary[fieldname] = flt(summary.get(fieldname))

	summary["closing_balance"] = (
		summary["opening_balance"]
		+ summary["debit_amount"]
		- summary["credit_amount"]
		- summary["write_off_amount"]
	)
	return summary


def _get_transactions(
	conditions: list[str],
	query_filters: dict,
	opening_balance: float,
	end_date,
) -> tuple[list[dict], int]:
	period_conditions = conditions + ["gle.posting_date >= %(start_date)s"]
	where_clause = " and ".join(period_conditions)

	transaction_count = frappe.db.sql(
		f"""
			select count(*)
			from `tabGL Entry` gle
			where {where_clause}
		""",
		query_filters,
	)[0][0]

	transactions = frappe.db.sql(
		f"""
			select
				gle.name,
				gle.posting_date,
				gle.voucher_type,
				gle.voucher_no,
				gle.account,
				coalesce(gle.debit_amount, 0) as debit_amount,
				coalesce(gle.credit_amount, 0) as credit_amount,
				gle.remark
			from `tabGL Entry` gle
			where {where_clause}
			order by
				gle.posting_date,
				gle.creation,
				gle.name
			limit %(max_transactions)s
		""",
		query_filters,
		as_dict=True,
	)

	running_balance = flt(opening_balance)
	for row in transactions:
		row["debit_amount"] = flt(row.get("debit_amount"))
		row["credit_amount"] = flt(row.get("credit_amount"))
		running_balance += row["debit_amount"] - row["credit_amount"]
		row["running_balance"] = running_balance
		row["age"] = max(date_diff(end_date, row.get("posting_date")), 0)

	return transactions, transaction_count


def _get_aging_breakdown(
	conditions: list[str],
	query_filters: dict,
	end_date,
) -> list[dict]:
	aging_rows = frappe.db.sql(
		f"""
			select
				gle.posting_date,
				sum(coalesce(gle.debit_amount, 0)) as debit_amount,
				sum(coalesce(gle.credit_amount, 0)) as credit_amount
			from `tabGL Entry` gle
			where {' and '.join(conditions)}
			group by gle.posting_date
			order by gle.posting_date
		""",
		query_filters,
		as_dict=True,
	)

	outstanding_debits = []
	unapplied_credit = 0.0

	for row in aging_rows:
		net_amount = flt(row.get("debit_amount")) - flt(row.get("credit_amount"))

		if net_amount > 0:
			applied_advance = min(net_amount, unapplied_credit)
			net_amount -= applied_advance
			unapplied_credit -= applied_advance
			if net_amount:
				outstanding_debits.append(
					{"posting_date": row.get("posting_date"), "amount": net_amount}
				)
		elif net_amount < 0:
			credit_to_apply = abs(net_amount)
			for debit in outstanding_debits:
				if not credit_to_apply:
					break
				applied_credit = min(debit["amount"], credit_to_apply)
				debit["amount"] -= applied_credit
				credit_to_apply -= applied_credit
			unapplied_credit += credit_to_apply

	bucket_values = {
		"current": 0.0,
		"30": 0.0,
		"60": 0.0,
		"90": 0.0,
		"120": 0.0,
		"over_120": 0.0,
	}

	for debit in outstanding_debits:
		amount = flt(debit.get("amount"))
		if not amount:
			continue

		age = date_diff(end_date, debit.get("posting_date"))
		if age <= 0:
			bucket_values["current"] += amount
		elif age <= 30:
			bucket_values["30"] += amount
		elif age <= 60:
			bucket_values["60"] += amount
		elif age <= 90:
			bucket_values["90"] += amount
		elif age <= 120:
			bucket_values["120"] += amount
		else:
			bucket_values["over_120"] += amount

	return [
		{"label": _("Current (0 Days)"), "value": bucket_values["current"]},
		{"label": _("1-30 Days"), "value": bucket_values["30"]},
		{"label": _("31-60 Days"), "value": bucket_values["60"]},
		{"label": _("61-90 Days"), "value": bucket_values["90"]},
		{"label": _("91-120 Days"), "value": bucket_values["120"]},
		{"label": _("120+ Days"), "value": bucket_values["over_120"]},
	]
