# Database design notes

## Entities and purpose

| Entity / relation | Purpose | Key relationship |
|---|---|---|
| `departments` | Department reference data | One department has many users and assets |
| `users` | Requesters and staff identities | Many users belong to one department |
| `asset_categories` | Controlled asset type list | One category has many assets |
| `ticket_categories` | Controlled support-area list | One category has many tickets |
| `priorities` | Priority label, order and SLA hours | One priority can be used by many tickets |
| `assets` | Asset master and assignment/location | An asset can have many warranties, tickets and maintenance records |
| `warranties` | Warranty provider, dates and coverage | Many warranty records can belong to one asset |
| `tickets` | Common ticket fields for all ticket types | One requester; optional asset; one priority and ticket category |
| `incidents` | Incident-specific impact, urgency and affected service | One-to-one subtype of a ticket |
| `service_requests` | Request type and approval metadata | One-to-one subtype of a ticket |
| `support_staff` | Technician profile and specialisation | Each technician profile references one user |
| `ticket_assignments` | Timestamped assignment/reassignment history | Many assignments per ticket and per technician |
| `ticket_status_history` | Status audit events | Many status changes per ticket |
| `resolutions` | Resolution text, root cause and prevention | At most one current resolution per ticket |
| `maintenance_records` | Planned/completed service operations and costs | Many maintenance records per asset |

## Functional dependencies (representative)

- `department_id → department_name, location`; `department_name → department_id, location`.
- `user_id → employee_code, full_name, email, phone, department_id, role, is_active`; `employee_code → user_id, ...`; `email → user_id, ...`.
- `asset_category_id → category_name, description`; `category_name → asset_category_id, description`.
- `priority_id → priority_name, sla_hours, sort_order`; `priority_name → priority_id, sla_hours, sort_order`.
- `asset_id → asset_tag, asset_name, asset_category_id, department_id, assigned_user_id, manufacturer, model_number, serial_number, purchase_date, asset_status, location, notes`; `asset_tag → asset_id, ...`.
- `ticket_category_id → category_name, description`; `ticket_number → ticket_id, ticket_type, requester_id, asset_id, ticket_category_id, priority_id, title, description, status, created_at, updated_at, due_at, resolved_at`.
- `ticket_id → ticket_type, requester_id, asset_id, ticket_category_id, priority_id, title, description, status, created_at, updated_at, due_at, resolved_at`.
- `staff_id → user_id, staff_code, specialization, shift_name, is_available`; `staff_code → staff_id, ...`.
- `resolution_id → ticket_id, resolved_by, resolution_text, root_cause, resolved_at, preventive_action`; `ticket_id → resolution_id, ...` because `ticket_id` is unique in `resolutions`.
- `maintenance_id → asset_id, performed_by, maintenance_type, scheduled_date, completed_date, cost, status, notes, created_at`.

Assignment and status-history relations use their own surrogate keys because a ticket can be assigned repeatedly and can have multiple status events.

## Normalization rationale

- **1NF:** Attributes contain atomic values. Lists of assignees, ticket updates, warranty periods and maintenance history are not packed into a single column.
- **2NF:** Most relations use a single-column primary key. In relations with a ticket subtype, `ticket_id` alone determines every subtype attribute. There are no partial dependencies on part of a composite key.
- **3NF:** Department names live in `departments`, category labels in category lookup tables, SLA hours in `priorities`, user identity attributes in `users`, technician-only attributes in `support_staff`, and resolution content in `resolutions`. This avoids storing those descriptive facts redundantly in every ticket or asset row.

The one-to-one subtype tables are optional by ticket type. The application creates an `incidents` row for an incident and a `service_requests` row for a service request. SQLite's standard CHECK/FK constraints enforce value and reference integrity; the Flask application enforces cross-row transition rules (for example, resolution must be documented before a ticket is set to resolved).

## Indexing

The schema indexes ticket status/creation time, requester, asset reference and priority; active assignment lookup by staff or ticket; ticket status history by ticket and date; warranty expiry; asset tag; and asset maintenance by date. These correspond to frequent list, dashboard and reporting filters.

## ER diagram

See [`ER_DIAGRAM.mmd`](ER_DIAGRAM.mmd). Keep the final report ERD synchronized with `sql/schema_sqlite.sql` and the running application if the schema is changed.
