# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from ice_control.api.utils import get_default_outlet,money_to_word


class SalePayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.selling.doctype.sale_payment_invoices.sale_payment_invoices import SalePaymentInvoices

		amended_from: DF.Link | None
		amount_to_pay: DF.Currency
		balance: DF.Currency
		balance_virtual: DF.Currency
		created_by: DF.Data | None
		currency: DF.Link | None
		customer: DF.Link
		customer_balance: DF.Currency
		customer_name: DF.Data | None
		enable_multiple_payment_type: DF.Check
		end_date: DF.Date | None
		exchange_rate: DF.Data | None
		input_amount: DF.Float
		naming_series: DF.Literal["SP.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link
		payment_amount: DF.Currency
		payment_amount_in_word: DF.Data | None
		payment_type: DF.Link | None
		photo: DF.AttachImage | None
		pos_sale_payment: DF.Data | None
		posting_date: DF.Date
		sale: DF.Link | None
		sales: DF.Table[SalePaymentInvoices]
		start_date: DF.Date | None
		total_amount_to_pay_virtual: DF.Currency
		total_payment_amount_virtual: DF.Currency
		total_sales_invoice: DF.Int
		write_off_amount: DF.Currency
	# end: auto-generated types

	_DOCTYPE_NAME = "Sale Payment"

	def validate(self):
		# super().validate()

		self.payment_amount_in_word = money_to_word(int(self.payment_amount))
		self.validate_sale_payment_invoices()
		update_totals(self)
		self.validate_payment_amount()

	def before_submit(self):
		self.sales = [
			d for d in self.sales
			if (d.payment_amount or 0) > 0
			or (d.write_off_amount or 0) > 0
		]

		if not self.payment_amount:
			frappe.throw(_("Please enter payment amount"))
		# self.update_account_code()

	def on_cancel(self):
		self.flags.ignore_links = True
		if self.pos_sale_payment:
			frappe.db.sql("delete from `tabPOS Sale Payment` where name=%(pos_sale_payment)s",{"pos_sale_payment":self.pos_sale_payment})

		frappe.db.sql("call sp_update_sale_information('',%(sale_payment)s)",{"sale_payment":self.name})

	def validate_sale_payment_invoices(self):
		for s in self.sales:
			# update payment date to sale payment invoice
			s.payment_date = self.posting_date
			s.customer = self.customer
			# we force to validate sale amount, payment amount and write off amount from db again to
			# ensure sale amount information is correct before save to db
			sale_amount, sale_payment,sale_write_off =frappe.db.get_value("Sale",s.sale,["total_amount","total_payment","total_write_off"])
			s.total_amount = sale_amount or 0
			s.paid_amount = sale_payment or 0
			s.sale_balance = s.total_amount - (s.paid_amount + (sale_write_off or 0))
			s.balance = (s.sale_balance or 0) - ((s.payment_amount or 0) + (s.write_off_amount or 0))
			s.payment_type = self.payment_type

	def validate_payment_amount(self):
		if self.input_amount:
			if (self.input_amount / float(self.exchange_rate))>self.payment_amount:
				frappe.throw(_("សូមបែងចែកចំនួនទឹកប្រាក់តាមវិកយប័ត្រអោយបានត្រឹមត្រូវ"))
		if self.payment_amount>self.amount_to_pay:
			frappe.throw(_("Payment amount cannot greater than amount to pay"))



	# custom doc event
	@frappe.whitelist()
	def get_unpaid_sales(self):
		data = []
		if self.start_date and self.end_date:
			sql = """
				select
					name, posting_date, total_amount,total_payment,balance
					from `tabSale`
					where
						(name = %(sale)s or %(sale)s = '') and
						balance> 0 and
						sale_status = 'Closed' and
						customer=%(customer)s and
						outlet = %(outlet)s  and
						posting_date between %(start_date)s and %(end_date)s
					order by
						posting_date,
						name
				"""
			data = frappe.db.sql(sql,{"outlet":self.outlet,"sale":self.sale or '',"customer": self.customer,"start_date":self.start_date, "end_date":self.end_date},as_dict = 1)
		else:
			sql = """
				select
					name, posting_date, total_amount,total_payment,balance
					from `tabSale`
					where
						(name = %(sale)s or %(sale)s = '') and
						balance> 0 and
						sale_status = 'Closed' and
						customer=%(customer)s and
						outlet = %(outlet)s
					order by
						posting_date,
						name
				"""
			data = frappe.db.sql(sql,{"outlet":self.outlet,"sale":self.sale or '',"customer": self.customer},as_dict = 1)
		return data or []

	@frappe.whitelist()
	def get_customer_credit_balance(self):
		if not self.outlet:
			frappe.throw(_("Please select oulet"))
		sql = "select sum(balance) as balance from `tabSale` where sale_status = 'Closed' and outlet=%(outlet)s and customer=%(customer)s and balance>0"
		data = frappe.db.sql(sql,{"outlet":self.outlet,"customer": self.customer},as_dict = 1)
		if data:
			return data[0].get("balance")
		return 0

	@frappe.whitelist()
	def get_default_outlet(self):
		if self.sale:
			return frappe.db.get_value("Sale",self.sale,"outlet")
		return get_default_outlet()



def update_totals(self):
	self.total_sales_invoice = len([d   for d in self.sales if (d.payment_amount or 0)> 0 or (d.write_off_amount or 0)>0 ])
	self.payment_amount = sum([d.payment_amount or 0 for d in self.sales if (d.payment_amount or 0)> 0 ])
	self.write_off_amount = sum([d.write_off_amount or 0 for d in self.sales if (d.write_off_amount or 0)> 0 ])
	self.balance = self.amount_to_pay - (self.payment_amount + self.write_off_amount)

@frappe.whitelist()
def add_comment_to_sale_after_submit_sale_payment(self):
	for s in self.sales:
		doc = frappe.get_doc("Sale",s.sale)
		comment_text = f"""
			<br/>
			<strong>ទទួលប្រាក់ពីអតិថិជន</strong> <br/>
			បង្កាន់ដៃបង់ប្រាក់៖ <strong>{self.name}</strong><br/>
			កាលបរិច្ឆេទ៖ <strong>{frappe.format(s.posting_date,{"fieldtype":"Date"})}</strong><br/>
			ទឹកប្រាក់ទទួល៖ <strong>{frappe.format(s.payment_amount,{"fieldtype":"Currency"})}</strong><br/>
			ទឹកប្រាក់កាត់ចោល៖ <strong>{frappe.format(s.write_off_amount,{"fieldtype":"Currency"})}</strong>
		"""

		frappe.msgprint(comment_text)
		doc.add_comment('Info', comment_text)
		audit_trail_doc = {
			"doctype":"Audit Trail Log",
			"ref_doctype":"Sale",
			"ref_doc_name":s.sale,
			"outlet":self.outlet,
			"posting_date":frappe.utils.now(),
			"station":"Backend Admin",
			"audit_trail_type":"បង់ប្រាក់",
			"description": comment_text
		}
		frappe.get_doc(audit_trail_doc).insert(ignore_permissions=True,ignore_links=True)

@frappe.whitelist()
def add_comment_to_sale_after_cancel_sale_payment(self):
	for s in self.sales:
		doc = frappe.get_doc("Sale",s.sale)
		comment_text = f"""
			<br/>
			<strong style='color:red'>លុបការទទួលប្រាក់ពីអតិថិជន</strong> <br/>
			បង្កាន់ដៃបង់ប្រាក់៖ <strong>{self.name}</strong><br/>
			កាលបរិច្ឆេទ៖ <strong>{frappe.format(s.posting_date,{"fieldtype":"Date"})}</strong><br/>
			ទឹកប្រាក់ទទួល៖ <strong>{frappe.format(s.payment_amount,{"fieldtype":"Currency"})}</strong><br/>
			ទឹកប្រាក់កាត់ចោល៖ <strong>{frappe.format(s.write_off_amount,{"fieldtype":"Currency"})}</strong>
		"""
		frappe.msgprint(comment_text)
		doc.add_comment('Info', comment_text)

		audit_trail_doc = {
			"doctype":"Audit Trail Log",
			"ref_doctype":"Sale",
			"ref_doc_name":s.sale,
			"outlet":self.outlet,
			"posting_date":frappe.utils.now(),
			"station":"Backend Admin",
			"audit_trail_type":"លុបការបង់ប្រាក់",
			"description": comment_text
		}
		frappe.get_doc(audit_trail_doc).insert(ignore_permissions=True,ignore_links=True)
