# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from ice_control.api.accounting import submit_general_ledger_entry,cancel_general_ledger_entery

class JournalEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.accounting.doctype.journal_entry_account.journal_entry_account import JournalEntryAccount

		account_entries: DF.Table[JournalEntryAccount]
		amended_from: DF.Link | None
		balance: DF.Currency
		naming_series: DF.Literal["JE.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link
		party: DF.DynamicLink | None
		party_name: DF.Data | None
		party_type: DF.Link | None
		photo: DF.AttachImage | None
		posting_date: DF.Date
		reference: DF.Data | None
		total_credit: DF.Currency
		total_debit: DF.Currency
	# end: auto-generated types

	_DOCTYPE_NAME = "Journal Entry"

	def validate(self):
		validate_account_debit_credit(self)
		self.total_debit = sum(d.debit for d in self.get("account_entries"))
		self.total_credit = sum(d.credit for d in self.get("account_entries"))

		if self.total_credit == 0 or self.total_debit == 0:
			frappe.throw(_("Credit and Debit must be greater than zero"))
		self.balance = self.total_debit - self.total_credit
		if self.balance != 0:
			frappe.throw(_("Balance must be zero"))

		for d in  self.account_entries:
			if d.party:
				fieldname =get_party_name_field(d.party_type)
				if fieldname:
					d.party_name = frappe.get_cached_value(d.party_type, d.party, fieldname)
			else:
				d.party_name = None

		fieldname =get_party_name_field(self.party_type)
		if fieldname:
			self.party_name = frappe.get_cached_value(self.party_type, self.party, get_party_name_field(self.party_type))

	def before_submit(self):
		for d in  self.account_entries:
			if d.party:
				fieldname =get_party_name_field(d.party_type)
				d.party_name = frappe.get_cached_value(d.party_type, d.party, fieldname)
			else:
				d.party_name = None


	def on_submit(self):
		submit_to_general_ledger_entry(self)

	def on_cancel(self):
		self.flags.ignore_links = 1
		cancel_general_ledger_entery("Journal Entry", self.name)

def validate_account_debit_credit(self):
	msg = ""
	for a in self.account_entries:
		if a.debit > 0 and a.credit > 0:
			msg += "<b>Row {0}</b>: You cannot credit and debit same account at the same time.".format(a.idx)
	if msg:
		frappe.throw(msg)


def get_party_name_field(party_type):
	if party_type:
		if party_type == "Vendor":
			return "vendor_name"
		elif party_type == "Customer":
			return "customer_name"
		elif party_type == "Employee":
			return "employee_name"
		else:
			frappe.throw(_("Party type must be either Customer or Vendor or Employee"))
	else:
		return None
def submit_to_general_ledger_entry(self):
	docs = []
	for i in self.account_entries:
		doc = {
			"doctype":"GL Entry",
			"outlet":self.outlet,
			"posting_date":self.posting_date,
			"account":i.account,
			"debit_amount":i.debit,
			"credit_amount":i.credit,

			"againt":(i.party or "") + " - " + (i.party_name or ""),
			"voucher_type":"Journal Entry",
			"voucher_no":self.name,
			"party_type":i.party_type,
			"party":i.party,
			"remark":i.description
		}

		docs.append(doc)

	submit_general_ledger_entry(docs=docs)
