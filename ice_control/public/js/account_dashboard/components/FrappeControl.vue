<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
	modelValue: { type: String, default: "" },
	fieldname: { type: String, required: true },
	fieldtype: { type: String, required: true },
	label: { type: String, required: true },
	options: { type: [Array, String], default: () => [] },
	disabled: Boolean,
	required: Boolean,
});

const emit = defineEmits(["update:modelValue"]);
const controlRoot = ref(null);
let control = null;

function emitValue() {
	const value = control?.get_value?.() || "";
	if (value !== props.modelValue) emit("update:modelValue", value);
}

function syncValue(value) {
	if (!control) return;
	const normalizedValue = value || "";
	if ((control.get_value?.() || "") !== normalizedValue) {
		control.set_input(normalizedValue);
	}
}

function syncOptions(options) {
	if (!control || props.fieldtype !== "Select") return;
	control.df.options = options || [];
	control.last_options = null;
	control.set_options?.(props.modelValue || "");
	control.set_input(props.modelValue || "");
}

function syncDisabled(disabled) {
	if (!control) return;
	control.$input?.prop("disabled", Boolean(disabled));
	control.$wrapper?.toggleClass("is-disabled", Boolean(disabled));
}

onMounted(async () => {
	await nextTick();
	control = frappe.ui.form.make_control({
		parent: window.jQuery(controlRoot.value),
		df: {
			fieldname: props.fieldname,
			fieldtype: props.fieldtype,
			label: props.label,
			options: props.options,
			reqd: props.required ? 1 : 0,
			is_filter: 1,
			onchange: emitValue,
		},
		render_input: true,
	});
	control.set_input(props.modelValue || "");
	syncDisabled(props.disabled);
});

watch(() => props.modelValue, syncValue);
watch(() => props.options, syncOptions, { deep: true });
watch(() => props.disabled, syncDisabled);

onBeforeUnmount(() => {
	control?.datepicker?.destroy?.();
	control?.$wrapper?.remove();
	control = null;
});
</script>

<template>
	<div ref="controlRoot" class="dashboard-frappe-control"></div>
</template>
