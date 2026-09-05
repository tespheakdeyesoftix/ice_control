# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from ice_control.api.inventory import get_stock_location_prouct,add_inventory_transaction


class StockEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.stock_management.doctype.stock_entry_products.stock_entry_products import StockEntryProducts

		amended_from: DF.Link | None
		multiplier: DF.Int
		naming_series: DF.Literal["STE.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link | None
		party: DF.DynamicLink | None
		party_name: DF.Data | None
		party_type: DF.Link | None
		posting_date: DF.Date
		reference_no: DF.Data | None
		stock_entry_products: DF.Table[StockEntryProducts]
		stock_entry_type: DF.Link
		stock_location: DF.Link | None
		total_cost: DF.Currency
		total_quantity: DF.Float
	# end: auto-generated types

	_DOCTYPE_NAME = "Stock Entry"
	def validate(self):
	 
		self.validate_stock_entry_products()
		self.validate_stock_entry()


	def validate_stock_entry_products(self):
		for d in self.stock_entry_products:
			# get product_cost

			slp = get_stock_location_prouct(d.product_code, d.default_stock_location or self.stock_location)
			 
			if slp:
				d.cost = slp.get("cost")
			d.total_cost = d.cost * d.quantity

	def validate_stock_entry(self):
		self.total_quantity = sum([d.quantity for d in self.stock_entry_products])
		self.total_cost = sum([d.total_cost for d in self.stock_entry_products])

	def on_submit(self):
		if not self.flags.ignore_submit_to_inventory:
			product_codes = [d for d in self.stock_entry_products if d.is_inventory_product ==1]
			data = [
			{
				"ref_doctype":self.doctype,
				"ref_docname":self.name,
				"posting_date":self.posting_date,
				"stock_location": p.default_stock_location or self.stock_location, #stock location index
				"product_code":p.product_code,
				"unit":p.unit,
				"quantity": p.quantity * self.multiplier,
				"is_calculate_cost":0,
			}
			for p in product_codes
			]
			add_inventory_transaction(data)
