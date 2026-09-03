import { createApp } from "vue";

import AccountDashboardComponent from "./AccountDashboard.vue";

class AccountDashboard {
	constructor({ wrapper, page }) {
		this.wrapper = wrapper;
		this.page = page;
		this.app = createApp(AccountDashboardComponent, {
			initialOutlet: frappe.boot.employee_outlet || "",
		});

		if (window.SetVueGlobals) SetVueGlobals(this.app);
		this.component = this.app.mount(this.wrapper.get(0));
	}

	refresh() {
		return this.component?.refresh?.();
	}

	destroy() {
		this.app?.unmount();
		this.component = null;
	}
}

frappe.provide("frappe.ui");
frappe.ui.AccountDashboard = AccountDashboard;

export default AccountDashboard;
