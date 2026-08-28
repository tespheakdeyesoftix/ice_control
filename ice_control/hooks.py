app_name = "ice_control"
app_title = "Ice Factory Management System"
app_publisher = "Tes Pheakdey"
app_description = "Ice produce management"
app_email = "pheakdey.micronet@gmail.com"
app_license = "mit"
app_logo_url = "/assets/ice_control/logo.png"
develop_version = "1.0.0-develop"
app_home = "/desk/selling"


# Send non-GET requests for this app's endpoints as native `application/json`
# bodies instead of form-encoded, per-key JSON-stringified values.
use_json_request_body = True

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
    {
        "name": "ice_control",
        "logo": "/assets/ice_control/logo.png",
        "title": "Ice Factory Management System",
        "route": "/desk/selling",
        "sequence_id": 10,
    }
]

# Companion apps that extend a host app (instead of taking their own apps-screen icon) can pin
# their workspaces into the host app's workspace dock (rail) with this hook. Declaring it keeps
# the app off the apps screen, so it takes precedence over any add_to_apps_screen above. Who can
# see a pinned workspace is controlled by that workspace's own Roles table.
# add_to_workspace_dock = [
# 	{
# 		"app": "ice_control",
# 		"workspace": "Selling",
# 	},
# 	{
# 		"app": "ice_control",
# 		"workspace": "Stock Management",
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ice_control/css/ice_control.css"
# app_include_js = "/assets/ice_control/js/ice_control.js"

app_include_css = [
		"/assets/ice_control/css/ice_control.css",
]
app_include_js = [
	"/assets/ice_control/js/ice_control.js",
	"/assets/ice_control/js/return_product.js",
    
]
# "/assets/ice_control/js/workspace_outlet_filter.js"

# include js, css files in header of web template
# web_include_css = "/assets/ice_control/css/ice_control.css"
# web_include_js = "/assets/ice_control/js/ice_control.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ice_control/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ice_control/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ice_control.utils.jinja_methods",
# 	"filters": "ice_control.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ice_control.install.before_install"
# after_install = "ice_control.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ice_control.uninstall.before_uninstall"
# after_uninstall = "ice_control.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ice_control.utils.before_app_install"
# after_app_install = "ice_control.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ice_control.utils.before_app_uninstall"
# after_app_uninstall = "ice_control.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "ice_control.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ice_control.notifications.get_notification_config"

boot_session = "ice_control.boot.boot_session"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Employee":  "ice_control.hr.doctype.employee.employee.get_permission_query_conditions",
	"Role": "ice_control.api.permission.role_has_permission",
	"Module Def": "ice_control.api.permission.module_def_has_permission"
}

#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ice_control.tasks.all"
# 	],
# 	"daily": [
# 		"ice_control.tasks.daily"
# 	],
# 	"hourly": [
# 		"ice_control.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ice_control.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ice_control.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ice_control.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "ice_control.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------

# from ice_control import overrides

# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ice_control.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ice_control.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ice_control.utils.before_request"]
# after_request = ["ice_control.utils.after_request"]

# Job Events
# ----------
# before_job = ["ice_control.utils.before_job"]
# after_job = ["ice_control.utils.after_job"]

# after_file_upload = ["ice_control.utils.after_file_upload"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ice_control.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Require all whitelisted methods to have type annotations
require_type_annotated_api_methods = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


fixtures = [
    {"dt": "HTML Template"},
    {
        "dt": "Custom Field",
        "filters": [
            ["dt", "in", ["Note"]]
        ]
    },
]