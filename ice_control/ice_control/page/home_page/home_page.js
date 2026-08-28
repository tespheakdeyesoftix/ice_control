frappe.pages['home-page'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Home'),
		single_column: true,
	});

	const currentUser = frappe.session.user;
	const bootUser = frappe.boot.user || {};
	const userInfo = (frappe.boot.user_info || {})[currentUser] || {};
	const business = frappe.boot.business_info || {};
	const fullName =
		bootUser.full_name ||
		userInfo.fullname ||
		userInfo.full_name ||
		currentUser;
	const initials = fullName
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part.charAt(0).toUpperCase())
		.join('');

	const context = {
		user: {
			full_name: fullName,
			image: bootUser.user_image || userInfo.image || userInfo.user_image,
			initials: initials || 'U',
		},
		business,
		business_logo: business.photo || business.receipt_logo,
	};

	const $main = $(wrapper).find('.layout-main-section');
	$main.addClass('home-page-main').html(frappe.render_template('home_page'));
	$main
		.find('[data-home-section=welcome-banner]')
		.html(frappe.render_template('welcome_banner', context));

	$main.find('.welcome-banner__avatar-image').on('error', function () {
		$(this)
			.addClass('hidden')
			.siblings('.welcome-banner__avatar-fallback')
			.removeClass('hidden');
	});

	const dailySummary = new HomePageDailySummary($main);
	page.add_action_icon(
		'refresh-cw',
		() => {
			if (!dailySummary.loading) dailySummary.load(dailySummary.postingDate);
		},
		'home-page-toolbar-refresh',
		__('Refresh')
	);
	dailySummary.load(frappe.datetime.get_today());
};

class HomePageDailySummary {
	constructor($main) {
		this.$container = $main.find('[data-home-section=daily-summary]');
		this.postingDate = frappe.datetime.get_today();
		this.loading = false;
		this.$container.on('change', '[data-summary-date]', (event) => {
			if (event.currentTarget.value) this.load(event.currentTarget.value);
		});
		this.$container.on('click', '[data-summary-refresh]', () => {
			if (!this.loading) this.load(this.postingDate);
		});
	}

	async load(postingDate) {
		this.postingDate = postingDate || frappe.datetime.get_today();
		this.loading = true;
		this.$container.html(`<div class='daily-summary__skeleton' role='status' aria-label='${__('Loading daily sales summary')}'></div>`);
		try {
			const response = await frappe.call({
				method: 'ice_control.ice_control.page.home_page.home_page.get_home_page_data',
				type: 'GET',
				args: { posting_date: this.postingDate },
			});
			const outlets = Array.isArray(response.message?.daily_sale_summary) ? response.message.daily_sale_summary : [];
			if (!outlets.length) {
				this.renderState(__('No sales summary'), __('There is no sales data for this date or you do not have access to an outlet.'));
				return;
			}
			this.render(outlets);
		} catch (error) {
			console.error('Unable to load daily sales summary', error);
			this.renderState(__('Could not load the summary'), __('Please check your connection and use refresh to try again.'));
		} finally {
			this.loading = false;
		}
	}

	render(outlets) {
		const totals = outlets.reduce((total, outlet) => {
			['order', 'amount'].forEach((key) => total[key] += this.number(outlet[`total_${key}`]));
			['order', 'amount'].forEach((key) => total[`pending_${key}`] += this.number(outlet[`total_pending_${key}`]));
			['order', 'amount'].forEach((key) => total[`deleted_${key}`] += this.number(outlet[`total_deleted_${key}`]));
			return total;
		}, { order: 0, amount: 0, pending_order: 0, pending_amount: 0, deleted_order: 0, deleted_amount: 0 });

		const context = {
			posting_date: this.postingDate,
			display_date: frappe.datetime.str_to_user(this.postingDate),
			outlet_count: outlets.length,
			outlet_label: outlets.length === 1 ? __('outlet') : __('outlets'),
			totals: {
				orders: this.formatNumber(totals.order), amount: this.formatMoney(totals.amount),
				pending_orders: this.formatNumber(totals.pending_order), pending_amount: this.formatMoney(totals.pending_amount),
				deleted_orders: this.formatNumber(totals.deleted_order), deleted_amount: this.formatMoney(totals.deleted_amount),
				quantities: this.formatQuantityBreakdown(outlets, 'total_quantity'),
				pending_quantities: this.formatQuantityBreakdown(outlets, 'total_pending_quantity'),
				deleted_quantities: this.formatQuantityBreakdown(outlets, 'total_deleted_quantity'),
			},
			outlets: outlets.map((outlet) => this.formatOutlet(outlet)),
		};
		this.$container.html(frappe.render_template('daily_summary', context));
	}

	formatQuantityBreakdown(outlets, field) {
		return outlets.map((outlet) => ({
			outlet: outlet.outlet || __('Outlet'),
			value: this.formatNumber(outlet[field]),
			unit: outlet.default_unit || '',
		}));
	}

	formatOutlet(outlet) {
		const products = Array.isArray(outlet.sale_product_summary) ? outlet.sale_product_summary : [];
		return {
			outlet: outlet.outlet || __('Outlet'), default_unit: outlet.default_unit || '', product_count: this.formatNumber(products.length),
			total_order: this.formatNumber(outlet.total_order), total_amount: this.formatMoney(outlet.total_amount), total_quantity: this.formatNumber(outlet.total_quantity),
			total_pending_order: this.formatNumber(outlet.total_pending_order), total_pending_amount: this.formatMoney(outlet.total_pending_amount), total_pending_quantity: this.formatNumber(outlet.total_pending_quantity),
			total_deleted_order: this.formatNumber(outlet.total_deleted_order), total_deleted_amount: this.formatMoney(outlet.total_deleted_amount), total_deleted_quantity: this.formatNumber(outlet.total_deleted_quantity),
			products: products.map((product) => ({
				product_code: product.product_code || '—', product_name: product.product_name || __('Unnamed product'), unit: product.unit || '',
				quantity: this.formatNumber(product.quantity), free_quantity: this.formatNumber(product.free_quantity), return_quantity: this.formatNumber(product.return_quantity), split_quantity: this.formatNumber(product.split_quantity), total_sale_quantity: this.formatNumber(product.total_sale_quantity), total_amount: this.formatMoney(product.total_amount),
			})),
		};
	}

	renderState(title, message) {
		this.$container.html(`<section class='daily-summary'><header class='daily-summary__header'><div><p class='daily-summary__eyebrow'>${__('Sales overview')}</p><h2 class='daily-summary__title'>${__('Daily Sales Summary')}</h2></div><div class='daily-summary__actions'><input class='daily-summary__date' data-summary-date type='date' value='${this.postingDate}'><button class='daily-summary__refresh' data-summary-refresh title='${__('Refresh')}'>↻</button></div></header><div class='daily-summary__state'><div class='daily-summary__state-content'><p class='daily-summary__state-title'>${title}</p><p class='daily-summary__state-message'>${message}</p></div></div></section>`);
	}

	number(value) {
		const number = Number(value);
		return Number.isFinite(number) ? number : 0;
	}

	formatNumber(value) {
		return format_number(this.number(value), null, 0);
	}

	formatMoney(value) {
		return format_currency(this.number(value), frappe.defaults.get_default('currency'));
	}
}
