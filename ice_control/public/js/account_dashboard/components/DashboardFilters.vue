<script setup>
import { reactive, ref, watch } from "vue";

const props = defineProps({
	modelValue: { type: Object, required: true },
	outlets: { type: Array, default: () => [] },
	loading: Boolean,
});
const emit = defineEmits(["apply"]);

const draft = reactive({ outlet: "", start_date: "", end_date: "" });
const validationMessage = ref("");

watch(
	() => props.modelValue,
	(value) => Object.assign(draft, value || {}),
	{ immediate: true, deep: true }
);

function apply() {
	validationMessage.value = "";
	if (!draft.start_date || !draft.end_date) {
		validationMessage.value = __("Start Date and End Date are required.");
		return;
	}
	if (draft.start_date > draft.end_date) {
		validationMessage.value = __("Start Date cannot be after End Date.");
		return;
	}
	emit("apply", { ...draft });
}
</script>

<template>
	<form class="dashboard-filters" @submit.prevent="apply">
		<label class="dashboard-filter">
			<span>{{ __("Outlet") }}</span>
			<select v-model="draft.outlet" :disabled="loading">
				<option value="">{{ __("All Outlets") }}</option>
				<option v-for="outlet in outlets" :key="outlet.value" :value="outlet.value">
					{{ outlet.label }}
				</option>
			</select>
		</label>

		<label class="dashboard-filter">
			<span>{{ __("Start Date") }}</span>
			<input v-model="draft.start_date" type="date" :disabled="loading" required />
		</label>

		<label class="dashboard-filter">
			<span>{{ __("End Date") }}</span>
			<input v-model="draft.end_date" type="date" :disabled="loading" required />
		</label>

		<button class="dashboard-filter__submit" type="submit" :disabled="loading">
			<span
				class="dashboard-filter__button-icon"
				v-html="frappe.utils.icon(loading ? 'loader' : 'refresh-cw', 'sm')"
			></span>
			{{ loading ? __("Loading") : __("Refresh") }}
		</button>

		<p v-if="validationMessage" class="dashboard-filter__error" role="alert">
			{{ validationMessage }}
		</p>
	</form>
</template>
