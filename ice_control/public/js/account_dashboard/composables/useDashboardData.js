import { ref } from "vue";

const DASHBOARD_METHOD =
	"ice_control.accounting.page.account_dashboard.account_dashboard.get_dashboard_data";

export function useDashboardData() {
	const data = ref(null);
	const loading = ref(false);
	const error = ref("");
	let requestId = 0;

	async function load(filters) {
		const activeRequest = ++requestId;
		loading.value = true;
		error.value = "";

		try {
			const response = await frappe.call({
				method: DASHBOARD_METHOD,
				type: "GET",
				args: {
					outlet: filters.outlet || "",
					start_date: filters.start_date,
					end_date: filters.end_date,
				},
			});
			if (activeRequest === requestId) data.value = response.message || null;
			return data.value;
		} catch (exception) {
			if (activeRequest === requestId) {
				error.value =
					exception?.message || __("Unable to load the account dashboard.");
			}
			throw exception;
		} finally {
			if (activeRequest === requestId) loading.value = false;
		}
	}

	return { data, loading, error, load };
}
