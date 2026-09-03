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
		.require("account_dashboard.bundle.js")
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
