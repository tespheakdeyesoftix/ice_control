# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SaleProducts(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_change_price: DF.Check
		allow_change_sale_type: DF.Check
		allow_free: DF.Check
		allow_return: DF.Check
		allow_split_bill: DF.Check
		allow_sum_qty: DF.Check
		base_unit: DF.Link | None
		cost: DF.Currency
		free_quantity: DF.Float
		is_inventory_product: DF.Check
		multiplier: DF.Float
		note: DF.SmallText | None
		outlet: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		photo: DF.Data | None
		price: DF.Currency
		product_category: DF.Link | None
		product_code: DF.Link | None
		product_name: DF.Data | None
		product_price: DF.Currency
		quantity: DF.Float
		return_quantity: DF.Float
		revenue_group: DF.Link
		sale_transaction_type: DF.Data | None
		split_quantity: DF.Float
		stock_location: DF.Link | None
		sub_total: DF.Currency
		total_amount: DF.Currency
		total_cost: DF.Currency
		total_sale_quantity: DF.Float
		unit: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Sale Products"
