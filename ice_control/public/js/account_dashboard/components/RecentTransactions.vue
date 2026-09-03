<script setup>
import { formatMoney } from "../dashboard_utils";
import PanelShell from "./PanelShell.vue";

defineProps({
	rows: { type: Array, default: () => [] },
	currency: { type: String, default: "" },
});

function openVoucher(row) {
	if (row.voucher_type && row.voucher_no) {
		frappe.set_route("Form", row.voucher_type, row.voucher_no);
	}
}

function getTimeAgo(timestamp) {
	return timestamp ? frappe.datetime.comment_when(timestamp) : "";
}
</script>

<template>
	<PanelShell title="Recent Transactions" subtitle="Latest posted vouchers in the selected period">
		<div v-if="rows.length" class="transaction-table-wrap">
			<table class="transaction-table">
				<thead>
					<tr>
						<th>{{ __("Date") }}</th>
						<th>{{ __("Voucher") }}</th>
						<th>{{ __("Party") }}</th>
						<th>{{ __("Type") }}</th>
						<th class="is-numeric">{{ __("Amount") }}</th>
						<th>{{ __("Status") }}</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in rows" :key="`${row.voucher_type}-${row.voucher_no}`">
						<td>{{ frappe.datetime.str_to_user(row.posting_date) }}</td>
						<td>
							<button class="transaction-link" type="button" @click="openVoucher(row)">
								{{ row.voucher_no }}
							</button>
						</td>
						<td>{{ row.party_name }}</td>
						<td>{{ __(row.voucher_type) }}</td>
						<td class="is-numeric">{{ formatMoney(row.amount, currency) }}</td>
						<td>
							<div class="transaction-status-cell">
								<span class="transaction-status">{{ row.status }}</span>
								<span
									v-if="row.created_at"
									class="transaction-time-ago"
									v-html="getTimeAgo(row.created_at)"
								></span>
							</div>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
		<div v-else class="dashboard-empty-state">{{ __("No posted transactions in this period") }}</div>
	</PanelShell>
</template>
