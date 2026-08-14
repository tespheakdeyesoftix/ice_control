# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ClosedSellingDate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.selling.doctype.closed_selling_date_items.closed_selling_date_items import ClosedSellingDateItems

		amended_from: DF.Link | None
		closed_selling_date_items: DF.Table[ClosedSellingDateItems]
		naming_series: DF.Literal["CSD.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link
		posting_date: DF.Date
	# end: auto-generated types

	_DOCTYPE_NAME = "Closed Selling Date"
