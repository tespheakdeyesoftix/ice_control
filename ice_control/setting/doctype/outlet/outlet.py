# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ice_control.api.utils import get_current_employee_outlets

class Outlet(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		default_income_account: DF.Link | None
		default_payable_account: DF.Link | None
		default_receivable_account: DF.Link | None
		default_stock_location: DF.Link | None
		default_unit: DF.Link | None
		enabled: DF.Check
		outlet_name: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Outlet"



def get_permission_query_conditions(user=None):
    user = user or frappe.session.user

    if user == "Administrator":
        return None

    access_outlets = get_current_employee_outlets()

    if not access_outlets:
        return "1 = 0"

    outlets = ", ".join(frappe.db.escape(outlet) for outlet in access_outlets)

    return f"`tabOutlet`.`name` IN ({outlets})"
	

