# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PurchaseOrderPaymentInvoices(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		balance: DF.Currency
		exchange_rate: DF.Float
		note: DF.SmallText | None
		outlet: DF.Link | None
		paid_amount: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party: DF.DynamicLink | None
		party_type: DF.Literal["Vendor", "Employee", "Customer"]
		payment_amount: DF.Currency
		payment_date: DF.Date | None
		payment_type: DF.Link | None
		payment_type_group: DF.Link | None
		posting_date: DF.Date | None
		purchase_amount: DF.Currency
		purchase_order: DF.Link
		purchase_order_balance: DF.Currency
		write_off_amount: DF.Float
	# end: auto-generated types

	_DOCTYPE_NAME = "Purchase Order Payment Invoices"
