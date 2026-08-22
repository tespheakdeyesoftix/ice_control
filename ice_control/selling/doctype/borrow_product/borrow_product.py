# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BorrowProduct(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		balance: DF.Float
		borrow_account: DF.Link | None
		borrow_reference_name: DF.Link | None
		cost: DF.Currency
		customer: DF.Link
		customer_name: DF.Data | None
		last_return_date: DF.Date | None
		naming_series: DF.Literal["BR.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link
		photo: DF.AttachImage | None
		posting_date: DF.Date
		product: DF.Link
		product_name: DF.Data | None
		quantity: DF.Float
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		return_quantity: DF.Float
		sale_product_id: DF.Data | None
		stock_location: DF.Link | None
		total_cost: DF.Currency
		transaction_type: DF.Literal["Borrow", "Return"]
		unit: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Borrow Product"
