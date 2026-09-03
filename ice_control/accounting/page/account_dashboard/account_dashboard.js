frappe.pages["account-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Account Dashboard"),
		single_column: true,
	});

	wrapper.accountDashboardPage = page;
	wrapper.accountDashboardMount = $("<div class='account-dashboard-mount'></div>").appendTo(
		page.main
	);
	setup_account_dashboard_toolbar(wrapper);
};

frappe.pages["account-dashboard"].on_page_show = function (wrapper) {
	load_account_dashboard(wrapper);
};

function load_account_dashboard(wrapper) {
	if (wrapper.accountDashboard) {
		return wrapper.accountDashboard.refresh();
	}
	if (wrapper.accountDashboardPromise) return wrapper.accountDashboardPromise;

	wrapper.accountDashboardPromise = frappe
		.require(["account_dashboard.bundle.js", "account_dashboard_styles.bundle.css"])
		.then(() => {
			wrapper.accountDashboard = new frappe.ui.AccountDashboard({
				wrapper: wrapper.accountDashboardMount,
				page: wrapper.accountDashboardPage,
			});
			return wrapper.accountDashboard;
		})
		.catch((error) => {
			wrapper.accountDashboardPromise = null;
			console.error("Unable to initialize Account Dashboard", error);
			frappe.msgprint({
				title: __("Account Dashboard"),
				message: __("Unable to load the dashboard assets. Please rebuild the app and try again."),
				indicator: "red",
			});
		});

	return wrapper.accountDashboardPromise;
}

function setup_account_dashboard_toolbar(wrapper) {
	const page = wrapper.accountDashboardPage;
	const quick_actions = [
		{ label: "Receive Payment", doctype: "Sale Payment" },
		{ label: "Pay Vendor", doctype: "Purchase Order Payment" },
		{ label: "Record Expense", doctype: "Expense" },
		{ label: "Journal Entry", doctype: "Journal Entry" },
	];

	quick_actions.forEach((action) => {
		page.add_inner_button(
			__(action.label),
			() => frappe.new_doc(action.doctype),
			__("Quick actions"),
			"default",
			true
		);
	});
	page.set_inner_btn_group_as_primary(__("Quick actions"));

	page.add_action_icon(
		"refresh-cw",
		() => load_account_dashboard(wrapper),
		"account-dashboard-refresh",
		__("Refresh")
	);
}
