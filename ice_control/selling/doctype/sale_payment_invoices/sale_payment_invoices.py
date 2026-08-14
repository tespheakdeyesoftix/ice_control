# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SalePaymentInvoices(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		balance: DF.Currency
		customer: DF.Link | None
		is_pay: DF.Check
		note: DF.SmallText | None
		outlet: DF.Link | None
		paid_amount: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_amount: DF.Currency
		payment_date: DF.Date | None
		payment_type: DF.Link | None
		payment_type_group: DF.Link | None
		posting_date: DF.Date | None
		sale: DF.Link
		sale_balance: DF.Currency
		total_amount: DF.Currency
		write_off_amount: DF.Currency
	# end: auto-generated types

	_DOCTYPE_NAME = "Sale Payment Invoices"
