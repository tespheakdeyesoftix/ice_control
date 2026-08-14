# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Outlet(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		default_stock_location: DF.Link | None
		default_unit: DF.Link | None
		enabled: DF.Check
		outlet_name: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Outlet"
