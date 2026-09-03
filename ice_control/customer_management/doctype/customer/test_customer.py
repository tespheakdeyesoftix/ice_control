# Copyright (c) 2026, Tes Pheakdey and Contributors
# See license.txt

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from ice_control.customer_management.doctype.customer.customer import (
	get_customer_ar_info,
)


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestCustomer(IntegrationTestCase):
	"""
	Integration tests for Customer.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestCustomerARInfo(UnitTestCase):
	@patch("ice_control.customer_management.doctype.customer.customer.today")
	@patch("ice_control.customer_management.doctype.customer.customer.frappe.db.sql")
	@patch("ice_control.customer_management.doctype.customer.customer.frappe.has_permission")
	def test_returns_opening_today_movements_and_ending_balance(
		self, has_permission, db_sql, mock_today
	):
		mock_today.return_value = "2026-09-03"
		db_sql.return_value = [
			frappe._dict(
				opening=100,
				debit_amount=40,
				credit_amount=25,
				write_off_amount=5,
			)
		]

		result = get_customer_ar_info("CU-0001")

		has_permission.assert_called_once_with(
			"Customer", "read", doc="CU-0001", throw=True
		)
		self.assertEqual(
			db_sql.call_args.args[1],
			{"customer": "CU-0001", "posting_date": date(2026, 9, 3)},
		)
		self.assertEqual(
			result,
			{
				"opening": 100.0,
				"debit_amount": 40.0,
				"credit_amount": 25.0,
				"payment_amount": 25.0,
				"write_off_amount": 5.0,
				"ending_balance": 110.0,
			},
		)
