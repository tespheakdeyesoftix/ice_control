# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document			

class Booking(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.selling.doctype.booking_products.booking_products import BookingProducts

		address: DF.SmallText | None
		booking_event: DF.Link
		booking_products: DF.Table[BookingProducts]
		created_by: DF.Data | None
		customer: DF.Link | None
		customer_name: DF.Data | None
		delivery_date: DF.Date | None
		naming_series: DF.Literal["BK.YYYY.-.####"]
		note: DF.SmallText | None
		phone_number: DF.Data
		posting_date: DF.Date | None
		total_amount: DF.Currency
	# end: auto-generated types

	_DOCTYPE_NAME = "Booking"

	def validate(self):
		if not self.created_by:
			self.created_by = frappe.get_cached_value("User",frappe.session.user,"full_name")

		if self.booking_products:
			for p in self.booking_products:
				p.total_amount = (p.price or 0) * (p.quantity or 0)
			
			self.total_amount = sum([x.total_amount or 0 for x in self.booking_products]) 
		else:
			self.total_amount = 0
			