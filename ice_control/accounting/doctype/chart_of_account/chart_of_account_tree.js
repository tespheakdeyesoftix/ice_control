frappe.treeview_settings['Chart of Account'] = {
    breadcrumb: 'Accounting',
    title: 'Chart of Accounts',
    fields: [
        {
            fieldtype: 'Data', fieldname: 'account_code',
            label: 'Account Code', reqd: true
        },
        {
            fieldtype: 'Data', fieldname: 'account_name',
            label: 'Account Name', reqd: true
        },
        {
            fieldtype: 'Data', fieldname: 'account_name_kh',
            label: 'Account Name (KH)', reqd: true
        },
        {
            fieldtype:'Select',
            fieldname:'root_type',
            label:__('Root Type'),
            options:"Asset\nLiabilities\nEquity\nIncome\nExpenses"
        },
        {
            fieldtype:'Select',
            fieldname:'account_type',
            label:__('Account Type'),
            options:"\nReceivable\nPayable\nCash\nBank\nIncome\nExpense\nTemporary\nStock Asset"
        },
        {
            fieldtype: 'Check', fieldname: 'is_group', label: 'Is Group'
        }
    ],
}


function expand_all(node) {
    if (!node) return;

    // Expand current node if not expanded
    if (!node.expanded) {
        node.toggle_node();
    }

    // Recursively expand children
    if (node.children && node.children.length > 0) {
        node.children.forEach(child => {
            expand_all(child);
        });
    }
}
