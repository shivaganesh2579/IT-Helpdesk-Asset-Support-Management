# Review presentations — Project 39

Three phase-specific PowerPoint decks are included:

1. `Phase_1_Problem_Scope_ERD.pptx` — Review 1: problem, objectives, scope, user roles, functional requirements, conceptual ER model and initial relational-schema groups.
2. `Phase_2_3NF_SQL_Queries.pptx` — Review 2: actual SQLite schema, relation groups, functional dependencies, 1NF–3NF rationale, integrity constraints and representative SQL reports.
3. `Phase_3_Application_Demo.pptx` — Final review: application architecture, captured prototype screens, ticket lifecycle, assets, maintenance, analytics, CSV export, observed manual evidence, tests included and future scope.

The current prototype is Flask + SQLite. `sql/mysql_schema.sql` is a MySQL 8 reference/migration artefact; the running app is SQLite-backed. Demo names and records are synthetic. Automated tests are included in `tests/test_app.py`; run `python -m unittest discover -s tests -v` and record the actual outcome before final submission.
