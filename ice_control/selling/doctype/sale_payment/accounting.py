import frappe
from frappe import _
from frappe.utils import flt

from ice_control.api.accounting import get_account_type, submit_general_ledger_entry


def submit_to_gl_entry(self):
    frappe.db.sql(
        """
        DELETE FROM `tabGL Entry`
        WHERE voucher_type = 'Sale Payment'
            AND voucher_no = %(voucher_no)s
        """,
        {"voucher_no": self.name},
    )

    payment_amount = flt(self.payment_amount)
    write_off_amount = flt(self.write_off_amount)
    if payment_amount <= 0 and write_off_amount <= 0:
        return

    outlet = frappe.get_cached_doc("Outlet", self.outlet)
    receivable_account = outlet.default_receivable_account
    payment_account = self.account_code

    if not receivable_account:
        frappe.throw(
            _("Please set Default Receivable Account for Outlet {0}.").format(
                frappe.bold(self.outlet)
            )
        )
    if not payment_account:
        frappe.throw(_("Payment to Account is required."))
    if payment_account == receivable_account:
        frappe.throw(
            _("Payment to Account and Receivable Account must be different.")
        )

    base_entry = {
        "outlet": self.outlet,
        "posting_date": self.posting_date,
        "voucher_type": "Sale Payment",
        "voucher_no": self.name,
        "reference_doctype": "Sale Payment",
        "reference_docname": self.name,
       "remark":self.note or _(
                                "បានទទួលប្រាក់ពី {0}. លេខវិក្កយបត្រ: {1}"
                            ).format(
                                self.customer_name,
                                ", ".join(
                                    f"{row.sale}: {frappe.format(row.payment_amount,{'fieldtype':'Currency'})}"
                                    for row in self.sales
                                    if row.payment_amount > 0
                                ),
                            ),
    }
    entries = []

    if payment_amount > 0:
        entries.extend(
            [
                {
                    **base_entry,
                    "transaction_type": "Payment",
                    "account": payment_account,
                    "account_type": get_account_type(payment_account),
                    "debit_amount": payment_amount,
                    "against": receivable_account,
                },
                {
                    **base_entry,
                    "account": receivable_account,
                    "account_type": get_account_type(receivable_account),
                    "credit_amount": payment_amount,
                    "against": payment_account,
                    "party_type": "Customer",
                    "party": self.customer,
                    "party_name": self.customer_name,
                    "transaction_type":"Payment",
                    
                },
            ]
        )

    if write_off_amount > 0:
        write_off_sales = [x for x in self.sales if (x.write_off_amount or 0)>0]

        remark = "កាត់ចោលពីបុង " + ", ".join(
            f"{x.sale}: {frappe.format(x.write_off_amount,{'fieldtype':'Currency'})}"
            for x in write_off_sales
        )
        entries.append(
            {
                **base_entry,
                "transaction_type": "Write Off",
                "account": receivable_account,
                "account_type": get_account_type(receivable_account),
                "credit_amount": write_off_amount,
                "against": payment_account,
                "party_type": "Customer",
                "party": self.customer,
                "party_name": self.customer_name,
                "remark":remark


            }
        )

    submit_general_ledger_entry(entries, run_commit=False)
