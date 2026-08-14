# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Vendor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.purchase_order.doctype.vendor_product_price.vendor_product_price import VendorProductPrice

		address: DF.SmallText | None
		phone_number_1: DF.Data | None
		phone_number_2: DF.Data | None
		product_price: DF.Table[VendorProductPrice]
		vendor_group: DF.Link
		vendor_name: DF.Data
	# end: auto-generated types

	_DOCTYPE_NAME = "Vendor"
