-- Representative SQL queries for Review 2 / report appendix.
-- These queries use the implemented SQLite schema and SQLite date functions.

-- 1. Open ticket queue and ageing (joins, calculated field, ordering)
SELECT t.ticket_number, t.title, t.status, p.priority_name, u.full_name AS requester,
       CAST(julianday('now') - julianday(t.created_at) AS INTEGER) AS age_days
FROM tickets t
JOIN users u ON u.user_id = t.requester_id
JOIN priorities p ON p.priority_id = t.priority_id
WHERE t.status NOT IN ('Resolved', 'Closed')
ORDER BY age_days DESC, p.sort_order;

-- 2. Average time from ticket creation to first assignment
SELECT ROUND(AVG((julianday(first_assignment.first_assigned) - julianday(t.created_at)) * 24), 2)
       AS avg_first_assignment_hours
FROM tickets t
LEFT JOIN (
    SELECT ticket_id, MIN(assigned_at) AS first_assigned
    FROM ticket_assignments GROUP BY ticket_id
) first_assignment ON first_assignment.ticket_id = t.ticket_id;

-- 3. Technician active workload
SELECT u.full_name, s.specialization,
       COUNT(DISTINCT CASE WHEN t.status NOT IN ('Resolved', 'Closed') THEN t.ticket_id END) AS active_tickets,
       COUNT(DISTINCT CASE WHEN t.status = 'Resolved' THEN t.ticket_id END) AS resolved_tickets
FROM support_staff s
JOIN users u ON u.user_id = s.user_id
LEFT JOIN ticket_assignments a ON a.staff_id = s.staff_id AND a.unassigned_at IS NULL
LEFT JOIN tickets t ON t.ticket_id = a.ticket_id
GROUP BY s.staff_id, u.full_name, s.specialization
ORDER BY active_tickets DESC;

-- 4. Asset ticket and maintenance history summary
SELECT a.asset_tag, a.asset_name,
       COUNT(DISTINCT t.ticket_id) AS ticket_count,
       COUNT(DISTINCT m.maintenance_id) AS maintenance_count,
       MAX(t.created_at) AS last_ticket_at
FROM assets a
LEFT JOIN tickets t ON t.asset_id = a.asset_id
LEFT JOIN maintenance_records m ON m.asset_id = a.asset_id
GROUP BY a.asset_id, a.asset_tag, a.asset_name
ORDER BY ticket_count DESC, maintenance_count DESC;

-- 5. Warranty expiry within the next 90 days (expired warranties are also retained for visibility)
SELECT a.asset_tag, a.asset_name, w.provider, w.warranty_end,
       CAST(julianday(w.warranty_end) - julianday('now') AS INTEGER) AS days_remaining
FROM warranties w
JOIN assets a ON a.asset_id = w.asset_id
WHERE date(w.warranty_end) <= date('now', '+90 day')
ORDER BY w.warranty_end;

-- 6. Recurring issue categories
SELECT c.category_name, COUNT(*) AS ticket_count,
       SUM(CASE WHEN t.status NOT IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS open_count,
       COUNT(DISTINCT t.asset_id) AS affected_assets
FROM tickets t
JOIN ticket_categories c ON c.ticket_category_id = t.ticket_category_id
GROUP BY c.ticket_category_id, c.category_name
HAVING COUNT(*) >= 2
ORDER BY ticket_count DESC;

-- 7. SLA breaches among unresolved tickets
SELECT t.ticket_number, t.title, p.priority_name, t.due_at
FROM tickets t
JOIN priorities p ON p.priority_id = t.priority_id
WHERE t.status NOT IN ('Resolved', 'Closed')
  AND t.due_at IS NOT NULL
  AND datetime(t.due_at) < datetime('now')
ORDER BY t.due_at;

-- 8. Status history for an individual ticket
SELECT h.old_status, h.new_status, h.changed_at, u.full_name AS changed_by, h.note
FROM ticket_status_history h
JOIN users u ON u.user_id = h.changed_by
WHERE h.ticket_id = ?
ORDER BY h.changed_at, h.history_id;

-- 9. Warranty expiry by department
SELECT d.department_name, COUNT(*) AS warranty_records,
       SUM(CASE WHEN date(w.warranty_end) < date('now') THEN 1 ELSE 0 END) AS expired_records,
       SUM(CASE WHEN date(w.warranty_end) BETWEEN date('now') AND date('now', '+30 day') THEN 1 ELSE 0 END) AS expiring_soon
FROM warranties w
JOIN assets a ON a.asset_id = w.asset_id
JOIN departments d ON d.department_id = a.department_id
GROUP BY d.department_id, d.department_name
ORDER BY expiring_soon DESC, expired_records DESC;
