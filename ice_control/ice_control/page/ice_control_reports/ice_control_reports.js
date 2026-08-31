frappe.pages['ice_control_reports'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Reports'),
		single_column: true,
	});

	page.main.addClass('ice-control-reports-main').html(
		frappe.render_template('ice_control_reports')
	);
	page.main.css({ padding: 0 });

	const reportsPage = new IceControlReports(page.main);
	wrapper.ice_control_reports = reportsPage;
	page.add_action_icon(
		'refresh-cw',
		() => {
			if (!reportsPage.loading) reportsPage.load();
		},
		'ice-control-reports-refresh',
		__('Refresh')
	);
	reportsPage.load();
};

class IceControlReports {
	constructor($main) {
		this.$groups = $main.find('[data-report-groups]');
		this.$status = $main.find('[data-report-status]');
		this.$search = $main.find('[data-report-search]');
		this.$clearSearch = $main.find('[data-report-search-clear]');
		this.loading = false;

		this.$groups.on('click', '[data-report-url]', (event) => {
			const report = $(event.currentTarget).data('report');
			if (report) this.openReport(report);
		});
		this.$search.on('input', () => this.filterReports(this.$search.val()));
		this.$search.on('keydown', (event) => {
			if (event.key === 'Escape' && this.$search.val()) this.clearSearch();
		});
		this.$clearSearch.on('click', () => this.clearSearch());
	}

	async load() {
		this.loading = true;
		this.showStatus(__('Loading reports...'));
		this.$groups.empty();
		this.$search.prop('disabled', true);

		try {
			const response = await frappe.call({
				method: 'ice_control.ice_control.page.ice_control_reports.ice_control_reports.get_report_list',
				type: 'GET',
			});
			const reports = Array.isArray(response.message)
				? response.message.filter((report) => report.report_url)
				: [];
			this.renderReports(reports);
		} catch (error) {
			console.error('Unable to load System Reports', error);
			this.showStatus(__('Could not load reports. Please refresh and try again.'));
		} finally {
			this.loading = false;
		}
	}

	renderReports(reports) {
		if (!reports.length) {
			this.showStatus(__('No reports are available.'));
			return;
		}

		this.$status.attr('hidden', true);
		this.$search.prop('disabled', false);
		const groups = new Map();
		reports.forEach((report) => {
			const groupTitle = report.parent_system_report || __('Other Reports');
			if (!groups.has(groupTitle)) groups.set(groupTitle, []);
			groups.get(groupTitle).push(report);
		});

		const fragment = document.createDocumentFragment();
		groups.forEach((groupReports, groupTitle) => {
			fragment.appendChild(this.makeGroupCard(groupTitle, groupReports));
		});
		this.$groups[0].appendChild(fragment);
		this.filterReports(this.$search.val());
	}

	makeGroupCard(groupTitle, reports) {
		const card = document.createElement('section');
		card.className = 'ice-report-card';
		card.dataset.groupText = this.normalizeSearchText(groupTitle);

		const header = document.createElement('header');
		header.className = 'ice-report-card__header';

		const title = document.createElement('h3');
		title.className = 'ice-report-card__title';
		title.textContent = groupTitle;
		header.appendChild(title);

		const count = document.createElement('span');
		count.className = 'ice-report-card__count';
		count.textContent = reports.length;
		header.appendChild(count);
		card.appendChild(header);

		const items = document.createElement('div');
		items.className = 'ice-report-card__items';
		reports.forEach((report) => {
			const button = document.createElement('button');
			button.type = 'button';
			button.className = 'ice-report-card__item';
			button.textContent = report.report_title || report.name;
			button.title = report.report_title || report.name;
			button.dataset.reportUrl = report.report_url;
			button.dataset.searchText = this.normalizeSearchText(
				[report.report_title, report.name, groupTitle].filter(Boolean).join(' ')
			);
			$(button).data('report', report);
			items.appendChild(button);
		});
		card.appendChild(items);

		return card;
	}

	filterReports(value) {
		const query = this.normalizeSearchText(value);
		let totalMatches = 0;

		this.$clearSearch.prop('hidden', !query);
		this.$groups.find('.ice-report-card').each((_, card) => {
			const groupMatches = Boolean(query) && card.dataset.groupText.includes(query);
			let groupMatchesCount = 0;

			$(card).find('.ice-report-card__item').each((__, item) => {
				const matches = !query || groupMatches || item.dataset.searchText.includes(query);
				item.hidden = !matches;
				if (matches) groupMatchesCount += 1;
			});

			card.hidden = groupMatchesCount === 0;
			card.querySelector('.ice-report-card__count').textContent = groupMatchesCount;
			totalMatches += groupMatchesCount;
		});

		if (query && totalMatches === 0) {
			this.showStatus(__('No reports match your search.'));
		} else {
			this.$status.attr('hidden', true);
		}
	}

	clearSearch() {
		this.$search.val('');
		this.filterReports('');
		this.$search.trigger('focus');
	}

	normalizeSearchText(value) {
		return String(value || '').normalize('NFKC').toLocaleLowerCase().trim();
	}

	openReport(report) {
		const reportTitle = report.report_title || report.name || __('Report viewer');
		const viewerUrl = new URL(
			'/assets/ice_control/report_server_viewer.html',
			window.location.origin
		);
		viewerUrl.searchParams.set('v', '3');
		viewerUrl.searchParams.set('report_path', report.report_url);

		const dialog = new frappe.ui.Dialog({
			title: reportTitle,
			size: 'extra-large',
			fields: [{
				fieldtype: 'HTML',
				fieldname: 'report_viewer',
			}],
		});
		const iframe = document.createElement('iframe');
		iframe.className = 'ice-report-dialog__frame';
		iframe.title = reportTitle;
		iframe.allow = 'clipboard-write';
		iframe.src = viewerUrl.toString();

		dialog.fields_dict.report_viewer.$wrapper.empty().append(iframe);
		dialog.$wrapper.addClass('ice-report-dialog');
		dialog.$wrapper.one('hidden.bs.modal', () => {
			iframe.src = 'about:blank';
			dialog.$wrapper.remove();
		});
		dialog.show();
	}

	showStatus(message) {
		this.$status.text(message).removeAttr('hidden');
	}
}
