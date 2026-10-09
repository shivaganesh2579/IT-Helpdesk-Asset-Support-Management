from __future__ import annotations

import csv
import io
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from flask import (Flask, abort, flash, g, make_response, redirect, render_template,
                   request, url_for)

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("HELPDESK_DB_PATH", BASE_DIR / "instance" / "helpdesk.db"))
SCHEMA_PATH = BASE_DIR / "sql" / "schema_sqlite.sql"

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-key"),
    DATABASE=str(DATABASE_PATH),
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
)

STATUSES = ["Open", "Assigned", "In Progress", "On Hold", "Resolved", "Closed"]
STATUS_TRANSITIONS = {
    "Open": {"Assigned", "In Progress", "On Hold", "Resolved", "Closed"},
    "Assigned": {"Open", "In Progress", "On Hold", "Resolved", "Closed"},
    "In Progress": {"Assigned", "On Hold", "Resolved", "Closed"},
    "On Hold": {"Assigned", "In Progress", "Resolved", "Closed"},
    "Resolved": {"In Progress", "Closed", "Open"},
    "Closed": {"Open"},
}
TERMINAL_STATUSES = ("Resolved", "Closed")
DEMO_ADMIN_USER_ID = 1  # Prototype attribution only; authentication is intentionally not part of this academic demo.


def now_text() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        g.db = connection
    return g.db


@app.teardown_appcontext
def close_db(_error: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_all(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return get_db().execute(sql, params).fetchall()


def query_one(sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    return get_db().execute(sql, params).fetchone()


def init_db(reset: bool = False) -> None:
    """Create the relational schema and insert deterministic-style, realistic demo data."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if reset and DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    if db.execute("SELECT COUNT(*) FROM departments").fetchone()[0] == 0:
        _seed_database(db)
    db.commit()
    db.close()


def _seed_database(db: sqlite3.Connection) -> None:
    today = date.today()
    d = lambda offset: (today + timedelta(days=offset)).isoformat()
    dt = lambda offset, hour=10: datetime.combine(today + timedelta(days=offset), datetime.min.time()).replace(hour=hour).isoformat(sep=" ")

    departments = [
        ("Information Technology", "Admin Block"),
        ("Finance", "North Wing"),
        ("Human Resources", "Main Block"),
        ("Engineering", "Innovation Centre"),
        ("Library Services", "Learning Commons"),
    ]
    db.executemany("INSERT INTO departments(department_name, location) VALUES (?,?)", departments)

    asset_cats = [
        ("Laptop", "Portable computing device"), ("Desktop", "Workstation computer"),
        ("Network", "Routers, switches and network equipment"), ("Printer", "Printing and scanning equipment"),
        ("Peripheral", "Monitors and accessories"), ("Server", "Compute and storage infrastructure"),
    ]
    ticket_cats = [
        ("Hardware", "Physical device and component issues"),
        ("Software", "Applications, operating systems and updates"),
        ("Network", "Connectivity and access issues"),
        ("Access", "Account, permissions and identity requests"),
        ("Email & Collaboration", "Email, meetings and collaboration tools"),
        ("Asset Request", "New device or peripheral requests"),
    ]
    db.executemany("INSERT INTO asset_categories(category_name, description) VALUES (?,?)", asset_cats)
    db.executemany("INSERT INTO ticket_categories(category_name, description) VALUES (?,?)", ticket_cats)
    db.executemany("INSERT INTO priorities(priority_name, sla_hours, sort_order) VALUES (?,?,?)", [
        ("Critical", 2, 1), ("High", 4, 2), ("Medium", 8, 3), ("Low", 24, 4)
    ])

    users = [
        ("EMP-0001", "Anita Rao", "anita.rao@example.edu", "+91 90000 00001", 1, "Admin"),
        ("EMP-0102", "Rahul Verma", "rahul.verma@example.edu", "+91 90000 00102", 2, "Requester"),
        ("EMP-0103", "Meera Nair", "meera.nair@example.edu", "+91 90000 00103", 3, "Requester"),
        ("EMP-0104", "Arjun Reddy", "arjun.reddy@example.edu", "+91 90000 00104", 4, "Requester"),
        ("EMP-0105", "Sana Khan", "sana.khan@example.edu", "+91 90000 00105", 5, "Requester"),
        ("EMP-0201", "Kiran Das", "kiran.das@example.edu", "+91 90000 00201", 1, "Technician"),
        ("EMP-0202", "Divya Menon", "divya.menon@example.edu", "+91 90000 00202", 1, "Technician"),
        ("EMP-0203", "Vikram Shah", "vikram.shah@example.edu", "+91 90000 00203", 1, "Technician"),
        ("EMP-0204", "Priya Iyer", "priya.iyer@example.edu", "+91 90000 00204", 1, "Technician"),
        ("EMP-0106", "Nikhil Bose", "nikhil.bose@example.edu", "+91 90000 00106", 4, "Requester"),
    ]
    db.executemany("""INSERT INTO users(employee_code, full_name, email, phone, department_id, role)
                      VALUES (?,?,?,?,?,?)""", users)
    technicians = [
        (6, "TECH-001", "Hardware & Endpoint", "Morning", 1),
        (7, "TECH-002", "Applications & Identity", "General", 1),
        (8, "TECH-003", "Network & Infrastructure", "General", 1),
        (9, "TECH-004", "Asset Lifecycle", "Evening", 1),
    ]
    db.executemany("""INSERT INTO support_staff(user_id, staff_code, specialization, shift_name, is_available)
                      VALUES (?,?,?,?,?)""", technicians)

    assets = [
        ("AST-1001", "Finance Laptop", 1, 2, 2, "Dell", "Latitude 5440", "DL-5440-01", d(-280), "In Use", "North Wing · F-204", "Finance team allocation"),
        ("AST-1002", "HR Workstation", 2, 3, 3, "HP", "ProDesk 600 G6", "HP-600-22", d(-650), "In Use", "Main Block · HR-12", ""),
        ("AST-1003", "Core Network Switch", 3, 1, None, "Cisco", "Catalyst 9200", "CS-9200-07", d(-500), "In Use", "Server Room A", "Core campus distribution switch"),
        ("AST-1004", "Engineering Laptop", 1, 4, 4, "Lenovo", "ThinkPad E14 Gen 5", "LN-E14-33", d(-190), "In Use", "Innovation Centre · E-09", ""),
        ("AST-1005", "Library Printer", 4, 5, None, "Brother", "MFC-L8900CDW", "BR-L8900-04", d(-720), "In Repair", "Learning Commons · Print Desk", "Paper feed issue reported"),
        ("AST-1006", "IT Admin Desktop", 2, 1, 1, "Lenovo", "ThinkCentre M90", "LN-M90-16", d(-130), "In Use", "Admin Block · IT-02", ""),
        ("AST-1007", "Meeting Room Display", 5, 1, None, "Samsung", "ViewFinity S6", "SM-VS6-14", d(-90), "In Use", "Conference Room 2", ""),
        ("AST-1008", "Virtualization Host", 6, 1, None, "Dell", "PowerEdge R450", "PE-R450-02", d(-1000), "In Use", "Server Room B", "Hosts internal support tools"),
        ("AST-1009", "Spare Laptop", 1, 1, None, "Acer", "TravelMate P2", "AC-P2-19", d(-60), "In Stock", "IT Store · Shelf B", "Available for allocation"),
        ("AST-1010", "Old Training Desktop", 2, 4, None, "HP", "ProDesk 400 G4", "HP-400-08", d(-1500), "Retired", "Asset Store", "Retired after lifecycle review"),
    ]
    db.executemany("""INSERT INTO assets(asset_tag, asset_name, asset_category_id, department_id, assigned_user_id,
                      manufacturer, model_number, serial_number, purchase_date, asset_status, location, notes)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", assets)

    warranties = [
        (1, "Dell ProSupport", d(-250), d(25), "On-site hardware support and parts", "WAR-DL-1001"),
        (2, "HP Care Pack", d(-620), d(-15), "Hardware repair and parts", "WAR-HP-1002"),
        (3, "Cisco Smart Net", d(-300), d(120), "Network equipment support", "WAR-CS-1003"),
        (4, "Lenovo Premier Support", d(-180), d(185), "On-site repair and technical support", "WAR-LN-1004"),
        (5, "Brother Service Plan", d(-700), d(7), "Printer parts and service", "WAR-BR-1005"),
        (6, "Lenovo On-site", d(-120), d(245), "Desktop hardware support", "WAR-LN-1006"),
        (8, "Dell ProSupport Plus", d(-950), d(-2), "Server hardware and critical response", "WAR-PE-1008"),
        (9, "Acer Limited Warranty", d(-45), d(320), "Standard limited warranty", "WAR-AC-1009"),
    ]
    db.executemany("""INSERT INTO warranties(asset_id, provider, warranty_start, warranty_end, coverage_details, reference_number)
                      VALUES (?,?,?,?,?,?)""", warranties)

    # Seed tickets use dates relative to the current date so the age/SLA views remain meaningful.
    tickets = [
        ("HD-26001", "Incident", 2, 1, 1, 1, "Core switch packet loss", "Intermittent packet loss affecting the finance and library VLANs.", "In Progress", -1, 0, 1),
        ("HD-26002", "Incident", 3, 2, 2, 2, "Laptop shuts down unexpectedly", "The HR workstation shuts down after several minutes of use.", "Assigned", -3, 0, 2),
        ("HD-26003", "Service Request", 4, 4, 6, 3, "Request for external monitor", "Please provide an external display for the engineering design workflow.", "Open", -2, 1, 0),
        ("HD-26004", "Incident", 5, 5, 1, 2, "Printer paper feed jam", "Library printer repeatedly jams when printing duplex jobs.", "On Hold", -5, 0, 4),
        ("HD-26005", "Incident", 6, 6, 2, 3, "VPN client fails to connect", "VPN client displays a connection timeout after the latest update.", "Resolved", -4, 0, 2),
        ("HD-26006", "Service Request", 2, 1, 4, 4, "Shared mailbox access", "Grant access to the quarterly-close shared mailbox.", "Closed", -12, 0, 3),
        ("HD-26007", "Incident", 4, 4, 2, 3, "Laptop battery drains quickly", "Battery runtime has reduced to less than 45 minutes.", "Open", -7, 0, 1),
        ("HD-26008", "Incident", 3, 2, 5, 3, "Email sync delay", "Desktop email sync is delayed by 20–30 minutes.", "Resolved", -8, 0, 2),
        ("HD-26009", "Service Request", 5, None, 6, 3, "New staff account setup", "Create account and base application access for a new staff member.", "Assigned", -1, 1, 0),
        ("HD-26010", "Incident", 10, 8, 3, 1, "Internal support portal unavailable", "Internal portal intermittently returns a 502 gateway error.", "In Progress", 0, 0, 3),
        ("HD-26011", "Incident", 2, 1, 1, 2, "Network connectivity drop", "Network connection drops intermittently in the finance area.", "Closed", -20, 0, 2),
        ("HD-26012", "Service Request", 3, 7, 6, 4, "Install approved PDF software", "Install the approved PDF tool on the HR workstation.", "Resolved", -2, 1, 0),
    ]
    ticket_ids: dict[str, int] = {}
    for ticket_no, ticket_type, requester, asset, category, priority, title, desc, status, age_days, request_child, tech in tickets:
        created_at = dt(age_days, 9 + (len(ticket_ids) % 7))
        sla_row = db.execute("SELECT sla_hours FROM priorities WHERE priority_id = ?", (priority,)).fetchone()
        created_dt = datetime.fromisoformat(created_at)
        due_at = (created_dt + timedelta(hours=sla_row[0])).isoformat(sep=" ")
        resolved_at = dt(age_days + 1, 14) if status in ("Resolved", "Closed") else None
        cur = db.execute("""INSERT INTO tickets(ticket_number, ticket_type, requester_id, asset_id, ticket_category_id,
                          priority_id, title, description, status, created_at, updated_at, due_at, resolved_at)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (ticket_no, ticket_type, requester, asset, category, priority, title, desc, status,
                          created_at, now_text(), due_at, resolved_at))
        tid = cur.lastrowid
        ticket_ids[ticket_no] = tid
        if ticket_type == "Incident":
            db.execute("INSERT INTO incidents(ticket_id, impact, urgency, occurred_at, affected_service) VALUES (?,?,?,?,?)",
                       (tid, "High" if priority <= 2 else "Moderate", "High" if priority <= 2 else "Moderate", created_at, "Campus IT service"))
        else:
            db.execute("INSERT INTO service_requests(ticket_id, request_type, approval_status, requested_for) VALUES (?,?,?,?)",
                       (tid, "Access / equipment request" if category in (4, 6) else "Software installation", "Approved" if status in ("Resolved", "Closed") else ("Pending" if priority <= 2 else "Not Required"), "Requester"))
        db.execute("INSERT INTO ticket_status_history(ticket_id, old_status, new_status, changed_by, changed_at, note) VALUES (?,?,?,?,?,?)",
                   (tid, None, "Open", requester, created_at, "Ticket logged"))
        # Keep the seeded audit trail consistent with the current status.
        status_chain = {
            "Open": [], "Assigned": ["Assigned"],
            "In Progress": ["Assigned", "In Progress"],
            "On Hold": ["Assigned", "In Progress", "On Hold"],
            "Resolved": ["Assigned", "In Progress", "Resolved"],
            "Closed": ["Assigned", "In Progress", "Resolved", "Closed"],
        }
        previous_status = "Open"
        for step_index, next_status in enumerate(status_chain[status], start=1):
            event_time = created_dt + timedelta(minutes=18 * step_index)
            if next_status == "Resolved" and resolved_at:
                event_time = datetime.fromisoformat(resolved_at)
            elif next_status == "Closed" and resolved_at:
                event_time = datetime.fromisoformat(resolved_at) + timedelta(minutes=30)
            db.execute("INSERT INTO ticket_status_history(ticket_id, old_status, new_status, changed_by, changed_at, note) VALUES (?,?,?,?,?,?)",
                       (tid, previous_status, next_status, DEMO_ADMIN_USER_ID, event_time, "Initial triage" if next_status == "Assigned" else "Demo workflow update"))
            previous_status = next_status
        if tech:
            assignee_staff = tech if tech <= 4 else 1
            assigned_at = (created_dt + timedelta(minutes=15)).isoformat(sep=" ")
            unassigned_at = (created_dt + timedelta(hours=2)).isoformat(sep=" ") if status in ("Resolved", "Closed") else None
            db.execute("""INSERT INTO ticket_assignments(ticket_id, staff_id, assigned_by, assigned_at, unassigned_at, assignment_note)
                          VALUES (?,?,?,?,?,?)""", (tid, assignee_staff, DEMO_ADMIN_USER_ID, assigned_at, unassigned_at, "Initial triage assignment"))
        if status in ("Resolved", "Closed"):
            resolved_staff = tech if tech else 2
            resolution = "Reconfigured the affected client/service, verified recovery with the requester, and documented the checks performed."
            db.execute("""INSERT INTO resolutions(ticket_id, resolved_by, resolution_text, root_cause, resolved_at, preventive_action)
                          VALUES (?,?,?,?,?,?)""", (tid, resolved_staff, resolution, "Configuration drift / local client issue", resolved_at, "Add the check to the next preventive review."))

    maintenance = [
        (3, 3, "Preventive", d(5), None, 0.0, "Scheduled", "Quarterly firmware and port-health review"),
        (5, 4, "Corrective", d(-1), d(0), 1200.0, "Completed", "Cleaned rollers and tested duplex feed"),
        (8, 3, "Inspection", d(18), None, 0.0, "Scheduled", "Review storage alerts and fan status"),
        (1, 1, "Preventive", d(30), None, 2500.0, "Scheduled", "Endpoint diagnostics and battery health"),
        (6, 1, "Upgrade", d(-8), d(-7), 650.0, "Completed", "Memory upgrade and post-upgrade validation"),
    ]
    db.executemany("""INSERT INTO maintenance_records(asset_id, performed_by, maintenance_type, scheduled_date,
                      completed_date, cost, status, notes) VALUES (?,?,?,?,?,?,?,?)""", maintenance)


def load_reference_data() -> dict[str, list[sqlite3.Row]]:
    return {
        "departments": query_all("SELECT department_id, department_name FROM departments ORDER BY department_name"),
        "users": query_all("SELECT user_id, full_name, employee_code FROM users WHERE is_active=1 ORDER BY full_name"),
        "requesters": query_all("SELECT user_id, full_name, employee_code FROM users WHERE is_active=1 AND role IN ('Requester','Admin') ORDER BY full_name"),
        "asset_categories": query_all("SELECT asset_category_id, category_name FROM asset_categories ORDER BY category_name"),
        "ticket_categories": query_all("SELECT ticket_category_id, category_name FROM ticket_categories ORDER BY category_name"),
        "priorities": query_all("SELECT priority_id, priority_name, sla_hours FROM priorities ORDER BY sort_order"),
        "assets": query_all("SELECT asset_id, asset_tag, asset_name FROM assets WHERE asset_status != 'Retired' ORDER BY asset_tag"),
        "technicians": query_all("""SELECT s.staff_id, s.staff_code, u.full_name, s.specialization
                                  FROM support_staff s JOIN users u ON u.user_id=s.user_id
                                  WHERE s.is_available=1 ORDER BY u.full_name"""),
    }


@app.context_processor
def inject_globals() -> dict[str, Any]:
    open_count = 0
    try:
        row = query_one("SELECT COUNT(*) AS count FROM tickets WHERE status NOT IN ('Resolved','Closed')")
        open_count = row["count"] if row else 0
    except sqlite3.Error:
        # Lets the app render its fallback page even if the local database has not been initialized yet.
        pass
    return {"today": date.today().isoformat(), "statuses": STATUSES, "active_endpoint": request.endpoint or "",
            "open_ticket_count": open_count}


@app.route("/")
def dashboard():
    totals = query_one("""SELECT
        COUNT(*) AS total_tickets,
        SUM(CASE WHEN status IN ('Open','Assigned','In Progress','On Hold') THEN 1 ELSE 0 END) AS open_tickets,
        SUM(CASE WHEN status='Resolved' THEN 1 ELSE 0 END) AS resolved_tickets,
        SUM(CASE WHEN priority_id IN (SELECT priority_id FROM priorities WHERE priority_name IN ('Critical','High'))
                 AND status NOT IN ('Resolved','Closed') THEN 1 ELSE 0 END) AS urgent_tickets
        FROM tickets""")
    asset_stats = query_one("""SELECT COUNT(*) AS total_assets,
        SUM(CASE WHEN asset_status='In Repair' THEN 1 ELSE 0 END) AS in_repair,
        SUM(CASE WHEN asset_status='In Stock' THEN 1 ELSE 0 END) AS in_stock FROM assets""")
    expiring = query_one("""SELECT COUNT(DISTINCT asset_id) AS count FROM warranties
                          WHERE date(warranty_end) BETWEEN date('now') AND date('now','+30 day')""")["count"]
    breached = query_one("""SELECT COUNT(*) AS count FROM tickets
                           WHERE status NOT IN ('Resolved','Closed') AND due_at IS NOT NULL AND datetime(due_at) < datetime('now')""")["count"]
    recent_tickets = query_all("""SELECT t.ticket_id, t.ticket_number, t.title, t.ticket_type, t.status, t.created_at,
            u.full_name AS requester_name, c.category_name, p.priority_name,
            (SELECT su.full_name FROM ticket_assignments a JOIN support_staff ss ON ss.staff_id=a.staff_id
             JOIN users su ON su.user_id=ss.user_id WHERE a.ticket_id=t.ticket_id AND a.unassigned_at IS NULL
             ORDER BY a.assigned_at DESC LIMIT 1) AS assignee_name
            FROM tickets t JOIN users u ON u.user_id=t.requester_id
            JOIN ticket_categories c ON c.ticket_category_id=t.ticket_category_id
            JOIN priorities p ON p.priority_id=t.priority_id
            ORDER BY CASE WHEN t.status IN ('Open','Assigned','In Progress','On Hold') THEN 0 ELSE 1 END,
                     t.created_at DESC LIMIT 7""")
    workload = query_all("""SELECT s.staff_id, u.full_name, s.specialization,
            SUM(CASE WHEN t.status NOT IN ('Resolved','Closed') THEN 1 ELSE 0 END) AS active_count,
            SUM(CASE WHEN t.status='Resolved' THEN 1 ELSE 0 END) AS resolved_count
            FROM support_staff s JOIN users u ON u.user_id=s.user_id
            LEFT JOIN ticket_assignments a ON a.staff_id=s.staff_id AND a.unassigned_at IS NULL
            LEFT JOIN tickets t ON t.ticket_id=a.ticket_id
            GROUP BY s.staff_id ORDER BY active_count DESC, u.full_name LIMIT 4""")
    categories = query_all("""SELECT c.category_name, COUNT(t.ticket_id) AS total
            FROM ticket_categories c LEFT JOIN tickets t ON t.ticket_category_id=c.ticket_category_id
            GROUP BY c.ticket_category_id ORDER BY total DESC, c.category_name LIMIT 5""")
    all_categories = sum(row["total"] for row in categories) or 1
    return render_template("dashboard.html", totals=totals, asset_stats=asset_stats, expiring=expiring,
                           breached=breached, recent_tickets=recent_tickets, workload=workload,
                           categories=categories, all_categories=all_categories)


@app.route("/tickets")
def tickets():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()
    ticket_type = request.args.get("type", "").strip()
    sql = """SELECT t.ticket_id, t.ticket_number, t.ticket_type, t.title, t.status, t.created_at,
             u.full_name AS requester_name, c.category_name, p.priority_name, a.asset_tag,
             (SELECT su.full_name FROM ticket_assignments ta JOIN support_staff ss ON ss.staff_id=ta.staff_id
              JOIN users su ON su.user_id=ss.user_id WHERE ta.ticket_id=t.ticket_id AND ta.unassigned_at IS NULL
              ORDER BY ta.assigned_at DESC LIMIT 1) AS assignee_name
             FROM tickets t JOIN users u ON u.user_id=t.requester_id
             JOIN ticket_categories c ON c.ticket_category_id=t.ticket_category_id
             JOIN priorities p ON p.priority_id=t.priority_id LEFT JOIN assets a ON a.asset_id=t.asset_id WHERE 1=1"""
    params: list[Any] = []
    if search:
        sql += " AND (t.ticket_number LIKE ? OR t.title LIKE ? OR u.full_name LIKE ? OR a.asset_tag LIKE ?)"
        params.extend([f"%{search}%"] * 4)
    if status:
        sql += " AND t.status = ?"
        params.append(status)
    if priority:
        sql += " AND p.priority_name = ?"
        params.append(priority)
    if ticket_type:
        sql += " AND t.ticket_type = ?"
        params.append(ticket_type)
    sql += " ORDER BY CASE WHEN t.status IN ('Open','Assigned','In Progress','On Hold') THEN 0 ELSE 1 END, t.created_at DESC"
    rows = query_all(sql, tuple(params))
    return render_template("tickets.html", tickets=rows, refs=load_reference_data(), filters={"q": search, "status": status, "priority": priority, "type": ticket_type})


@app.route("/tickets/new", methods=["GET", "POST"])
def ticket_new():
    refs = load_reference_data()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        ticket_type = request.form.get("ticket_type", "Incident")
        if len(title) < 3 or len(description) < 5:
            flash("Add a descriptive title and a description of at least 5 characters.", "error")
            return render_template("ticket_form.html", refs=refs, form=request.form, page_title="Log a ticket")
        if ticket_type not in ("Incident", "Service Request"):
            flash("Choose a valid ticket type.", "error")
            return render_template("ticket_form.html", refs=refs, form=request.form, page_title="Log a ticket")
        try:
            requester_id = int(request.form["requester_id"])
            priority_id = int(request.form["priority_id"])
            category_id = int(request.form["ticket_category_id"])
            asset_id = int(request.form["asset_id"]) if request.form.get("asset_id") else None
            db = get_db()
            priority = db.execute("SELECT sla_hours FROM priorities WHERE priority_id=?", (priority_id,)).fetchone()
            if not priority:
                raise ValueError("Select a valid priority.")
            due_at = (datetime.now() + timedelta(hours=priority["sla_hours"])).replace(microsecond=0).isoformat(sep=" ")
            year_code = str(date.today().year)[-2:]
            max_no = db.execute("SELECT MAX(CAST(substr(ticket_number, 6) AS INTEGER)) FROM tickets WHERE ticket_number LIKE ?", (f"HD-{year_code}%",)).fetchone()[0] or 0
            ticket_number = f"HD-{year_code}{max_no + 1:03d}"
            with db:
                cur = db.execute("""INSERT INTO tickets(ticket_number,ticket_type,requester_id,asset_id,ticket_category_id,
                                   priority_id,title,description,status,created_at,updated_at,due_at)
                                   VALUES (?,?,?,?,?,?,?,?,'Open',?,?,?)""",
                                 (ticket_number, ticket_type, requester_id, asset_id, category_id, priority_id, title, description, now_text(), now_text(), due_at))
                tid = cur.lastrowid
                if ticket_type == "Incident":
                    db.execute("INSERT INTO incidents(ticket_id,impact,urgency,occurred_at,affected_service) VALUES (?,?,?,?,?)",
                               (tid, request.form.get("impact", "Moderate"), request.form.get("urgency", "Moderate"), now_text(), request.form.get("affected_service", "IT service")))
                else:
                    db.execute("INSERT INTO service_requests(ticket_id,request_type,approval_status,requested_for) VALUES (?,?,?,?)",
                               (tid, request.form.get("request_type", "General request"), request.form.get("approval_status", "Not Required"), request.form.get("requested_for", "Requester")))
                db.execute("INSERT INTO ticket_status_history(ticket_id,old_status,new_status,changed_by,changed_at,note) VALUES (?,NULL,'Open',?,?,?)",
                           (tid, requester_id, now_text(), "Ticket created"))
            flash(f"Ticket {ticket_number} was created successfully.", "success")
            return redirect(url_for("ticket_detail", ticket_id=tid))
        except (ValueError, KeyError, sqlite3.IntegrityError) as exc:
            flash(f"Could not create ticket: {exc}", "error")
    return render_template("ticket_form.html", refs=refs, form={}, page_title="Log a ticket")


@app.route("/tickets/<int:ticket_id>")
def ticket_detail(ticket_id: int):
    ticket = query_one("""SELECT t.*, u.full_name AS requester_name, u.email AS requester_email, d.department_name,
        c.category_name, p.priority_name, p.sla_hours, a.asset_tag, a.asset_name, a.model_number,
        (SELECT ss.staff_id FROM ticket_assignments ta JOIN support_staff ss ON ss.staff_id=ta.staff_id
         WHERE ta.ticket_id=t.ticket_id AND ta.unassigned_at IS NULL ORDER BY ta.assigned_at DESC LIMIT 1) AS current_staff_id,
        (SELECT su.full_name FROM ticket_assignments ta JOIN support_staff ss ON ss.staff_id=ta.staff_id
         JOIN users su ON su.user_id=ss.user_id WHERE ta.ticket_id=t.ticket_id AND ta.unassigned_at IS NULL
         ORDER BY ta.assigned_at DESC LIMIT 1) AS assignee_name
        FROM tickets t JOIN users u ON u.user_id=t.requester_id JOIN departments d ON d.department_id=u.department_id
        JOIN ticket_categories c ON c.ticket_category_id=t.ticket_category_id JOIN priorities p ON p.priority_id=t.priority_id
        LEFT JOIN assets a ON a.asset_id=t.asset_id WHERE t.ticket_id=?""", (ticket_id,))
    if not ticket:
        abort(404)
    history = query_all("""SELECT h.*, u.full_name AS changed_by_name FROM ticket_status_history h
                         JOIN users u ON u.user_id=h.changed_by WHERE h.ticket_id=? ORDER BY h.changed_at DESC, h.history_id DESC""", (ticket_id,))
    assignments = query_all("""SELECT ta.*, u.full_name AS technician_name, s.staff_code, s.specialization
                              FROM ticket_assignments ta JOIN support_staff s ON s.staff_id=ta.staff_id
                              JOIN users u ON u.user_id=s.user_id WHERE ta.ticket_id=? ORDER BY ta.assigned_at DESC""", (ticket_id,))
    resolution = query_one("""SELECT r.*, u.full_name AS resolved_by_name FROM resolutions r
                              JOIN support_staff s ON s.staff_id=r.resolved_by JOIN users u ON u.user_id=s.user_id
                              WHERE r.ticket_id=?""", (ticket_id,))
    child = query_one("SELECT * FROM incidents WHERE ticket_id=?", (ticket_id,)) if ticket["ticket_type"] == "Incident" else query_one("SELECT * FROM service_requests WHERE ticket_id=?", (ticket_id,))
    return render_template("ticket_detail.html", ticket=ticket, history=history, assignments=assignments,
                           resolution=resolution, child=child, refs=load_reference_data(),
                           allowed_transitions=sorted(STATUS_TRANSITIONS[ticket["status"]]))


@app.route("/tickets/<int:ticket_id>/assign", methods=["POST"])
def ticket_assign(ticket_id: int):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
    if not ticket:
        abort(404)
    if ticket["status"] in TERMINAL_STATUSES:
        flash("Reopen a resolved or closed ticket before changing its assignment.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    try:
        staff_id = int(request.form.get("staff_id", ""))
    except ValueError:
        flash("Choose a valid technician.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    staff = db.execute("SELECT * FROM support_staff WHERE staff_id=? AND is_available=1", (staff_id,)).fetchone()
    if not staff:
        flash("That technician is not available for assignment.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    with db:
        db.execute("UPDATE ticket_assignments SET unassigned_at=? WHERE ticket_id=? AND unassigned_at IS NULL", (now_text(), ticket_id))
        db.execute("INSERT INTO ticket_assignments(ticket_id,staff_id,assigned_by,assigned_at,assignment_note) VALUES (?,?,?,?,?)",
                   (ticket_id, staff_id, DEMO_ADMIN_USER_ID, now_text(), request.form.get("assignment_note", "Assigned from ticket workspace").strip()))
        if ticket["status"] == "Open":
            db.execute("UPDATE tickets SET status='Assigned', updated_at=? WHERE ticket_id=?", (now_text(), ticket_id))
            db.execute("INSERT INTO ticket_status_history(ticket_id,old_status,new_status,changed_by,changed_at,note) VALUES (?,?,'Assigned',?,?,?)",
                       (ticket_id, "Open", DEMO_ADMIN_USER_ID, now_text(), "Technician assigned"))
    flash("Technician assignment updated.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.route("/tickets/<int:ticket_id>/status", methods=["POST"])
def ticket_status(ticket_id: int):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
    if not ticket:
        abort(404)
    new_status = request.form.get("status", "")
    note = request.form.get("note", "").strip()
    if new_status not in STATUS_TRANSITIONS.get(ticket["status"], set()):
        flash(f"Status transition from {ticket['status']} to {new_status} is not allowed.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    if new_status == "Resolved":
        flash("To resolve a ticket, use the Resolution form and document the fix.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    if new_status == "Closed" and ticket["status"] != "Resolved":
        flash("Record a resolution before closing a ticket.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    with db:
        if new_status in ("Closed", "Open"):
            db.execute("UPDATE ticket_assignments SET unassigned_at=? WHERE ticket_id=? AND unassigned_at IS NULL", (now_text(), ticket_id))
        db.execute("UPDATE tickets SET status=?, updated_at=?, resolved_at=CASE WHEN ? IN ('Open','Assigned','In Progress','On Hold') THEN NULL ELSE resolved_at END WHERE ticket_id=?",
                   (new_status, now_text(), new_status, ticket_id))
        db.execute("INSERT INTO ticket_status_history(ticket_id,old_status,new_status,changed_by,changed_at,note) VALUES (?,?,?,?,?,?)",
                   (ticket_id, ticket["status"], new_status, DEMO_ADMIN_USER_ID, now_text(), note or "Status updated"))
    flash(f"Ticket status changed to {new_status}.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.route("/tickets/<int:ticket_id>/resolve", methods=["POST"])
def ticket_resolve(ticket_id: int):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
    if not ticket:
        abort(404)
    if ticket["status"] == "Closed":
        flash("Reopen the ticket before updating its resolution.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    text = request.form.get("resolution_text", "").strip()
    if len(text) < 8:
        flash("Resolution details must contain at least 8 characters.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    staff_value = request.form.get("resolved_by", "").strip()
    try:
        staff_id = int(staff_value)
    except ValueError:
        current = db.execute("SELECT staff_id FROM ticket_assignments WHERE ticket_id=? AND unassigned_at IS NULL ORDER BY assigned_at DESC LIMIT 1", (ticket_id,)).fetchone()
        staff_id = current["staff_id"] if current else None
    if not staff_id or not db.execute("SELECT 1 FROM support_staff WHERE staff_id=?", (staff_id,)).fetchone():
        flash("Select a technician who performed the resolution.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    resolved_at = now_text()
    with db:
        existing = db.execute("SELECT resolution_id FROM resolutions WHERE ticket_id=?", (ticket_id,)).fetchone()
        if existing:
            db.execute("""UPDATE resolutions SET resolved_by=?, resolution_text=?, root_cause=?, resolved_at=?, preventive_action=?
                          WHERE ticket_id=?""", (staff_id, text, request.form.get("root_cause", "").strip(), resolved_at,
                                                   request.form.get("preventive_action", "").strip(), ticket_id))
        else:
            db.execute("""INSERT INTO resolutions(ticket_id,resolved_by,resolution_text,root_cause,resolved_at,preventive_action)
                          VALUES (?,?,?,?,?,?)""", (ticket_id, staff_id, text, request.form.get("root_cause", "").strip(),
                                                     resolved_at, request.form.get("preventive_action", "").strip()))
        if ticket["status"] != "Resolved":
            db.execute("INSERT INTO ticket_status_history(ticket_id,old_status,new_status,changed_by,changed_at,note) VALUES (?,?,?,?,?,?)",
                       (ticket_id, ticket["status"], "Resolved", DEMO_ADMIN_USER_ID, resolved_at, "Resolution recorded"))
        db.execute("UPDATE tickets SET status='Resolved', resolved_at=?, updated_at=? WHERE ticket_id=?", (resolved_at, resolved_at, ticket_id))
        db.execute("UPDATE ticket_assignments SET unassigned_at=? WHERE ticket_id=? AND unassigned_at IS NULL", (resolved_at, ticket_id))
    flash("Resolution saved and ticket marked as resolved.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.route("/tickets/<int:ticket_id>/delete", methods=["POST"])
def ticket_delete(ticket_id: int):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
    if not ticket:
        abort(404)
    if ticket["status"] != "Open":
        flash("Only unassigned Open tickets can be deleted. Use status history for the audit trail on active work.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    assigned = db.execute("SELECT 1 FROM ticket_assignments WHERE ticket_id=?", (ticket_id,)).fetchone()
    if assigned:
        flash("This ticket has assignment history and cannot be removed.", "error")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    with db:
        db.execute("DELETE FROM tickets WHERE ticket_id=?", (ticket_id,))
    flash(f"Ticket {ticket['ticket_number']} was removed.", "success")
    return redirect(url_for("tickets"))


@app.route("/assets")
def assets():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    sql = """SELECT a.*, ac.category_name, d.department_name, u.full_name AS assigned_to,
        (SELECT MAX(w.warranty_end) FROM warranties w WHERE w.asset_id=a.asset_id) AS warranty_end,
        (SELECT COUNT(*) FROM tickets t WHERE t.asset_id=a.asset_id) AS ticket_count
        FROM assets a JOIN asset_categories ac ON ac.asset_category_id=a.asset_category_id
        JOIN departments d ON d.department_id=a.department_id LEFT JOIN users u ON u.user_id=a.assigned_user_id WHERE 1=1"""
    params: list[Any] = []
    if search:
        sql += " AND (a.asset_tag LIKE ? OR a.asset_name LIKE ? OR a.model_number LIKE ? OR a.serial_number LIKE ? OR d.department_name LIKE ?)"
        params.extend([f"%{search}%"] * 5)
    if status:
        sql += " AND a.asset_status=?"
        params.append(status)
    sql += " ORDER BY CASE a.asset_status WHEN 'In Repair' THEN 0 WHEN 'In Use' THEN 1 WHEN 'In Stock' THEN 2 ELSE 3 END, a.asset_tag"
    return render_template("assets.html", assets=query_all(sql, tuple(params)), filters={"q": search, "status": status})


@app.route("/assets/new", methods=["GET", "POST"])
def asset_new():
    refs = load_reference_data()
    if request.method == "POST":
        form = request.form
        required = [form.get("asset_tag", "").strip(), form.get("asset_name", "").strip(), form.get("manufacturer", "").strip(), form.get("model_number", "").strip(), form.get("purchase_date", "").strip()]
        if not all(required):
            flash("Complete all required asset fields.", "error")
            return render_template("asset_form.html", refs=refs, form=form, page_title="Register asset")
        try:
            purchase_date_value = date.fromisoformat(required[4])
            if purchase_date_value > date.today():
                raise ValueError("Purchase date cannot be in the future.")
            warranty_provider = form.get("warranty_provider", "").strip()
            warranty_start = form.get("warranty_start", "").strip()
            warranty_end = form.get("warranty_end", "").strip()
            if any([warranty_provider, warranty_start, warranty_end]) and not all([warranty_provider, warranty_start, warranty_end]):
                raise ValueError("For warranty tracking, enter the provider and both start/end dates.")
            db = get_db()
            with db:
                cur = db.execute("""INSERT INTO assets(asset_tag,asset_name,asset_category_id,department_id,assigned_user_id,
                                 manufacturer,model_number,serial_number,purchase_date,asset_status,location,notes)
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                                 (required[0], required[1], int(form["asset_category_id"]), int(form["department_id"]),
                                  int(form["assigned_user_id"]) if form.get("assigned_user_id") else None,
                                  required[2], required[3], form.get("serial_number", "").strip() or None,
                                  required[4], form.get("asset_status", "In Use"), form.get("location", "Main Campus").strip(),
                                  form.get("notes", "").strip()))
                aid = cur.lastrowid
                if warranty_provider and warranty_start and warranty_end:
                    db.execute("INSERT INTO warranties(asset_id,provider,warranty_start,warranty_end,coverage_details,reference_number) VALUES (?,?,?,?,?,?)",
                               (aid, warranty_provider, warranty_start, warranty_end, form.get("coverage_details", "Standard manufacturer coverage"), form.get("warranty_reference", "").strip() or None))
            flash(f"Asset {required[0]} registered successfully.", "success")
            return redirect(url_for("asset_detail", asset_id=aid))
        except (ValueError, sqlite3.IntegrityError) as exc:
            flash(f"Could not register asset: {exc}", "error")
            return render_template("asset_form.html", refs=refs, form=form, page_title="Register asset")
    return render_template("asset_form.html", refs=refs, form={}, page_title="Register asset")


@app.route("/assets/<int:asset_id>")
def asset_detail(asset_id: int):
    asset = query_one("""SELECT a.*, ac.category_name, d.department_name, u.full_name AS assigned_to,
                        u.email AS assigned_email FROM assets a JOIN asset_categories ac ON ac.asset_category_id=a.asset_category_id
                        JOIN departments d ON d.department_id=a.department_id LEFT JOIN users u ON u.user_id=a.assigned_user_id
                        WHERE a.asset_id=?""", (asset_id,))
    if not asset:
        abort(404)
    warranties = query_all("SELECT * FROM warranties WHERE asset_id=? ORDER BY warranty_end DESC", (asset_id,))
    maintenance_rows = query_all("""SELECT m.*, u.full_name AS technician_name FROM maintenance_records m
                                 LEFT JOIN support_staff s ON s.staff_id=m.performed_by LEFT JOIN users u ON u.user_id=s.user_id
                                 WHERE m.asset_id=? ORDER BY m.scheduled_date DESC""", (asset_id,))
    related_tickets = query_all("""SELECT ticket_id,ticket_number,title,status,created_at FROM tickets WHERE asset_id=?
                                ORDER BY created_at DESC LIMIT 8""", (asset_id,))
    return render_template("asset_detail.html", asset=asset, warranties=warranties, maintenance=maintenance_rows, tickets=related_tickets, refs=load_reference_data())


@app.route("/assets/<int:asset_id>/edit", methods=["GET", "POST"])
def asset_edit(asset_id: int):
    asset = query_one("SELECT * FROM assets WHERE asset_id=?", (asset_id,))
    if not asset:
        abort(404)
    refs = load_reference_data()
    if request.method == "POST":
        form = request.form
        try:
            edit_purchase_date = date.fromisoformat(form.get("purchase_date", ""))
            if edit_purchase_date > date.today():
                raise ValueError("Purchase date cannot be in the future.")
            with get_db() as db:
                db.execute("""UPDATE assets SET asset_tag=?,asset_name=?,asset_category_id=?,department_id=?,assigned_user_id=?,
                              manufacturer=?,model_number=?,serial_number=?,purchase_date=?,asset_status=?,location=?,notes=? WHERE asset_id=?""",
                           (form.get("asset_tag", "").strip(), form.get("asset_name", "").strip(), int(form["asset_category_id"]),
                            int(form["department_id"]), int(form["assigned_user_id"]) if form.get("assigned_user_id") else None,
                            form.get("manufacturer", "").strip(), form.get("model_number", "").strip(), form.get("serial_number", "").strip() or None,
                            form.get("purchase_date", ""), form.get("asset_status", "In Use"), form.get("location", "").strip(),
                            form.get("notes", "").strip(), asset_id))
            flash("Asset details updated.", "success")
            return redirect(url_for("asset_detail", asset_id=asset_id))
        except (ValueError, KeyError, sqlite3.IntegrityError) as exc:
            flash(f"Could not update asset: {exc}", "error")
            return render_template("asset_form.html", refs=refs, form=form, page_title=f"Edit {asset['asset_tag']}", asset=asset)
    form = dict(asset)
    return render_template("asset_form.html", refs=refs, form=form, page_title=f"Edit {asset['asset_tag']}", asset=asset)


@app.route("/assets/<int:asset_id>/delete", methods=["POST"])
def asset_delete(asset_id: int):
    db = get_db()
    asset = db.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
    if not asset:
        abort(404)
    linked = db.execute("SELECT COUNT(*) FROM tickets WHERE asset_id=?", (asset_id,)).fetchone()[0]
    if linked:
        flash("This asset is referenced by tickets. Retire it instead of deleting it to preserve history.", "error")
        return redirect(url_for("asset_detail", asset_id=asset_id))
    with db:
        db.execute("DELETE FROM assets WHERE asset_id=?", (asset_id,))
    flash(f"Asset {asset['asset_tag']} deleted.", "success")
    return redirect(url_for("assets"))


@app.route("/maintenance", methods=["GET", "POST"])
def maintenance():
    refs = load_reference_data()
    if request.method == "POST":
        form = request.form
        try:
            asset_id = int(form["asset_id"])
            schedule_date = form.get("scheduled_date", "")
            status_value = form.get("status", "Scheduled")
            completed_value = form.get("completed_date", "").strip() or (date.today().isoformat() if status_value == "Completed" else None)
            with get_db() as db:
                db.execute("""INSERT INTO maintenance_records(asset_id,performed_by,maintenance_type,scheduled_date,
                              completed_date,cost,status,notes) VALUES (?,?,?,?,?,?,?,?)""",
                           (asset_id, int(form["performed_by"]) if form.get("performed_by") else None,
                            form.get("maintenance_type", "Preventive"), schedule_date, completed_value,
                            float(form.get("cost", "0") or 0), status_value, form.get("notes", "").strip()))
            flash("Maintenance record added.", "success")
            return redirect(url_for("maintenance"))
        except (ValueError, KeyError, sqlite3.IntegrityError) as exc:
            flash(f"Could not save maintenance record: {exc}", "error")
    rows = query_all("""SELECT m.*, a.asset_tag, a.asset_name, u.full_name AS technician_name
                        FROM maintenance_records m JOIN assets a ON a.asset_id=m.asset_id
                        LEFT JOIN support_staff s ON s.staff_id=m.performed_by LEFT JOIN users u ON u.user_id=s.user_id
                        ORDER BY CASE m.status WHEN 'In Progress' THEN 0 WHEN 'Scheduled' THEN 1 ELSE 2 END,
                                 m.scheduled_date ASC""")
    return render_template("maintenance.html", maintenance=rows, refs=refs)


@app.route("/maintenance/<int:maintenance_id>/status", methods=["POST"])
def maintenance_status(maintenance_id: int):
    row = query_one("SELECT * FROM maintenance_records WHERE maintenance_id=?", (maintenance_id,))
    if not row:
        abort(404)
    new_status = request.form.get("status", "")
    if new_status not in ("Scheduled", "In Progress", "Completed", "Cancelled"):
        flash("Choose a valid maintenance status.", "error")
        return redirect(url_for("maintenance"))
    completed_date = date.today().isoformat() if new_status == "Completed" else None
    with get_db() as db:
        db.execute("UPDATE maintenance_records SET status=?, completed_date=COALESCE(?,completed_date) WHERE maintenance_id=?",
                   (new_status, completed_date, maintenance_id))
        if new_status == "Completed":
            db.execute("UPDATE assets SET asset_status='In Use' WHERE asset_id=? AND asset_status='In Repair'", (row["asset_id"],))
    flash("Maintenance status updated.", "success")
    return redirect(url_for("maintenance"))


@app.route("/technicians")
def technicians():
    rows = query_all("""SELECT s.staff_id,s.staff_code,s.specialization,s.shift_name,s.is_available,u.full_name,u.email,
        COUNT(DISTINCT CASE WHEN t.status NOT IN ('Resolved','Closed') THEN t.ticket_id END) AS active_tickets,
        COUNT(DISTINCT CASE WHEN t.status='Resolved' THEN t.ticket_id END) AS resolved_tickets,
        ROUND(AVG(CASE WHEN r.resolved_at IS NOT NULL THEN (julianday(r.resolved_at)-julianday(t.created_at))*24 END),1) AS avg_resolution_hours
        FROM support_staff s JOIN users u ON u.user_id=s.user_id
        LEFT JOIN ticket_assignments a ON a.staff_id=s.staff_id
        LEFT JOIN tickets t ON t.ticket_id=a.ticket_id
        LEFT JOIN resolutions r ON r.ticket_id=t.ticket_id
        GROUP BY s.staff_id ORDER BY active_tickets DESC, u.full_name""")
    return render_template("technicians.html", technicians=rows)


@app.route("/reports")
def reports():
    open_tickets = query_all("""SELECT t.ticket_id,t.ticket_number,t.title,t.status,p.priority_name,t.created_at,
        CAST(julianday('now')-julianday(t.created_at) AS INTEGER) AS age_days,u.full_name AS requester,
        (SELECT su.full_name FROM ticket_assignments a JOIN support_staff ss ON ss.staff_id=a.staff_id
         JOIN users su ON su.user_id=ss.user_id WHERE a.ticket_id=t.ticket_id AND a.unassigned_at IS NULL
         ORDER BY a.assigned_at DESC LIMIT 1) AS assignee
        FROM tickets t JOIN priorities p ON p.priority_id=t.priority_id JOIN users u ON u.user_id=t.requester_id
        WHERE t.status NOT IN ('Resolved','Closed') ORDER BY age_days DESC,t.created_at""")
    response = query_one("""SELECT ROUND(AVG((julianday(first_response.first_assigned)-julianday(t.created_at))*24),2) AS avg_hours,
        MIN((julianday(first_response.first_assigned)-julianday(t.created_at))*24) AS fastest_hours,
        COUNT(first_response.first_assigned) AS responded_count
        FROM tickets t LEFT JOIN (SELECT ticket_id,MIN(assigned_at) AS first_assigned FROM ticket_assignments GROUP BY ticket_id) first_response
        ON first_response.ticket_id=t.ticket_id""")
    tech_load = query_all("""SELECT u.full_name,s.specialization,
        COUNT(DISTINCT CASE WHEN t.status NOT IN ('Resolved','Closed') THEN t.ticket_id END) AS active_tickets,
        COUNT(DISTINCT CASE WHEN t.status='Resolved' THEN t.ticket_id END) AS resolved_tickets
        FROM support_staff s JOIN users u ON u.user_id=s.user_id
        LEFT JOIN ticket_assignments a ON a.staff_id=s.staff_id AND a.unassigned_at IS NULL
        LEFT JOIN tickets t ON t.ticket_id=a.ticket_id GROUP BY s.staff_id ORDER BY active_tickets DESC,u.full_name""")
    asset_history = query_all("""SELECT a.asset_tag,a.asset_name,COUNT(DISTINCT t.ticket_id) AS ticket_count,
        COUNT(DISTINCT m.maintenance_id) AS maintenance_count,MAX(t.created_at) AS last_ticket
        FROM assets a LEFT JOIN tickets t ON t.asset_id=a.asset_id
        LEFT JOIN maintenance_records m ON m.asset_id=a.asset_id
        GROUP BY a.asset_id ORDER BY ticket_count DESC,maintenance_count DESC,a.asset_tag LIMIT 8""")
    warranty_expiry = query_all("""SELECT a.asset_tag,a.asset_name,w.provider,w.warranty_end,
        CAST(julianday(w.warranty_end)-julianday('now') AS INTEGER) AS days_remaining
        FROM warranties w JOIN assets a ON a.asset_id=w.asset_id
        WHERE date(w.warranty_end) <= date('now','+90 day')
        ORDER BY w.warranty_end ASC LIMIT 12""")
    recurring = query_all("""SELECT c.category_name,COUNT(*) AS total,
        SUM(CASE WHEN t.status NOT IN ('Resolved','Closed') THEN 1 ELSE 0 END) AS open_count,
        COUNT(DISTINCT t.asset_id) AS affected_assets
        FROM tickets t JOIN ticket_categories c ON c.ticket_category_id=t.ticket_category_id
        GROUP BY c.ticket_category_id HAVING COUNT(*) >= 2 ORDER BY total DESC""")
    sla = query_one("""SELECT COUNT(*) AS total,
        SUM(CASE WHEN datetime(due_at) < datetime('now') THEN 1 ELSE 0 END) AS overdue
        FROM tickets WHERE status NOT IN ('Resolved','Closed')""")
    return render_template("reports.html", open_tickets=open_tickets, response=response, tech_load=tech_load,
                           asset_history=asset_history, warranty_expiry=warranty_expiry, recurring=recurring, sla=sla)


@app.route("/reports/export.csv")
def export_reports():
    rows = query_all("""SELECT t.ticket_number,t.ticket_type,t.title,t.status,p.priority_name,c.category_name,
        u.full_name AS requester,t.created_at,t.due_at,t.resolved_at FROM tickets t
        JOIN priorities p ON p.priority_id=t.priority_id JOIN ticket_categories c ON c.ticket_category_id=t.ticket_category_id
        JOIN users u ON u.user_id=t.requester_id ORDER BY t.created_at DESC""")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Ticket Number", "Type", "Title", "Status", "Priority", "Category", "Requester", "Created At", "Due At", "Resolved At"])
    for row in rows:
        writer.writerow([row[key] for key in row.keys()])
    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=helpdesk-ticket-report.csv"
    return response


@app.route("/search")
def global_search():
    q = request.args.get("q", "").strip()
    if not q:
        return redirect(url_for("dashboard"))
    pattern = f"%{q}%"
    ticket_rows = query_all("""SELECT ticket_id,ticket_number,title,status FROM tickets
                              WHERE ticket_number LIKE ? OR title LIKE ? OR description LIKE ? ORDER BY created_at DESC LIMIT 10""",
                            (pattern, pattern, pattern))
    asset_rows = query_all("""SELECT asset_id,asset_tag,asset_name,model_number,asset_status FROM assets
                             WHERE asset_tag LIKE ? OR asset_name LIKE ? OR serial_number LIKE ? OR model_number LIKE ? LIMIT 10""",
                           (pattern, pattern, pattern, pattern))
    user_rows = query_all("SELECT user_id,full_name,email,employee_code FROM users WHERE full_name LIKE ? OR email LIKE ? LIMIT 8", (pattern, pattern))
    return render_template("search.html", q=q, tickets=ticket_rows, assets=asset_rows, users=user_rows)


@app.route("/health")
def health():
    count = query_one("SELECT COUNT(*) AS count FROM tickets")["count"]
    return {"status": "ok", "database": "connected", "ticket_records": count}


@app.errorhandler(404)
def not_found(_error: Any):
    return render_template("404.html"), 404


if __name__ == "__main__":
    import sys
    reset = "--reset-db" in sys.argv
    init_db(reset=reset)
    print("\nIT Helpdesk & Asset Support is starting")
    print("Open http://127.0.0.1:5000 in your browser")
    print("Demo data is local and is stored in instance/helpdesk.db\n")
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
