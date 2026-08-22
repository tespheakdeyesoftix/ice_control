# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TubeIceProduceMachine(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_edit_start_meter_number: DF.Check
		cost: DF.Currency
		end_meter_number: DF.Int
		infected_quantity: DF.Float
		machine_name: DF.Link
		note: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		produce_drop: DF.Int
		product_code: DF.Link
		start_meter_number: DF.Int
		total_produce_quantity: DF.Float
	# end: auto-generated types

	_DOCTYPE_NAME = "Tube Ice Produce Machine"
