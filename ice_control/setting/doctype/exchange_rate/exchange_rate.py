# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ExchangeRate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		currency_exchange_rate: DF.Data
		from_currency: DF.Link
		posting_date: DF.Date
		to_currency: DF.Link
	# end: auto-generated types

	_DOCTYPE_NAME = "Exchange Rate"
