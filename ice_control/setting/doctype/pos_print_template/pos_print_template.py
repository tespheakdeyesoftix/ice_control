# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class POSPrintTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		enabled: DF.Check
		layout_json: DF.JSON | None
		number_of_copies: DF.Int
		orientation: DF.Literal["Portrait", "Landscape"]
		paper_size: DF.Literal["A6", "A5", "A4"]
		schema_version: DF.Int
		template_logo: DF.AttachImage | None
		template_name: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "POS Print Template"
