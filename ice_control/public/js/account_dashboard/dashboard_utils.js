export function toNumber(value) {
	const number = Number(value);
	return Number.isFinite(number) ? number : 0;
}

export function formatMoney(value, currency) {
	return format_currency(toNumber(value), currency || undefined);
}

export function formatCompactNumber(value, currency) {
	const number = toNumber(value);
	const absolute = Math.abs(number);
	let display = number;
	let suffix = "";
	if (absolute >= 1_000_000) {
		display = number / 1_000_000;
		suffix = "M";
	} else if (absolute >= 1_000) {
		display = number / 1_000;
		suffix = "K";
	}
	return `${format_currency(display, currency || undefined, 1)}${suffix}`;
}

export function formatChartLabel(value, granularity) {
	if (!value) return "";
	if (granularity === "month") {
		const [year, month] = value.split("-");
		return new Intl.DateTimeFormat(undefined, { month: "short", year: "2-digit" }).format(
			new Date(Number(year), Number(month) - 1, 1)
		);
	}
	return frappe.datetime.str_to_user(value);
}

export function navigate(route, routeOptions = null) {
	if (!Array.isArray(route) || !route.length) return;
	frappe.route_options = routeOptions || null;
	frappe.set_route(...route);
}
