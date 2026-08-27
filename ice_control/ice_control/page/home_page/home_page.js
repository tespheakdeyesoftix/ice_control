frappe.pages['home-page'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
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
};
