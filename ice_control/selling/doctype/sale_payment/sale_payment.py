# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SalePayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.selling.doctype.sale_payment_invoices.sale_payment_invoices import SalePaymentInvoices

		amended_from: DF.Link | None
		amount_to_pay: DF.Currency
		balance: DF.Currency
		balance_virtual: DF.Currency
		currency: DF.Link | None
		customer: DF.Link
		customer_balance: DF.Currency
		customer_name: DF.Data | None
		enable_multiple_payment_type: DF.Check
		end_date: DF.Date | None
		exchange_rate: DF.Data | None
		input_amount: DF.Float
		naming_series: DF.Literal["SP.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link
		payment_amount: DF.Currency
		payment_amount_in_word: DF.Data | None
		payment_type: DF.Link | None
		photo: DF.AttachImage | None
		pos_sale_payment: DF.Data | None
		posting_date: DF.Date
		sale: DF.Link | None
		start_date: DF.Date | None
		table_pjmt: DF.Table[SalePaymentInvoices]
		total_amount_to_pay: DF.Currency
		total_payment_amount: DF.Currency
		total_sales_invoice: DF.Int
		write_off_amount: DF.Currency
	# end: auto-generated types

	_DOCTYPE_NAME = "Sale Payment"
