# Copyright (c) 2026, Tes Pheakdey and Contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase

from ice_control.accounting.report.trail_balance.trail_balance import (
	build_rows,
	get_totals,
	roll_up_balances,
	split_balance,
)


class TestTrailBalance(UnitTestCase):
	def test_split_balance_uses_debit_for_positive_and_credit_for_negative(self):
		self.assertEqual(split_balance(125), (125, 0.0))
		self.assertEqual(split_balance(-80), (0.0, 80))
		self.assertEqual(split_balance(0), (0.0, 0.0))

	def test_roll_up_preserves_debit_and_credit_sides(self):
		accounts = [
			self.make_account("Assets", "1000", "Assets", is_group=1, lft=1),
			self.make_account("Cash", "1100", "Cash", parent="Assets", lft=2),
			self.make_account(
				"Accumulated Depreciation",
				"1200",
				"Accumulated Depreciation",
				parent="Assets",
				lft=3,
			),
		]
		balances = {
			"Cash": self.make_balance(opening_debit=100, debit_amount=20, closing_debit=120),
			"Accumulated Depreciation": self.make_balance(
				opening_credit=25,
				credit_amount=5,
				closing_credit=30,
			),
		}

		roll_up_balances(accounts, balances)

		assets = accounts[0]
		self.assertEqual(assets.opening_debit, 100)
		self.assertEqual(assets.opening_credit, 25)
		self.assertEqual(assets.debit_amount, 20)
		self.assertEqual(assets.credit_amount, 5)
		self.assertEqual(assets.closing_debit, 120)
		self.assertEqual(assets.closing_credit, 30)

		rows = build_rows(accounts, show_empty=False)
		self.assertEqual(
			[row["account"] for row in rows],
			["Assets", "Cash", "Accumulated Depreciation"],
		)
		self.assertEqual(rows[1]["parent_account"], "1000")

	def test_totals_use_direct_accounts_only_and_expose_imbalance(self):
		balances = {
			"Cash": self.make_balance(
				opening_debit=100,
				debit_amount=50,
				credit_amount=10,
				closing_debit=140,
			),
			"Equity": self.make_balance(
				opening_credit=100,
				debit_amount=10,
				credit_amount=50,
				closing_credit=140,
			),
		}

		totals = get_totals(balances)

		self.assertEqual(totals["opening_debit"], totals["opening_credit"])
		self.assertEqual(totals["debit_amount"], totals["credit_amount"])
		self.assertEqual(totals["closing_debit"], totals["closing_credit"])
		self.assertEqual(totals["closing_difference"], 0)

		balances["Equity"]["closing_credit"] = 135
		self.assertEqual(get_totals(balances)["closing_difference"], 5)

	@staticmethod
	def make_account(
		name: str,
		account_code: str,
		account_name: str,
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
			root_type="Asset",
			parent_chart_of_account=parent,
			is_group=is_group,
			outlet="",
			lft=lft,
		)

	@staticmethod
	def make_balance(**values) -> dict:
		balance = {
			"opening_debit": 0.0,
			"opening_credit": 0.0,
			"debit_amount": 0.0,
			"credit_amount": 0.0,
			"closing_debit": 0.0,
			"closing_credit": 0.0,
			"transaction_count": 1,
			"has_activity": True,
		}
		balance.update(values)
		return balance
