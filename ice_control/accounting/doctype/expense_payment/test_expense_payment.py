# Copyright (c) 2026, Tes Pheakdey and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from ice_control.accounting.doctype.expense_payment.accounting import submit_to_gl_entry
from ice_control.accounting.doctype.expense_payment.expense_payment import update_expenses


EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestExpensePayment(IntegrationTestCase):
	def test_allocate_payment_amount_with_exchange_rate_and_write_off(self):
		payment = frappe.new_doc("Expense Payment")
		payment.input_amount = 240
		payment.exchange_rate = 2
		payment.append(
			"expenses",
			{
				"expense": "TEST-EXPENSE-1",
				"expense_balance": 100,
				"write_off_amount": 10,
			},
		)
		payment.append(
			"expenses",
			{
				"expense": "TEST-EXPENSE-2",
				"expense_balance": 50,
			},
		)

		payment.allocate_payment_amount()

		self.assertEqual(payment.expenses[0].payment_amount, 90)
		self.assertEqual(payment.expenses[0].balance, 0)
		self.assertEqual(payment.expenses[1].payment_amount, 30)
		self.assertEqual(payment.expenses[1].balance, 20)
		self.assertEqual(payment.amount_to_pay, 150)
		self.assertEqual(payment.total_payment, 120)
		self.assertEqual(payment.total_write_off, 10)
		self.assertEqual(payment.balance, 20)

	def test_update_expense_record_recalculates_rows_and_summary(self):
		payment = frappe.new_doc("Expense Payment")
		payment.append(
			"expenses",
			{
				"expense": "TEST-EXPENSE-1",
				"expense_balance": 100,
				"payment_amount": 30,
				"write_off_amount": 10,
			},
		)
		payment.append(
			"expenses",
			{
				"expense": "TEST-EXPENSE-2",
				"expense_balance": 50,
				"payment_amount": 20,
				"write_off_amount": 5,
			},
		)

		payment.update_expense_record()

		self.assertEqual(payment.expenses[0].balance, 60)
		self.assertEqual(payment.expenses[1].balance, 25)
		self.assertEqual(payment.amount_to_pay, 150)
		self.assertEqual(payment.total_payment, 50)
		self.assertEqual(payment.total_write_off, 15)
		self.assertEqual(payment.balance, 85)

	@patch(
		"ice_control.accounting.doctype.expense_payment.accounting.submit_general_ledger_entry"
	)
	@patch("ice_control.accounting.doctype.expense_payment.accounting.get_account_type")
	@patch("ice_control.accounting.doctype.expense_payment.accounting.frappe.get_cached_doc")
	@patch("ice_control.accounting.doctype.expense_payment.accounting.delete_gl_entries")
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
			"TEST-WRITE-OFF": "Expense",
		}.get
		payment = frappe._dict(
			name="TEST-EXP-PAY-1",
			outlet="TEST-OUTLET",
			posting_date="2026-09-05",
			vendor="TEST-VENDOR",
			vendor_name="Test Vendor",
			account_code="TEST-CASH",
			total_payment=100,
			total_write_off=20,
			note=None,
			expenses=[
				frappe._dict(
					expense="TEST-EXPENSE-1",
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
		self.assertEqual(entries_by_account_and_type[("TEST-WRITE-OFF", "Write Off")]["credit_amount"], 20)

	@patch("ice_control.accounting.doctype.expense_payment.expense_payment.frappe.db.sql")
	def test_update_expenses_aggregates_all_submitted_payments(self, db_sql):
		payment = frappe._dict(
			expenses=[
				frappe._dict(expense="TEST-EXPENSE-1"),
				frappe._dict(expense="TEST-EXPENSE-2"),
			]
		)

		update_expenses(payment)

		db_sql.assert_called_once()
		query, values = db_sql.call_args.args
		self.assertIn("payment.docstatus = 1", query)
		self.assertIn("group by epi.expense", query)
		self.assertEqual(set(values["expenses"]), {"TEST-EXPENSE-1", "TEST-EXPENSE-2"})
