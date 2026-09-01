# Copyright (c) 2026, Tes Pheakdey and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestSalePayment(IntegrationTestCase):
	"""
	Integration tests for SalePayment.
	Use this class for testing interactions between multiple components.
	"""

	def test_overpayment_uses_full_input_amount_with_exchange_rate(self):
		payment = frappe.new_doc("Sale Payment")
		payment.input_amount = 240
		payment.exchange_rate = 2
		payment.append(
			"sales",
			{
				"sale": "TEST-SALE",
				"sale_balance": 100,
			},
		)

		payment.allocate_payment_amount()

		self.assertEqual(payment.amount_to_pay, 100)
		self.assertEqual(payment.sales[0].payment_amount, 100)
		self.assertEqual(payment.payment_amount, 120)
		self.assertEqual(payment.input_amount, 240)
