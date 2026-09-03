# Copyright (c) 2026, Tes Pheakdey and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from ice_control.accounting.report.balance_sheet.balance_sheet import (
	add_accumulated_profit,
	build_rows,
	get_normal_balance,
	get_totals,
	roll_up_balances,
)


class TestBalanceSheet(UnitTestCase):
	def test_normal_balance_follows_account_root_type(self):
		self.assertEqual(get_normal_balance("Asset", 125, 20), 105)
		self.assertEqual(get_normal_balance("Expenses", 125, 20), 105)
		self.assertEqual(get_normal_balance("Liabilities", 20, 125), 105)
		self.assertEqual(get_normal_balance("Equity", 20, 125), 105)
		self.assertEqual(get_normal_balance("Income", 20, 125), 105)

	def test_rollup_and_accumulated_profit_are_reflected_in_equity_tree(self):
		accounts = [
			self.make_account("Equity", "3000", "Equity", "Equity", is_group=1, lft=1),
			self.make_account(
				"Capital", "3100", "Capital", "Equity", parent="Equity", lft=2
			),
		]
		balances = {
			"Capital": self.make_balance("Equity", debit_amount=20, credit_amount=120),
		}

		roll_up_balances(accounts, balances)
		earnings_parent = add_accumulated_profit(accounts, 35, 2)
		with patch(
			"ice_control.accounting.report.balance_sheet.balance_sheet._",
			side_effect=lambda message: message,
		):
			rows = build_rows(
				accounts,
				show_empty=False,
				earnings={"profit": 35, "transaction_count": 2},
				earnings_parent=earnings_parent,
			)

		self.assertEqual(accounts[0].amount, 135)
		self.assertEqual(
			[row["account"] for row in rows],
			["Equity", "Capital", "Accumulated Profit / (Loss)"],
		)
		self.assertEqual(rows[2]["parent_account"], "Equity")
		self.assertEqual(rows[2]["amount"], 35)

	def test_totals_include_profit_in_equity_and_expose_difference(self):
		balances = {
			"Cash": self.make_balance("Asset", debit_amount=200),
			"Payable": self.make_balance("Liabilities", credit_amount=80),
			"Capital": self.make_balance("Equity", credit_amount=100),
		}

		totals = get_totals(balances, {"profit": 20})

		self.assertEqual(totals["assets"], 200)
		self.assertEqual(totals["liabilities"], 80)
		self.assertEqual(totals["total_equity"], 120)
		self.assertEqual(totals["liabilities_and_equity"], 200)
		self.assertEqual(totals["difference"], 0)

		balances["Cash"]["debit_amount"] = 205
		self.assertEqual(get_totals(balances, {"profit": 20})["difference"], 5)

	@staticmethod
	def make_account(
		name: str,
		account_code: str,
		account_name: str,
		root_type: str,
		*,
		parent: str | None = None,
		is_group: int = 0,
		lft: int = 0,
	) -> frappe._dict:
		return frappe._dict(
			name=name,
			account_code=account_code,
			account_name=account_name,
			account_type=None,
			root_type=root_type,
			parent_chart_of_account=parent,
			is_group=is_group,
			outlet="",
			lft=lft,
		)

	@staticmethod
	def make_balance(root_type: str, **values) -> dict:
		balance = {
			"root_type": root_type,
			"debit_amount": 0.0,
			"credit_amount": 0.0,
			"transaction_count": 1,
		}
		balance.update(values)
		return balance
