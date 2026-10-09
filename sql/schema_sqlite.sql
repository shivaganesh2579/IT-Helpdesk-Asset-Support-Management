PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departments (
    department_id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_name TEXT NOT NULL UNIQUE,
    location TEXT NOT NULL DEFAULT 'Main Campus'
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_code TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    department_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'Requester' CHECK (role IN ('Admin','Requester','Technician')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(department_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS asset_categories (
    asset_category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS ticket_categories (
    ticket_category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS priorities (
    priority_id INTEGER PRIMARY KEY AUTOINCREMENT,
    priority_name TEXT NOT NULL UNIQUE CHECK (priority_name IN ('Critical','High','Medium','Low')),
    sla_hours INTEGER NOT NULL CHECK (sla_hours > 0),
    sort_order INTEGER NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_tag TEXT NOT NULL UNIQUE,
    asset_name TEXT NOT NULL,
    asset_category_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    assigned_user_id INTEGER,
    manufacturer TEXT NOT NULL,
    model_number TEXT NOT NULL,
    serial_number TEXT UNIQUE,
    purchase_date TEXT NOT NULL CHECK (date(purchase_date) IS NOT NULL),
    asset_status TEXT NOT NULL DEFAULT 'In Use' CHECK (asset_status IN ('In Use','In Repair','In Stock','Retired','Lost')),
    location TEXT NOT NULL DEFAULT 'Main Campus',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_category_id) REFERENCES asset_categories(asset_category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (department_id) REFERENCES departments(department_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (assigned_user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS warranties (
    warranty_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    warranty_start TEXT NOT NULL CHECK (date(warranty_start) IS NOT NULL),
    warranty_end TEXT NOT NULL CHECK (date(warranty_end) IS NOT NULL AND date(warranty_end) >= date(warranty_start)),
    coverage_details TEXT NOT NULL,
    reference_number TEXT UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_number TEXT NOT NULL UNIQUE,
    ticket_type TEXT NOT NULL CHECK (ticket_type IN ('Incident','Service Request')),
    requester_id INTEGER NOT NULL,
    asset_id INTEGER,
    ticket_category_id INTEGER NOT NULL,
    priority_id INTEGER NOT NULL,
    title TEXT NOT NULL CHECK (length(trim(title)) > 2),
    description TEXT NOT NULL CHECK (length(trim(description)) > 4),
    status TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Assigned','In Progress','On Hold','Resolved','Closed')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_at TEXT,
    resolved_at TEXT,
    FOREIGN KEY (requester_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON UPDATE CASCADE ON DELETE SET NULL,
    FOREIGN KEY (ticket_category_id) REFERENCES ticket_categories(ticket_category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (priority_id) REFERENCES priorities(priority_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (due_at IS NULL OR date(due_at) IS NOT NULL),
    CHECK (resolved_at IS NULL OR date(resolved_at) IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS incidents (
    ticket_id INTEGER PRIMARY KEY,
    impact TEXT NOT NULL CHECK (impact IN ('Low','Moderate','High','Critical')),
    urgency TEXT NOT NULL CHECK (urgency IN ('Low','Moderate','High','Critical')),
    occurred_at TEXT,
    affected_service TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS service_requests (
    ticket_id INTEGER PRIMARY KEY,
    request_type TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'Not Required' CHECK (approval_status IN ('Not Required','Pending','Approved','Rejected')),
    requested_for TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS support_staff (
    staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    staff_code TEXT NOT NULL UNIQUE,
    specialization TEXT NOT NULL,
    shift_name TEXT NOT NULL DEFAULT 'General',
    is_available INTEGER NOT NULL DEFAULT 1 CHECK (is_available IN (0,1)),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS ticket_assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    staff_id INTEGER NOT NULL,
    assigned_by INTEGER NOT NULL,
    assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    unassigned_at TEXT,
    assignment_note TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (staff_id) REFERENCES support_staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (assigned_by) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (unassigned_at IS NULL OR datetime(unassigned_at) >= datetime(assigned_at))
);

CREATE TABLE IF NOT EXISTS ticket_status_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL CHECK (new_status IN ('Open','Assigned','In Progress','On Hold','Resolved','Closed')),
    changed_by INTEGER NOT NULL,
    changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS resolutions (
    resolution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL UNIQUE,
    resolved_by INTEGER NOT NULL,
    resolution_text TEXT NOT NULL CHECK (length(trim(resolution_text)) >= 8),
    root_cause TEXT,
    resolved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    preventive_action TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (resolved_by) REFERENCES support_staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS maintenance_records (
    maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    performed_by INTEGER,
    maintenance_type TEXT NOT NULL CHECK (maintenance_type IN ('Preventive','Corrective','Inspection','Upgrade')),
    scheduled_date TEXT NOT NULL CHECK (date(scheduled_date) IS NOT NULL),
    completed_date TEXT,
    cost REAL NOT NULL DEFAULT 0 CHECK (cost >= 0),
    status TEXT NOT NULL DEFAULT 'Scheduled' CHECK (status IN ('Scheduled','In Progress','Completed','Cancelled')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (performed_by) REFERENCES support_staff(staff_id) ON UPDATE CASCADE ON DELETE SET NULL,
    CHECK (completed_date IS NULL OR date(completed_date) IS NOT NULL),
    CHECK (completed_date IS NULL OR date(completed_date) IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_tickets_status_created ON tickets(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_requester ON tickets(requester_id);
CREATE INDEX IF NOT EXISTS idx_tickets_asset ON tickets(asset_id);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority_id);
CREATE INDEX IF NOT EXISTS idx_assignments_staff_active ON ticket_assignments(staff_id, unassigned_at);
CREATE INDEX IF NOT EXISTS idx_assignments_ticket_active ON ticket_assignments(ticket_id, unassigned_at);
CREATE INDEX IF NOT EXISTS idx_history_ticket_date ON ticket_status_history(ticket_id, changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_warranties_expiry ON warranties(warranty_end);
CREATE INDEX IF NOT EXISTS idx_assets_tag ON assets(asset_tag);
CREATE INDEX IF NOT EXISTS idx_maintenance_asset_date ON maintenance_records(asset_id, scheduled_date DESC);
