<script setup>
import { formatMoney } from "../dashboard_utils";
import PanelShell from "./PanelShell.vue";

defineProps({
	rows: { type: Array, default: () => [] },
	currency: { type: String, default: "" },
});

function openParty(row) {
	if (row.party_type && row.party) frappe.set_route("Form", row.party_type, row.party);
}

function openReport() {
	frappe.set_route("query-report", "Account Payable");
}
</script>

<template>
	<PanelShell title="Top Payables" subtitle="Largest outstanding party balances">
		<template #action>
			<button class="dashboard-text-button" type="button" @click="openReport">
				{{ __("View All") }}
			</button>
		</template>
		<div v-if="rows.length" class="payable-list">
			<button
				v-for="row in rows"
				:key="`${row.party_type}-${row.party}`"
				class="payable-row"
				type="button"
				@click="openParty(row)"
			>
				<span>
					<strong>{{ row.party_name }}</strong>
					<small>{{ __(row.party_type) }}</small>
				</span>
				<b>{{ formatMoney(row.balance, currency) }}</b>
			</button>
		</div>
		<div v-else class="dashboard-empty-state">{{ __("No outstanding payables") }}</div>
	</PanelShell>
</template>
