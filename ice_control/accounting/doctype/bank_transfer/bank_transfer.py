# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BankTransfer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount: DF.Currency
		currency: DF.Link
		exchange_rate: DF.Float
		input_amount: DF.Float
		naming_series: DF.Literal["BTS.####"]
		note: DF.LongText | None
		outlet: DF.Link
		posting_date: DF.Date
		transfer_type: DF.Literal["Bank Transfer", "Direct Transfer"]
		withdraw_by: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Bank Transfer"

	def validate(self):
		if self.amount<=0:
			frappe.throw("Transfer amount cannot be zero")

	@frappe.whitelist()
	def get_currency_exchange_rate(self):
		main_currency = frappe.get_doc("System Settings")
		exchange_rate = frappe.db.sql("select currency_exchange_rate from `tabExchange Rate` where from_currency = '{0}' and to_currency = '{1}' order by posting_date desc limit 1".format(main_currency.currency,self.currency),as_dict=1)
		if len(exchange_rate)>0:
			return exchange_rate[0]["currency_exchange_rate"]
		else:
			return 1
