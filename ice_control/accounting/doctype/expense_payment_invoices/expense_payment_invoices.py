# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ExpensePaymentInvoices(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		balance: DF.Currency
		expense: DF.Link | None
		expense_amount: DF.Currency
		expense_balance: DF.Currency
		expense_date: DF.Date | None
		note: DF.SmallText | None
		paid_amount: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_amount: DF.Currency
		write_off_amount: DF.Currency
	# end: auto-generated types

	_DOCTYPE_NAME = "Expense Payment Invoices"
