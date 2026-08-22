# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BlockIceProduceGrid(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		block_grid_name: DF.Data | None
		column: DF.Int
		location: DF.Link
		max_produce_quantity: DF.Int
		naming_series: DF.Literal["GRD.-.####"]
		note: DF.SmallText | None
		product_code: DF.Link
		row: DF.Int
		total_produce_per_day: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "Block Ice Produce Grid"

	def validate(self):
		self.max_produce_quantity = self.total_produce_per_day*self.row*self.column
		if not self.block_grid_name:
			self.block_grid_name = "{} {}x{}".format(self.location, self.row,self.column)
