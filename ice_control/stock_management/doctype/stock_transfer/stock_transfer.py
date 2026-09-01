# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StockTransfer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.stock_management.doctype.stock_transfer_products.stock_transfer_products import StockTransferProducts

		approved_at: DF.Date | None
		approved_by: DF.Link | None
		from_stock_location: DF.Link
		naming_series: DF.Literal["ST.YYYY.-.####"]
		note: DF.SmallText | None
		requested_by: DF.Link | None
		status: DF.Literal["Draft", "Pending", "Approved", "Completed", "Cancelled"]
		stock_transfer_product_items: DF.Table[StockTransferProducts]
		to_stock_location: DF.Link
		transfer_date: DF.Date
	# end: auto-generated types

	_DOCTYPE_NAME = "Stock Transfer"

	def validate(self):
		self.validate_stock_locations()

	def validate_stock_locations(self):
		if self.from_stock_location == self.to_stock_location:
			frappe.throw("From Stock Location and To Stock Location cannot be the same.")
