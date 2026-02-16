JAZZMIN_SETTINGS = {
    # title of the window (Will default to current_admin_site.site_title if absent or None)
    "site_title": "O'rmon Admin",

    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_header": "O'rmon Xo'jaligi",

    # Title on the brand (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_brand": "O'rmon Admin",

    # Logo to use for your site, must be present in static files, used for brand on top left
    "site_logo": "admin/img/forest-logo.png",

    # Logo to use for your site, must be present in static files, used for login form logo (defaults to site_logo)
    "login_logo": None,

    # Logo to use for login form in dark themes (defaults to login_logo)
    "login_logo_dark": None,

    # CSS classes that are applied to the logo above
    "site_logo_classes": "img-circle",

    # Relative path to a favicon for your site, will default to site_logo if absent (ideally 32x32 px)
    "site_icon": None,

    # Welcome text on the login screen
    "welcome_sign": "O'rmon Xo'jaligi Boshqaruv Paneliga Xush Kelibsiz",

    # Copyright on the footer
    "copyright": "O'rmon Xo'jaligi © 2025",

    # List of model admins to search from the search bar, search bar omitted if excluded
    # If you want to use a single search field you dont need to use a list, you can use a simple string
    "search_model": ["users.CustomUser", "reports.Report", "general.Organization"],

    # Field name on user model that contains avatar ImageField/URLField/Charfield or a callable that receives the user
    "user_avatar": "image",

    ############
    # Top Menu #
    ############

    # Links to put along the top menu
    "topmenu_links": [
        # Url that gets reversed (Permissions can be added)
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},

        # model admin to link to (Permissions checked against model)
        {"model": "users.CustomUser"},

        # App with dropdown menu to all its models pages (Permissions checked against models)
        {"app": "reports"},
        {"app": "general"},
    ],

    #############
    # User Menu #
    #############

    # Additional links to include in the user menu on the top right ('app' url type is not allowed)
    "usermenu_links": [
        {"name": "Profil", "url": "admin:password_change", "icon": "fas fa-user"},
        {"name": "Yordam", "url": "https://t.me/forest_support", "icon": "fas fa-question-circle", "new_window": True},
    ],

    #############
    # Side Menu #
    #############

    # Whether to display the side menu
    "show_sidebar": True,

    # Whether to aut expand the menu
    "navigation_expanded": True,

    # Hide these apps when generating side menu e.g (auth)
    "hide_apps": [],

    # Hide these models when generating side menu (e.g auth.user)
    "hide_models": [],

    # List of apps (and/or models) to base side menu ordering off of (does not need to contain all apps/models)
    "order_with_respect_to": ["users", "reports", "report_admin_stat", "general"],

    # Custom links to append to app groups, keyed on app name
    "custom_links": {
        "general": [
            {
                "name": "Yangi e'lon",
                "url": "admin:general_announcement_add",
                "icon": "fas fa-bullhorn",
            }
        ]
    },

    # Icons that are used when one is not manually specified
    "icons": {
        "users.CustomUser": "fas fa-user",
        "users.PersonalInfo": "fas fa-id-card",
        "users.Position": "fas fa-briefcase",

        "reports.Report": "fas fa-file-alt",
        "reports.Statement": "fas fa-file-signature",
        "reports.StatementColumn": "fas fa-columns",
        "reports.Deadline": "fas fa-calendar-alt",
        "reports.Plan": "fas fa-tasks",
        "reports.PlanItem": "fas fa-list",
        "reports.Plant": "fas fa-leaf",
        "reports.PlantPlan": "fas fa-seedling",

        "general.Organization": "fas fa-building",
        "general.Notification": "fas fa-bell",
        "general.Announcement": "fas fa-bullhorn",
        "general.Handbook": "fas fa-book",
        "general.LandDocument": "fas fa-file-pdf",
        "general.LandManagement": "fas fa-map-marked-alt",

        "report_admin_stat.ReportStatistics": "fas fa-chart-pie",
        "report_admin_stat.StatementStatistics": "fas fa-chart-bar",

        "logs.HistoryActionJournal": "fas fa-history",
        "admin.LogEntry": "fas fa-history",

    },

    # Icons that are used when one is not manually specified
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-file",

    #################
    # Related Modal #
    #################
    # Use modals instead of popups
    "related_modal_active": True,

    #############
    # UI Tweaks #
    #############
    # Relative paths to custom CSS/JS scripts (must be present in static files)
    "custom_css": "admin/css/custom.css",
    "custom_js": None,
    # Whether to link font from fonts.googleapis.com (use custom_css to supply font otherwise)
    "use_google_fonts_cdn": True,
    # Whether to show the UI customizer on the sidebar
    "show_ui_builder": False,

    ###############
    # Change view #
    ###############
    # Render out the change view as a single form, or in tabs, current options are
    # - single
    # - horizontal_tabs
    # - vertical_tabs
    # - collapsible
    # - carousel
    "changeform_format": "horizontal_tabs",
    # override change forms on a per modeladmin basis
    "changeform_format_overrides": {
    # Users app
    "users.CustomUser": "horizontal_tabs",
    "users.PersonalInfo": "collapsible",

    # Reports app
    "reports.Report": "horizontal_tabs",
    "reports.Statement": "horizontal_tabs",
    "reports.Deadline": "horizontal_tabs",
    "reports.Plan": "horizontal_tabs",
    "reports.StatementColumn": "collapsible",

    # General app
    "general.Organization": "vertical_tabs",
    "general.Announcement": "horizontal_tabs",
},
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
    }
}
