# Helix IT — IT Helpdesk & Asset Support Management

A database-backed web prototype for **Project 39: Design and Implementation of a Database Management System for IT Helpdesk and Asset Support Management System**.

Helix IT centralizes incident and service-request logging, asset inventory, warranty visibility, technician assignments, status history, resolutions, maintenance records and operational reports. It is designed as an academic DBMS prototype: the application uses SQL against a normalized relational schema, not static UI-only data.

> **Prototype note:** This version uses SQLite for zero-configuration local evaluation. SQLite is one of the options shown in the supplied report template. If the faculty requires MySQL/PostgreSQL specifically, use `sql/mysql_schema.sql` as the MySQL 8 schema reference and port the connector/configuration before describing the running application as MySQL-backed. The current running prototype is SQLite-backed.

> **Submission stage:** This package is the prototype-first milestone. The three real review presentations, final report and public Google Drive video-link document are listed in `presentations/README.md` and `submission/README.md` but are not fabricated as finished deliverables before the application is verified on your laptop.

## Features

- **Overview dashboard:** open tickets, urgent work, asset count, warranty watch, SLA ageing, ticket activity and technician workload.
- **Ticket management:** create incidents and service requests; search and filter; link assets; assign/reassign technicians; change status using allowed transitions; record resolutions and preventive action; inspect assignment and status history.
- **Asset inventory:** register, edit and search assets; unique asset tags and serial numbers; department/user ownership; lifecycle state; warranty records and linked support history.
- **Technician directory:** specialisation, availability, active workload and resolved ticket metrics.
- **Maintenance:** schedule preventive/corrective work, assign a technician, record costs and update maintenance status.
- **Reports:** open-ticket ageing, SLA due-date view, first-assignment response time, technician load, asset history, recurring issue categories, warranty expiry watch and CSV export.
- **Relational DBMS features:** primary and foreign keys, `UNIQUE`, `NOT NULL`, `CHECK`, `DEFAULT`, referential actions, transaction-scoped writes, history tables and indexes.
- **Sample data:** realistic synthetic records are seeded automatically on first launch. They are clearly for demonstration and are not production service metrics.

## Stack

- Python 3.10+
- Flask 3.x
- SQLite 3 (foreign-key enforcement enabled)
- HTML5, CSS and vanilla JavaScript
- Jinja templates

## Quick start — macOS / Linux

```bash
cd IT-Helpdesk-Asset-Support
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000**. The database is created at `instance/helpdesk.db` and sample data is added on the first run.

### Windows

```powershell
cd IT-Helpdesk-Asset-Support
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### Reset the demo database

This deletes the local demo database and recreates the schema and sample records:

```bash
python app.py --reset-db
```

Do not use the reset option after creating records you need to keep.

### Health check

Open `http://127.0.0.1:5000/health`. Expected response resembles:

```json
{"database":"connected","status":"ok","ticket_records":12}
```

## Recommended demo path

1. Open the Overview dashboard and review the ticket backlog and attention items.
2. Go to **Tickets → Log a ticket**. Create an incident or service request, assign a priority and optionally link an asset.
3. Open the ticket, assign a technician and change the status. The change is written to `ticket_status_history`.
4. Save a resolution. The app validates the minimum resolution details, records who performed the resolution and moves the ticket to `Resolved`.
5. Open **Asset inventory**, inspect an asset's warranty and ticket history, and register or edit a device.
6. Open **Maintenance** to add a preventive task and mark it completed.
7. Visit **Reports & analytics**, review ageing, response-time and warranty-expiry reports, then export the ticket CSV.

## Repository layout

```text
IT-Helpdesk-Asset-Support/
├── app.py                         # Flask routes, validation, SQL operations and seed data
├── requirements.txt
├── README.md
├── sql/
│   ├── schema_sqlite.sql          # Implemented schema used by the prototype
│   ├── mysql_schema.sql           # MySQL 8 schema reference for DBMS migration
│   └── report_queries.sql         # Representative SQL reports / joins / aggregates
├── docs/
│   ├── DATABASE_DESIGN.md         # Entities, relationships, functional dependencies, 3NF notes
│   └── ER_DIAGRAM.mmd              # Mermaid ER diagram source
├── templates/                     # Jinja HTML pages
├── static/
│   ├── css/style.css
│   └── js/app.js
├── tests/test_app.py
├── presentations/                 # Phase 1/2/3 slide decks are added after review content is confirmed
├── submission/                    # Final report / public video link checklist
└── instance/                      # Generated local DB; ignored by Git
```

## Database design overview

The schema separates department/user details from asset and ticket facts. `tickets` stores common fields for both incidents and service requests; the one-to-one subtype tables `incidents` and `service_requests` store type-specific fields. Priorities and categories are lookup tables. Assignment and status history are separate, timestamped relations rather than repeating columns inside a ticket row. A resolution is stored only for an existing ticket and has a unique ticket reference. Warranty and maintenance records are separate from the asset master, allowing multiple historic records per device.

### Main business rules

- `asset_tag`, `ticket_number`, employee code, user email and serial number (when supplied) are unique.
- Foreign keys protect links among users, departments, assets, tickets, support staff and history.
- Priority is chosen from the priority relation with its SLA hours.
- Allowed status transitions are checked in application logic; a ticket cannot be marked resolved through the generic status form without a documented resolution.
- Resolution notes must be meaningful before the ticket is marked resolved.
- Ticket deletion is restricted to a new, unassigned open ticket. Assets referenced by tickets cannot be deleted; retire them instead.
- Warranty start/end dates are checked for valid order; maintenance costs cannot be negative and date fields are validated.
- Frequently filtered ticket status/date, assignments, asset tags, warranty expiry and maintenance history have indexes.

## Testing

Run the automated route and database tests:

```bash
python -m unittest discover -s tests -v
```

The tests use a temporary database and do not modify your demo database.

## Important limitations

- This is a local academic prototype and has no login/authentication, production deployment configuration, email integration or role-based access control. Demo actions are attributed to a seeded administrator to make status history easy to demonstrate.
- Seed names, employees, phone numbers and service records are synthetic.
- The app is intentionally not intended to receive real personal, confidential or operational data.
- The MySQL schema is provided as a migration/reference artefact; the Flask routes in this first version are wired to SQLite.

## Academic project information

- **Project:** Project 39 — Design and Implementation of a Database Management System for IT Helpdesk and Asset Support Management System
- **Course:** Database Management Systems — Project-Based Learning
- **Institution:** Woxsen University, School of Technology

For the final submission, place the three phase presentations, final report, 5-minute prototype video link document and any required screenshots under a clearly named `presentations/`, `report/`, `video/` or `docs/` directory. Only claim features and test results that have actually been demonstrated.
