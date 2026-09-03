# Copyright (c) 2026, Tes Pheakdey and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from ice_control.purchase_order.doctype.purchase_order_payment.accounting import (
	submit_to_gl_entry,
)


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestPurchaseOrderPayment(IntegrationTestCase):
	"""
	Integration tests for PurchaseOrderPayment.
	Use this class for testing interactions between multiple components.
	"""

	@patch(
		"ice_control.purchase_order.doctype.purchase_order_payment.purchase_order_payment._get_party_account_payable_balance"
	)
	def test_get_party_account_payable_balance(self, get_payable_balance):
		get_payable_balance.return_value = -125
		payment = frappe.new_doc("Purchase Order Payment")
		payment.party_type = "Vendor"
		payment.party = "TEST-VENDOR"
		payment.outlet = "TEST-OUTLET"
		payment.posting_date = "2026-09-02"

		payment.get_party_account_payable_balance()

		get_payable_balance.assert_called_once_with(
			party_type="Vendor",
			party="TEST-VENDOR",
			outlet="TEST-OUTLET",
			date="2026-09-02",
		)
		self.assertEqual(payment.party_payable_balance, -125)

	def test_before_submit_requires_positive_payment_amount(self):
		for payment_amount in (0, -1):
			with self.subTest(payment_amount=payment_amount):
				payment = frappe.new_doc("Purchase Order Payment")
				payment.payment_amount = payment_amount

				with self.assertRaisesRegex(
					frappe.ValidationError,
					"Payment Amount must be greater than zero",
				):
					payment.before_submit()

	def test_allocate_payment_amount_with_exchange_rate_and_write_off(self):
		payment = frappe.new_doc("Purchase Order Payment")
		payment.input_amount = 240
		payment.exchange_rate = 2
		payment.append(
			"purchase_orders",
			{
				"purchase_order": "TEST-PO-1",
				"purchase_order_balance": 100,
				"write_off_amount": 10,
			},
		)
		payment.append(
			"purchase_orders",
			{
				"purchase_order": "TEST-PO-2",
				"purchase_order_balance": 50,
			},
		)

		payment.allocate_payment_amount()

		self.assertEqual(payment.purchase_orders[0].payment_amount, 90)
		self.assertEqual(payment.purchase_orders[0].balance, 0)
		self.assertEqual(payment.purchase_orders[1].payment_amount, 30)
		self.assertEqual(payment.purchase_orders[1].balance, 20)
		self.assertEqual(payment.amount_to_pay, 150)
		self.assertEqual(payment.payment_amount, 120)
		self.assertEqual(payment.total_write_off_amount, 10)
		self.assertEqual(payment.balance, 20)
		self.assertEqual(payment.total_invoices, 2)
		self.assertEqual(payment.input_amount, 240)

	@patch(
		"ice_control.purchase_order.doctype.purchase_order_payment.accounting.submit_general_ledger_entry"
	)
	@patch(
		"ice_control.purchase_order.doctype.purchase_order_payment.accounting.get_account_type"
	)
	@patch(
		"ice_control.purchase_order.doctype.purchase_order_payment.accounting.frappe.get_cached_doc"
	)
	@patch(
		"ice_control.purchase_order.doctype.purchase_order_payment.accounting.delete_gl_entries"
	)
	def test_submit_to_gl_entry_posts_balanced_payment_and_write_off(
		self,
		delete_entries,
		get_cached_doc,
		get_account_type,
		submit_entries,
	):
		get_cached_doc.return_value = frappe._dict(
			default_payable_account="TEST-AP",
			default_purchase_write_off_account="TEST-WRITE-OFF",
		)
		get_account_type.side_effect = {
			"TEST-AP": "Payable",
			"TEST-CASH": "Cash",
			"TEST-WRITE-OFF": "Expense Account",
		}.get
		payment = frappe._dict(
			name="TEST-POP-1",
			outlet="TEST-OUTLET",
			posting_date="2026-09-02",
			party_type="Vendor",
			party="TEST-VENDOR",
			party_name="Test Vendor",
			payment_amount=100,
			total_write_off_amount=20,
			payment_from_account="TEST-CASH",
			note=None,
			purchase_orders=[
				frappe._dict(
					purchase_order="TEST-PO-1",
					payment_amount=100,
					write_off_amount=20,
				)
			],
		)

		submit_to_gl_entry(payment)

		delete_entries.assert_called_once_with(payment)
		submit_entries.assert_called_once()
		entries = submit_entries.call_args.args[0]
		self.assertFalse(submit_entries.call_args.kwargs["run_commit"])
		self.assertEqual(len(entries), 4)
		self.assertEqual(sum(row.get("debit_amount") or 0 for row in entries), 120)
		self.assertEqual(sum(row.get("credit_amount") or 0 for row in entries), 120)

		entries_by_account_and_type = {
			(row["account"], row["transaction_type"]): row for row in entries
		}
		self.assertEqual(entries_by_account_and_type[("TEST-AP", "Payment")]["debit_amount"], 100)
		self.assertEqual(entries_by_account_and_type[("TEST-CASH", "Payment")]["credit_amount"], 100)
		self.assertEqual(entries_by_account_and_type[("TEST-AP", "Write Off")]["debit_amount"], 20)
		self.assertEqual(
			entries_by_account_and_type[("TEST-WRITE-OFF", "Write Off")]["credit_amount"],
			20,
		)
