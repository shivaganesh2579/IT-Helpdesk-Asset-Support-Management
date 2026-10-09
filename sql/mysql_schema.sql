-- MySQL 8 schema reference / migration aid (not the connector used by the current Flask prototype).
-- Database: CREATE DATABASE helix_helpdesk CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE helix_helpdesk;

CREATE TABLE IF NOT EXISTS departments (
  department_id INT AUTO_INCREMENT PRIMARY KEY,
  department_name VARCHAR(120) NOT NULL UNIQUE,
  location VARCHAR(160) NOT NULL DEFAULT 'Main Campus'
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  employee_code VARCHAR(30) NOT NULL UNIQUE,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  phone VARCHAR(40),
  department_id INT NOT NULL,
  role ENUM('Admin','Requester','Technician') NOT NULL DEFAULT 'Requester',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_users_department FOREIGN KEY (department_id) REFERENCES departments(department_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_users_active CHECK (is_active IN (0,1))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS asset_categories (
  asset_category_id INT AUTO_INCREMENT PRIMARY KEY,
  category_name VARCHAR(80) NOT NULL UNIQUE,
  description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ticket_categories (
  ticket_category_id INT AUTO_INCREMENT PRIMARY KEY,
  category_name VARCHAR(100) NOT NULL UNIQUE,
  description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS priorities (
  priority_id INT AUTO_INCREMENT PRIMARY KEY,
  priority_name ENUM('Critical','High','Medium','Low') NOT NULL UNIQUE,
  sla_hours INT NOT NULL,
  sort_order INT NOT NULL UNIQUE,
  CONSTRAINT chk_priority_sla CHECK (sla_hours > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS assets (
  asset_id INT AUTO_INCREMENT PRIMARY KEY,
  asset_tag VARCHAR(40) NOT NULL UNIQUE,
  asset_name VARCHAR(160) NOT NULL,
  asset_category_id INT NOT NULL,
  department_id INT NOT NULL,
  assigned_user_id INT NULL,
  manufacturer VARCHAR(100) NOT NULL,
  model_number VARCHAR(120) NOT NULL,
  serial_number VARCHAR(120) UNIQUE,
  purchase_date DATE NOT NULL,
  asset_status ENUM('In Use','In Repair','In Stock','Retired','Lost') NOT NULL DEFAULT 'In Use',
  location VARCHAR(180) NOT NULL DEFAULT 'Main Campus',
  notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_assets_category FOREIGN KEY (asset_category_id) REFERENCES asset_categories(asset_category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_assets_department FOREIGN KEY (department_id) REFERENCES departments(department_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_assets_user FOREIGN KEY (assigned_user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS warranties (
  warranty_id INT AUTO_INCREMENT PRIMARY KEY,
  asset_id INT NOT NULL,
  provider VARCHAR(160) NOT NULL,
  warranty_start DATE NOT NULL,
  warranty_end DATE NOT NULL,
  coverage_details TEXT NOT NULL,
  reference_number VARCHAR(120) UNIQUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_warranty_asset FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT chk_warranty_dates CHECK (warranty_end >= warranty_start),
  INDEX idx_warranties_expiry (warranty_end)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tickets (
  ticket_id INT AUTO_INCREMENT PRIMARY KEY,
  ticket_number VARCHAR(30) NOT NULL UNIQUE,
  ticket_type ENUM('Incident','Service Request') NOT NULL,
  requester_id INT NOT NULL,
  asset_id INT NULL,
  ticket_category_id INT NOT NULL,
  priority_id INT NOT NULL,
  title VARCHAR(220) NOT NULL,
  description TEXT NOT NULL,
  status ENUM('Open','Assigned','In Progress','On Hold','Resolved','Closed') NOT NULL DEFAULT 'Open',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  due_at DATETIME NULL,
  resolved_at DATETIME NULL,
  CONSTRAINT chk_ticket_title CHECK (CHAR_LENGTH(TRIM(title)) > 2),
  CONSTRAINT chk_ticket_description CHECK (CHAR_LENGTH(TRIM(description)) > 4),
  CONSTRAINT fk_ticket_requester FOREIGN KEY (requester_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_ticket_asset FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_ticket_category FOREIGN KEY (ticket_category_id) REFERENCES ticket_categories(ticket_category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_ticket_priority FOREIGN KEY (priority_id) REFERENCES priorities(priority_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  INDEX idx_tickets_status_created (status, created_at),
  INDEX idx_tickets_requester (requester_id),
  INDEX idx_tickets_asset (asset_id),
  INDEX idx_tickets_priority (priority_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS incidents (
  ticket_id INT PRIMARY KEY,
  impact ENUM('Low','Moderate','High','Critical') NOT NULL,
  urgency ENUM('Low','Moderate','High','Critical') NOT NULL,
  occurred_at DATETIME NULL,
  affected_service VARCHAR(160),
  CONSTRAINT fk_incidents_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS service_requests (
  ticket_id INT PRIMARY KEY,
  request_type VARCHAR(160) NOT NULL,
  approval_status ENUM('Not Required','Pending','Approved','Rejected') NOT NULL DEFAULT 'Not Required',
  requested_for VARCHAR(160),
  CONSTRAINT fk_requests_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS support_staff (
  staff_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  staff_code VARCHAR(40) NOT NULL UNIQUE,
  specialization VARCHAR(160) NOT NULL,
  shift_name VARCHAR(50) NOT NULL DEFAULT 'General',
  is_available TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT fk_staff_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_staff_available CHECK (is_available IN (0,1))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ticket_assignments (
  assignment_id INT AUTO_INCREMENT PRIMARY KEY,
  ticket_id INT NOT NULL,
  staff_id INT NOT NULL,
  assigned_by INT NOT NULL,
  assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  unassigned_at DATETIME NULL,
  assignment_note VARCHAR(500),
  CONSTRAINT fk_assignment_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_assignment_staff FOREIGN KEY (staff_id) REFERENCES support_staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_assignment_user FOREIGN KEY (assigned_by) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_assignment_dates CHECK (unassigned_at IS NULL OR unassigned_at >= assigned_at),
  INDEX idx_assignments_staff_active (staff_id, unassigned_at),
  INDEX idx_assignments_ticket_active (ticket_id, unassigned_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ticket_status_history (
  history_id INT AUTO_INCREMENT PRIMARY KEY,
  ticket_id INT NOT NULL,
  old_status ENUM('Open','Assigned','In Progress','On Hold','Resolved','Closed') NULL,
  new_status ENUM('Open','Assigned','In Progress','On Hold','Resolved','Closed') NOT NULL,
  changed_by INT NOT NULL,
  changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  note VARCHAR(500),
  CONSTRAINT fk_history_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_history_user FOREIGN KEY (changed_by) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  INDEX idx_history_ticket_date (ticket_id, changed_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS resolutions (
  resolution_id INT AUTO_INCREMENT PRIMARY KEY,
  ticket_id INT NOT NULL UNIQUE,
  resolved_by INT NOT NULL,
  resolution_text TEXT NOT NULL,
  root_cause VARCHAR(500),
  resolved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  preventive_action VARCHAR(500),
  CONSTRAINT chk_resolution_text CHECK (CHAR_LENGTH(TRIM(resolution_text)) >= 8),
  CONSTRAINT fk_resolution_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_resolution_staff FOREIGN KEY (resolved_by) REFERENCES support_staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS maintenance_records (
  maintenance_id INT AUTO_INCREMENT PRIMARY KEY,
  asset_id INT NOT NULL,
  performed_by INT NULL,
  maintenance_type ENUM('Preventive','Corrective','Inspection','Upgrade') NOT NULL,
  scheduled_date DATE NOT NULL,
  completed_date DATE NULL,
  cost DECIMAL(12,2) NOT NULL DEFAULT 0,
  status ENUM('Scheduled','In Progress','Completed','Cancelled') NOT NULL DEFAULT 'Scheduled',
  notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_maintenance_cost CHECK (cost >= 0),
  CONSTRAINT fk_maintenance_asset FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_maintenance_staff FOREIGN KEY (performed_by) REFERENCES support_staff(staff_id) ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX idx_maintenance_asset_date (asset_id, scheduled_date)
) ENGINE=InnoDB;

-- asset_tag already has a UNIQUE index.
