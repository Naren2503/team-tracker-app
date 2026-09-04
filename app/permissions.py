VIEW_ALL_RECORDS = "view_all_records"
VIEW_OWN_RECORDS = "view_own_records"
CREATE_RECORDS = "create_records"
EDIT_OWN_RECORDS = "edit_own_records"
EDIT_ALL_RECORDS = "edit_all_records"
DELETE_RECORDS = "delete_records"
IMPORT_EXCEL = "import_excel_data"
EXPORT_DATA = "export_data"
MANAGE_USERS = "manage_users"
MANAGE_DASHBOARD = "manage_dashboard_settings"
VIEW_AUDIT = "view_audit_log"

ALL_PERMISSIONS = [
    VIEW_ALL_RECORDS,
    VIEW_OWN_RECORDS,
    CREATE_RECORDS,
    EDIT_OWN_RECORDS,
    EDIT_ALL_RECORDS,
    DELETE_RECORDS,
    IMPORT_EXCEL,
    EXPORT_DATA,
    MANAGE_USERS,
    MANAGE_DASHBOARD,
    VIEW_AUDIT,
]

ROLE_DEFAULTS = {
    "Admin": ALL_PERMISSIONS,
    "Editor": [VIEW_OWN_RECORDS, CREATE_RECORDS, EDIT_OWN_RECORDS, IMPORT_EXCEL, EXPORT_DATA],
    "Viewer": [VIEW_OWN_RECORDS, EXPORT_DATA],
}
