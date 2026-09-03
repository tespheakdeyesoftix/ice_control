# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, fmt_money


class ClosedSellingDate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.selling.doctype.closed_selling_date_items.closed_selling_date_items import ClosedSellingDateItems

		amended_from: DF.Link | None
		closed_selling_date_items: DF.Table[ClosedSellingDateItems]
		naming_series: DF.Literal["CSD.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link
		posting_date: DF.Date
	# end: auto-generated types

	_DOCTYPE_NAME = "Closed Selling Date"

	def validate(self):
		"""Recalculate system values and persist the user's reconciliation input."""
		context = self._get_close_date_context()
		if not context:
			self.html_preview_close_date_data = ""
			return

		self._sync_close_date_items(context["sections"])
		_add_reconciliation_values(context["sections"], self.closed_selling_date_items)
		self.html_preview_close_date_data = _render_close_date_data(context)

	def before_submit(self):
		if not cint(self.i_am_confirmed_all_data_below_are_correct):
			frappe.throw(_("Confirm that all closing data is correct before submitting."))

		if not self.closed_selling_date_items:
			frappe.throw(_("Closing data is required before submitting."))

		missing_actual_values = [
			row.title for row in self.closed_selling_date_items
			if row.actual_value is None or row.actual_value == ""
		]
		if missing_actual_values:
			frappe.throw(
				_("Enter Actual Value for every closing item before submitting. Missing: {0}").format(
					", ".join(missing_actual_values[:5])
				)
			)

		missing_notes = [
			row.title for row in self.closed_selling_date_items
			if abs(flt(row.total_amount)) > 0.005 and not (row.note or "").strip()
		]
		if missing_notes:
			frappe.throw(
				_("A note is required for every non-zero difference. Missing: {0}").format(
					", ".join(missing_notes[:5])
				)
			)

	@frappe.whitelist()
	def get_close_date_data(self):
		"""Return an editable outlet/day reconciliation preview."""
		context = self._get_close_date_context()
		if not context:
			return ""

		_add_reconciliation_values(context["sections"], self.closed_selling_date_items)
		return _render_close_date_data(context)

	def _sync_close_date_items(self, sections):
		existing_rows = {
			(row.category, row.title): row
			for row in self.closed_selling_date_items
		}
		self.set("closed_selling_date_items", [])

		for section in sections:
			for item in section["items"]:
				existing = existing_rows.get((section["title"], item["title"]))
				actual_value = existing.get("actual_value") if existing else None
				note = existing.get("note") if existing else None
				difference = (
					flt(actual_value) - flt(item["value"])
					if actual_value is not None and actual_value != ""
					else None
				)
				self.append("closed_selling_date_items", {
					"category": section["title"],
					"title": item["title"],
					"fieldtype": item["fieldtype"],
					"value": item["value"],
					"actual_value": actual_value,
					"total_amount": difference,
					"note": note,
				})

	def _get_close_date_context(self):
		if not self.outlet or not self.posting_date:
			return None

		filters = {"outlet": self.outlet, "posting_date": self.posting_date}
		currency = frappe.defaults.get_global_default("currency")

		sales = _query_one(
			"""
				select
					sum(case when sale_status = 'Closed' then 1 else 0 end) as closed_count,
					sum(case when sale_status = 'Draft' then 1 else 0 end) as draft_count,
					sum(case when sale_status = 'Deleted' then 1 else 0 end) as deleted_count,
					sum(case when sale_status = 'Closed' then total_quantity else 0 end) as quantity,
					sum(case when sale_status = 'Closed' then total_free else 0 end) as free_quantity,
					sum(case when sale_status = 'Closed' then total_quantity_return else 0 end) as return_quantity,
					sum(case when sale_status = 'Closed' then total_amount else 0 end) as amount,
					sum(case when sale_status = 'Closed' then total_payment else 0 end) as paid,
					sum(case when sale_status = 'Closed' then balance else 0 end) as balance,
					sum(case when sale_status = 'Closed' then total_write_off else 0 end) as write_off
				from `tabSale`
				where outlet = %(outlet)s and posting_date = %(posting_date)s
			""",
			filters,
		)
		payments = _query_one(
			"""
				select
					sum(case when docstatus = 1 then 1 else 0 end) as submitted_count,
					sum(case when docstatus = 0 then 1 else 0 end) as draft_count,
					sum(case when docstatus = 1 then payment_amount else 0 end) as amount
				from `tabSale Payment`
				where outlet = %(outlet)s and posting_date = %(posting_date)s
			""",
			filters,
		)
		pos_payments = _query_one(
			"""
				select count(p.name) as payment_rows, sum(p.payment_amount) as amount
				from `tabPOS Sale Payment` p
				inner join `tabSale` s on s.name = p.parent
				where s.outlet = %(outlet)s
					and s.posting_date = %(posting_date)s
					and s.sale_status = 'Closed'
			""",
			filters,
		)
		purchases = _query_one(
			"""
				select
					sum(case when docstatus = 1 then 1 else 0 end) as submitted_count,
					sum(case when docstatus = 0 then 1 else 0 end) as draft_count,
					sum(case when docstatus = 1 then total_quantity else 0 end) as quantity,
					sum(case when docstatus = 1 then total_cost else 0 end) as amount,
					sum(case when docstatus = 1 then total_payment else 0 end) as paid,
					sum(case when docstatus = 1 then balance else 0 end) as balance
				from `tabPurchase Orders`
				where outlet = %(outlet)s and posting_date = %(posting_date)s
			""",
			filters,
		)
		purchase_payments = _query_one(
			"""
				select
					sum(case when docstatus = 1 then 1 else 0 end) as submitted_count,
					sum(case when docstatus = 0 then 1 else 0 end) as draft_count,
					sum(case when docstatus = 1 then payment_amount else 0 end) as amount,
					sum(case when docstatus = 1 then total_write_off_amount else 0 end) as write_off
				from `tabPurchase Order Payment`
				where outlet = %(outlet)s and posting_date = %(posting_date)s
			""",
			filters,
		)
		expenses = _query_one(
			"""
				select count(name) as entry_count, sum(total_expense) as amount
				from `tabExpense`
				where outlet = %(outlet)s and posting_date = %(posting_date)s
			""",
			filters,
		)
		transfers = _query_one(
			"""
				select
					sum(case when docstatus = 1 then 1 else 0 end) as submitted_count,
					sum(case when docstatus = 0 then 1 else 0 end) as draft_count,
					sum(case when docstatus = 1 then amount else 0 end) as amount
				from `tabBank Transfer`
				where outlet = %(outlet)s and posting_date = %(posting_date)s
			""",
			filters,
		)
		tube_ice = _query_one(
			"""
				select
					sum(case when docstatus = 1 then 1 else 0 end) as submitted_count,
					sum(case when docstatus = 0 then 1 else 0 end) as draft_count,
					sum(case when docstatus = 1 then total_produce_quantity else 0 end) as produced,
					sum(case when docstatus = 1 then total_produce_drop else 0 end) as dropped,
					sum(case when docstatus = 1 then total_infected_quantity else 0 end) as infected
				from `tabTube Ice Produce`
				where outlet = %(outlet)s and posting_date = %(posting_date)s
			""",
			filters,
		)
		block_ice = _query_one(
			"""
				select
					sum(case when docstatus = 1 then 1 else 0 end) as submitted_count,
					sum(case when docstatus = 0 then 1 else 0 end) as draft_count,
					sum(case when docstatus = 1 then total_produce_quantity else 0 end) as produced,
					sum(case when docstatus = 1 then total_defected_quantity else 0 end) as defected,
					sum(case when docstatus = 1 then total_remaining_quantity else 0 end) as remaining
				from `tabBlock Ice Produce`
				where outlet = %(outlet)s and posting_date = %(posting_date)s
			""",
			filters,
		)
		ledger = _query_one(
			"""
				select count(name) as entry_count, sum(debit_amount) as debit, sum(credit_amount) as credit
				from `tabGL Entry`
				where outlet = %(outlet)s
					and posting_date = %(posting_date)s
					and coalesce(is_cancelled, 0) = 0
			""",
			filters,
		)

		blockers = [
			_make_check(_("Draft sales"), sales.draft_count, _("Close or delete all draft sales.")),
			_make_check(_("Draft sale payments"), payments.draft_count, _("Submit or remove all draft sale payments.")),
			_make_check(_("Draft purchase orders"), purchases.draft_count, _("Submit or remove all draft purchase orders.")),
			_make_check(_("Draft purchase payments"), purchase_payments.draft_count, _("Submit or remove all draft purchase payments.")),
			_make_check(_("Draft cash/bank transfers"), transfers.draft_count, _("Submit or remove all draft transfers.")),
			_make_check(_("Draft tube ice production"), tube_ice.draft_count, _("Submit or remove the draft production record.")),
			_make_check(_("Draft block ice production"), block_ice.draft_count, _("Submit or remove the draft production record.")),
		]
		ledger_difference = flt(ledger.debit) - flt(ledger.credit)
		if abs(ledger_difference) > 0.005:
			blockers.append({
				"label": _("General ledger is not balanced"),
				"count": None,
				"message": _("Debit and credit differ by {0}.").format(
					_fmt_currency(abs(ledger_difference), currency)
				),
				"is_blocker": True,
			})
		blockers = [check for check in blockers if check["is_blocker"]]

		sections = [
			_section(_("Sales"), [
				_metric(_("Closed invoices"), sales.closed_count, "Int", currency),
				_metric(_("Deleted invoices"), sales.deleted_count, "Int", currency),
				_metric(_("Sale quantity"), sales.quantity, "Float", currency),
				_metric(_("Free quantity"), sales.free_quantity, "Float", currency),
				_metric(_("Returned quantity"), sales.return_quantity, "Float", currency),
				_metric(_("Sale amount"), sales.amount, "Currency", currency, True),
				_metric(_("Recorded payment"), sales.paid, "Currency", currency),
				_metric(_("Outstanding balance"), sales.balance, "Currency", currency),
				_metric(_("Write-off"), sales.write_off, "Currency", currency),
			]),
			_section(_("Collections"), [
				_metric(_("Submitted receipts"), payments.submitted_count, "Int", currency),
				_metric(_("Receipt amount"), payments.amount, "Currency", currency, True),
				_metric(_("POS payment rows"), pos_payments.payment_rows, "Int", currency),
				_metric(_("POS tender amount"), pos_payments.amount, "Currency", currency),
			]),
			_section(_("Purchases"), [
				_metric(_("Submitted purchase orders"), purchases.submitted_count, "Int", currency),
				_metric(_("Purchased quantity"), purchases.quantity, "Float", currency),
				_metric(_("Purchase cost"), purchases.amount, "Currency", currency, True),
				_metric(_("Purchase paid"), purchases.paid, "Currency", currency),
				_metric(_("Purchase payable"), purchases.balance, "Currency", currency),
			]),
			_section(_("Payments and expenses"), [
				_metric(_("Submitted purchase payments"), purchase_payments.submitted_count, "Int", currency),
				_metric(_("Purchase payment amount"), purchase_payments.amount, "Currency", currency, True),
				_metric(_("Purchase write-off"), purchase_payments.write_off, "Currency", currency),
				_metric(_("Expense entries"), expenses.entry_count, "Int", currency),
				_metric(_("Expense amount"), expenses.amount, "Currency", currency, True),
			]),
			_section(_("Cash and bank transfers"), [
				_metric(_("Submitted transfers"), transfers.submitted_count, "Int", currency),
				_metric(_("Transfer amount"), transfers.amount, "Currency", currency, True),
			]),
			_section(_("Ice production"), [
				_metric(_("Tube ice produced"), tube_ice.produced, "Float", currency, True),
				_metric(_("Tube ice dropped"), tube_ice.dropped, "Float", currency),
				_metric(_("Tube ice infected"), tube_ice.infected, "Float", currency),
				_metric(_("Block ice produced"), block_ice.produced, "Float", currency, True),
				_metric(_("Block ice defective"), block_ice.defected, "Float", currency),
				_metric(_("Block ice remaining"), block_ice.remaining, "Float", currency),
			]),
			_section(_("General ledger"), [
				_metric(_("GL entries"), ledger.entry_count, "Int", currency),
				_metric(_("Total debit"), ledger.debit, "Currency", currency, True),
				_metric(_("Total credit"), ledger.credit, "Currency", currency, True),
				_metric(_("Difference"), ledger_difference, "Currency", currency),
			]),
		]

		return {
			"sections": sections,
			"blockers": blockers,
			"ready_to_close": not blockers,
			"currency": currency,
			"is_submitted": self.docstatus == 1,
			"generated_at": frappe.utils.format_datetime(frappe.utils.now_datetime()),
		}


def _query_one(query, values):
	rows = frappe.db.sql(query, values, as_dict=True)
	return frappe._dict(rows[0] if rows else {})


def _render_close_date_data(context):
	return frappe.render_template(
		"ice_control/selling/doctype/closed_selling_date/preview_close_date_data.html",
		context,
	)


def _add_reconciliation_values(sections, closing_items):
	saved_rows = {
		(row.category, row.title): row
		for row in closing_items
	}
	for section in sections:
		for item in section["items"]:
			row = saved_rows.get((section["title"], item["title"]))
			actual_value = row.get("actual_value") if row else None
			note = row.get("note") if row else None
			has_actual_value = actual_value is not None and actual_value != ""
			difference = flt(actual_value) - flt(item["value"]) if has_actual_value else None
			item.update({
				"actual_value": actual_value if has_actual_value else "",
				"note": note or "",
				"difference": difference if has_actual_value else "",
				"difference_display": (
					_format_metric_value(difference, item["fieldtype"], item["currency"])
					if has_actual_value else "—"
				),
				"has_difference": has_actual_value and abs(flt(difference)) > 0.005,
			})


def _metric(title, value, fieldtype, currency, emphasized=False):
	value = cint(value) if fieldtype == "Int" else flt(value)
	return {
		"title": title,
		"value": value,
		"display_value": _format_metric_value(value, fieldtype, currency),
		"fieldtype": fieldtype,
		"currency": currency,
		"emphasized": emphasized,
	}


def _format_metric_value(value, fieldtype, currency):
	if fieldtype == "Currency":
		return _fmt_currency(value, currency)
	if fieldtype == "Int":
		return f"{cint(value):,}"
	return f"{flt(value):,.2f}"


def _fmt_currency(value, currency):
	return fmt_money(flt(value), currency=currency)


def _section(title, items):
	return {"title": title, "items": items}


def _make_check(label, count, message):
	count = cint(count)
	return {
		"label": label,
		"count": count,
		"message": message,
		"is_blocker": count > 0,
	}
