# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BusinessInformation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.setting.doctype.closed_selling_date_doctype.closed_selling_date_doctype import ClosedSellingDateDoctype

		address: DF.SmallText | None
		base_exchange_currency: DF.Link | None
		block_ice_outlet: DF.Link | None
		business_name_en: DF.Data | None
		business_name_kh: DF.Data | None
		closed_doctypes: DF.Table[ClosedSellingDateDoctype]
		currency_format: DF.Data | None
		currency_symbol: DF.Data | None
		default_currency: DF.Link | None
		number_of_day_seller_can_view_sale_list: DF.Int
		phone_number_1: DF.Data | None
		phone_number_2: DF.Data | None
		photo: DF.AttachImage | None
		property_code: DF.Data | None
		receipt_logo: DF.AttachImage | None
		report_server_token: DF.SmallText | None
		report_service_url: DF.Data | None
		second_currency: DF.Link | None
		server_report_url: DF.Data | None
		tube_ice_outlet: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Business Information"
