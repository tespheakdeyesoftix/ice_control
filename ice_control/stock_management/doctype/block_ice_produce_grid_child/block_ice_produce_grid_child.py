# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BlockIceProduceGridChild(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		block_grid_name: DF.Data | None
		block_grid_number: DF.Link
		column: DF.Int
		cost: DF.Currency
		defected_quantity: DF.Int
		max_produce_quantity: DF.Int
		note: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		produce_data: DF.JSON | None
		product: DF.Link | None
		row: DF.Int
		total_produce_per_day: DF.Int
		total_produce_quantity: DF.Int
		total_remaining_quantity: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "Block Ice Produce Grid Child"
