# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from ice_control.accounting.doctype.expense_payment.accounting import (
	delete_gl_entries,
	submit_to_gl_entry,
)
from ice_control.api.utils import validate_close_date


class ExpensePayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.accounting.doctype.expense_payment_invoices.expense_payment_invoices import ExpensePaymentInvoices

		account_code: DF.Link | None
		amended_from: DF.Link | None
		amount_to_pay: DF.Currency
		balance: DF.Currency
		currency: DF.Link | None
		current_expense_payable_balance: DF.Currency
		exchange_rate: DF.Currency
		expense: DF.Link | None
		expenses: DF.Table[ExpensePaymentInvoices]
		input_amount: DF.Float
		naming_series: DF.Literal["EXPP.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link
		payable_account: DF.Link | None
		payment_type: DF.Link
		photo: DF.AttachImage | None
		posting_date: DF.Date
		reference_number: DF.Data | None
		total_payment: DF.Currency
		total_write_off: DF.Currency
		vendor: DF.Link
		vendor_name: DF.Data | None
		write_off_account: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Expense Payment"

	def validate(self):
		self.validate_expense_payment_invoices()
		update_expense_summary(self)
		validate_payment_amount(self)
		
		validate_close_date(self.posting_date, self.creation, self.outlet)

	def before_submit(self):
		validate_accounts(self)
		
		self.expenses = [
			expense
			for expense in self.expenses
			if flt(expense.payment_amount) > 0 or flt(expense.write_off_amount) > 0
		]
		update_expense_summary(self)
		if not self.expenses:
			frappe.throw(_("Please enter a Payment Amount or Write Off Amount."))

	def on_submit(self):
		update_expenses(self)
		submit_to_gl_entry(self)

	def on_cancel(self):
		self.flags.ignore_links = True
		delete_gl_entries(self)
		update_expenses(self)

	def validate_expense_payment_invoices(self):
		seen_expenses = set()
		for row in self.expenses:
			if not row.expense:
				continue
			if row.expense in seen_expenses:
				frappe.throw(_("Expense {0} is selected more than once.").format(row.expense))
			seen_expenses.add(row.expense)

			expense = frappe.db.get_value(
				"Expense",
				row.expense,
				[
					"docstatus",
					"posting_date",
					"outlet",
					"vendor",
					"total_expense",
					"total_payment",
					"balance",
				],
				as_dict=True,
			)
			if not expense or expense.docstatus != 1:
				frappe.throw(_("Expense {0} must be submitted before payment.").format(row.expense))
			if expense.outlet != self.outlet or expense.vendor != self.vendor:
				frappe.throw(
					_("Expense {0} does not belong to the selected Outlet and Vendor.").format(
						row.expense
					)
				)
			if getdate(expense.posting_date) > getdate(self.posting_date):
				frappe.throw(
					_("Expense {0} is dated after this payment.").format(row.expense)
				)

			row.expense_date = expense.posting_date
			row.expense_amount = expense.total_expense
			row.paid_amount = expense.total_payment
			row.expense_balance = expense.balance
			row.payment_amount = flt(row.payment_amount)
			row.write_off_amount = flt(row.write_off_amount)
			if row.payment_amount < 0 or row.write_off_amount < 0:
				frappe.throw(_("Payment and Write Off amounts cannot be negative."))
			if row.payment_amount + row.write_off_amount > flt(row.expense_balance):
				frappe.throw(
					_("Payment and Write Off exceed the balance for Expense {0}.").format(
						row.expense
					)
				)
			row.balance = (
				flt(row.expense_balance)
				- row.payment_amount
				- row.write_off_amount
			)

	@frappe.whitelist(methods=["POST"])
	def allocate_payment_amount(self):
		exchange_rate = flt(self.exchange_rate) or 1
		payment_to_allocate = max(flt(self.input_amount) / exchange_rate, 0)

		for expense in self.expenses:
			expense_balance = max(flt(expense.expense_balance), 0)
			write_off_amount = min(
				max(flt(expense.write_off_amount), 0),
				expense_balance,
			)
			amount_after_write_off = expense_balance - write_off_amount
			allocated_amount = (
				min(payment_to_allocate, amount_after_write_off)
				if expense.expense
				else 0
			)

			expense.payment_amount = allocated_amount
			expense.write_off_amount = write_off_amount
			expense.balance = amount_after_write_off - allocated_amount
			payment_to_allocate = max(payment_to_allocate - allocated_amount, 0)

		update_expense_summary(self)

	@frappe.whitelist(methods=["POST"])
	def update_expense_record(self):
		for expense in self.expenses:
			if not expense.expense:
				expense.balance = 0
				continue
			expense.balance = (
				flt(expense.expense_balance)
				- flt(expense.payment_amount)
				- flt(expense.write_off_amount)
			)
		update_expense_summary(self)

	@frappe.whitelist(methods=["POST"])
	def update_summary(self):
		update_expense_summary(self)

	def update_expense_summary(self):
		update_expense_summary(self)

	@frappe.whitelist(methods=["POST"])
	def get_vendor_expense_balance(self):
		if not self.vendor or not self.outlet or not self.posting_date:
			self.current_expense_payable_balance = 0
			return

		self.current_expense_payable_balance = frappe.db.sql(
			"""
				select coalesce(
					sum(coalesce(debit_amount, 0) - coalesce(credit_amount, 0)),
					0
				)
				from `tabGL Entry`
				where party_type = 'Vendor'
					and party = %(vendor)s
					and voucher_type in ('Expense','Expense Payment')
					and account_type = 'Payable'
					and outlet = %(outlet)s
					and posting_date <= %(posting_date)s
					and coalesce(is_cancelled, 0) = 0
			""",
			{
				"vendor": self.vendor,
				"outlet": self.outlet,
				"posting_date": self.posting_date,
			},
		)[0][0]


def update_expense_summary(self):
	expenses = [expense for expense in self.expenses if expense.expense]
	self.amount_to_pay = sum(flt(expense.expense_balance) for expense in expenses)
	self.total_payment = sum(flt(expense.payment_amount) for expense in expenses)
	self.total_write_off = sum(flt(expense.write_off_amount) for expense in expenses)
	exchange_rate = flt(self.exchange_rate) or 1
	entered_payment_amount = max(flt(self.input_amount) / exchange_rate, 0)
	effective_payment_amount = max(self.total_payment, entered_payment_amount)
	self.balance = self.amount_to_pay - effective_payment_amount - self.total_write_off


def update_expenses(self):
	expense_names = [row.expense for row in self.expenses if row.expense]
	if not expense_names:
		return

	frappe.db.sql(
		"""
			update `tabExpense` expense
			left join (
				select
					epi.expense,
					sum(coalesce(epi.payment_amount, 0)) as total_payment,
					sum(coalesce(epi.write_off_amount, 0)) as total_write_off
				from `tabExpense Payment Invoices` epi
				inner join `tabExpense Payment` payment on payment.name = epi.parent
				where epi.expense in %(expenses)s
					and epi.docstatus = 1
					and payment.docstatus = 1
				group by epi.expense
			) totals on totals.expense = expense.name
			set
				expense.total_payment = coalesce(totals.total_payment, 0),
				expense.total_write_off = coalesce(totals.total_write_off, 0),
				expense.balance = expense.total_expense
					- coalesce(totals.total_payment, 0)
					- coalesce(totals.total_write_off, 0),
				expense.status = case
					when expense.docstatus = 0 then 'Draft'
					when expense.docstatus = 2 then 'Cancelled'
					when coalesce(totals.total_payment, 0)
						+ coalesce(totals.total_write_off, 0) >= expense.total_expense
						then 'Paid'
					when coalesce(totals.total_payment, 0)
						+ coalesce(totals.total_write_off, 0) > 0
						then 'Partially Paid'
					else 'Unpaid'
				end
			where expense.name in %(expenses)s
		""",
		{"expenses": tuple(set(expense_names))},
	)


def validate_payment_amount(self):
	if flt(self.balance) < 0:
		frappe.throw(_("Payment amount cannot exceed the amount to pay."))


def validate_accounts(self):
	from ice_control.api.api import (
		get_outlet_default_accounts,
	)

	if not self.account_code:
		self.account_code = frappe.get_cached_value("Has Default Account", {"outlet":self.outlet,"parent":self.payment_type}, "default_purchase_payment_account")

	if not self.account_code:
		frappe.throw("សូមជ្រើសរើសលេខកូដគណនីសាច់ប្រាក់យកទៅបង់ចំណាយ")


	outlet = get_outlet_default_accounts(self.outlet)
	if not self.payable_account:
		self.payable_account = outlet.get("default_payable_account")
		

	if not self.write_off_account:
		self.write_off_account = outlet.get("default_purchase_write_off_account")

	if not self.payable_account:
		frappe.throw(_("សូមជ្រើសរើសគណនីបំណុលសម្រាប់ទីតាំង {0}.").format(self.outlet))
	if flt(self.total_write_off) > 0 and not self.write_off_account:
		frappe.throw(_("សូមជ្រើសរើសគណនីបញ្ចុះតម្លៃ ឬចំណូលសម្រាប់ទីតាំង Outlet {0}.").format(self.outlet))
