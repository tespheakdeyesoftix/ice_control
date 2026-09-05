# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class StockEntryType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_change_cost: DF.Check
		multiplier: DF.Int
		stock_entry_type: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Stock Entry Type"
