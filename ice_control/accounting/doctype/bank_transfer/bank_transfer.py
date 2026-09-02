# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ice_control.accounting.doctype.bank_transfer.accounting import (
	delete_gl_entries,
	submit_to_gl_entry,
)
from ice_control.api.accounting import get_account_balance
from ice_control.api.utils import validate_close_date


class BankTransfer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount: DF.Currency
		available_amount_to_transfer: DF.Currency
		bank: DF.Link | None
		bank_number: DF.Data | None
		currency: DF.Link
		exchange_rate: DF.Float
		input_amount: DF.Float
		naming_series: DF.Literal["BTS.####"]
		note: DF.SmallText | None
		outlet: DF.Link
		posting_date: DF.Date
		transfer_from: DF.Link
		transfer_to: DF.Link
		transfer_to_account_type: DF.Data | None
		transfer_type: DF.Literal["Bank Transfer", "Cash Transfer", "Owner Withdrawal"]
		withdraw_by: DF.Link | None
		withdraw_by_name: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Bank Transfer"

	def validate(self):
		validate_close_date(self.posting_date, self.creation, self.outlet)

	def before_submit(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Transfer amount must be greater than zero."))
		if not self.transfer_from:
			frappe.throw(_("Transfer From account is required."))
		if not self.transfer_to:
			frappe.throw(_("Transfer To account is required."))
		if self.transfer_from == self.transfer_to:
			frappe.throw(_("Transfer From and Transfer To accounts must be different."))

		self.available_amount_to_transfer = get_account_balance(
			account_code=self.transfer_from,
			outlet=self.outlet,
			date=self.posting_date,
		)

	def on_submit(self):
		submit_to_gl_entry(self)

	def on_cancel(self):
		delete_gl_entries(self)
