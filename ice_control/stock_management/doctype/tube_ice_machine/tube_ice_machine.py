# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TubeIceMachine(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		machine_name: DF.Data | None
		product_code: DF.Link | None
		sort_order: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "Tube Ice Machine"
