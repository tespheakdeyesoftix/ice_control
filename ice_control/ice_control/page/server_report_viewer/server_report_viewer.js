function getReportViewerContext() {
	const query = new URLSearchParams(window.location.search);
	const routeOptions = frappe.route_options || {};
	
 

	return {
		reportPath: routeOptions.report_url || query.get("report_url") || "",
		outlet: routeOptions.outlet || query.get("outlet") || ""

	};
}

function updateReportViewer(wrapper) {
	const state = wrapper.report_viewer_state;
	if (!state) {
		return;
	}

	const context = getReportViewerContext();
	const viewerUrl = new URL(
		"/assets/ice_control/report_server_viewer.html",
		window.location.origin
	);

	if (context.reportPath) {
		viewerUrl.searchParams.set("report_path", context.reportPath);
	}
	if (context.outlet) {
		viewerUrl.searchParams.set("outlet", context.outlet);
	}
	
	
	viewerUrl.searchParams.set("user", frappe.session.user_fullname || "");
	


	const nextSource = viewerUrl.toString();
	if (state.source !== nextSource) {
		state.source = nextSource;
		state.viewer.src = nextSource;
	}
}

frappe.pages["server-report-viewer"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Server Report Viewer"),
		single_column: true,
	});

	const viewer = document.createElement("iframe");
	viewer.className = "server-report-viewer-frame";
	viewer.title = __("Server Report Viewer");
	viewer.setAttribute("allow", "clipboard-write");

	Object.assign(viewer.style, {
		width: "100%",
		height: "calc(100vh - 50px)",
		minHeight: "500px",
		border: "0",
		display: "block",
		background: "#fff",
	});

	page.main.empty().append(viewer);
	page.main.css({ padding: 0, overflow: "hidden" });

	wrapper.report_viewer_state = { viewer: viewer, source: "" };
	updateReportViewer(wrapper);

	window.addEventListener("popstate", function () {
		updateReportViewer(wrapper);
	});

	frappe.router.on("change", function () {
		if (frappe.get_route()[0] === "server-report-viewer") {
			updateReportViewer(wrapper);
		}
	});
};

frappe.pages["server-report-viewer"].on_page_show = function (wrapper) {
	updateReportViewer(wrapper);
};
