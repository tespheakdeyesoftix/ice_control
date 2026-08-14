# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Customer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.customer_management.doctype.customer_free_products.customer_free_products import CustomerFreeProducts
		from ice_control.customer_management.doctype.customer_product_price.customer_product_price import CustomerProductPrice

		address: DF.SmallText | None
		can_edit_bill: DF.Check
		can_show_price: DF.Check
		can_split_bill: DF.Check
		company_name: DF.Data | None
		customer_group: DF.Link
		customer_name: DF.Data
		enabled: DF.Check
		gender: DF.Literal["Male", "Female"]
		is_company: DF.Check
		is_customer: DF.Check
		is_driver: DF.Check
		keyword: DF.Data
		naming_series: DF.Literal["CU.####"]
		phone_number_1: DF.Data | None
		phone_number_2: DF.Data | None
		photo: DF.AttachImage | None
		plate_number: DF.Data | None
		product_prices: DF.Table[CustomerProductPrice]
		table_bvxf: DF.Table[CustomerFreeProducts]
	# end: auto-generated types

	_DOCTYPE_NAME = "Customer"
