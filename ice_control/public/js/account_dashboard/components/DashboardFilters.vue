<script setup>
import { computed, reactive, watch } from "vue";

import FrappeControl from "./FrappeControl.vue";

const props = defineProps({
	modelValue: { type: Object, required: true },
	outlets: { type: Array, default: () => [] },
	loading: Boolean,
});
const emit = defineEmits(["apply"]);

const draft = reactive({ outlet: "", start_date: "", end_date: "" });
const outletOptions = computed(() => [
	{ label: __("All Outlets"), value: "" },
	...props.outlets.map((outlet) => ({
		label: outlet.label,
		value: outlet.value,
	})),
]);

watch(
	() => props.modelValue,
	(value) => Object.assign(draft, value || {}),
	{ immediate: true, deep: true }
);

function showWarning(message) {
	frappe.show_alert({ message, indicator: "orange" });
}

function apply() {
	if (!draft.start_date || !draft.end_date) {
		showWarning(__("Start Date and End Date are required."));
		return;
	}
	if (draft.start_date > draft.end_date) {
		showWarning(__("Start Date cannot be after End Date."));
		return;
	}
	if (!props.loading) emit("apply", { ...draft });
}
</script>

<template>
	<form class="dashboard-filters" @submit.prevent="apply">
		<FrappeControl
			v-model="draft.outlet"
			fieldname="dashboard_outlet"
			fieldtype="Select"
			:label="__('Outlet')"
			:options="outletOptions"
			:disabled="loading"
		/>

		<FrappeControl
			v-model="draft.start_date"
			fieldname="dashboard_start_date"
			fieldtype="Date"
			:label="__('Start Date')"
			:disabled="loading"
			required
		/>

		<FrappeControl
			v-model="draft.end_date"
			fieldname="dashboard_end_date"
			fieldtype="Date"
			:label="__('End Date')"
			:disabled="loading"
			required
		/>

		<button
			class="dashboard-filter__submit btn btn-primary"
			type="submit"
			:disabled="loading"
		>
			<span
				class="dashboard-filter__button-icon"
				v-html="frappe.utils.icon(loading ? 'loader' : 'refresh-cw', 'sm')"
			></span>
			{{ loading ? __("Loading") : __("Refresh") }}
		</button>
	</form>
</template>
