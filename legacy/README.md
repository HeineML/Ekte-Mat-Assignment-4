# Legacy: SQLite storage from Oblig 4

This folder holds the SQLite implementation of the repository interfaces that Ekte Mat Online used in
Oblig 4 (tag `v1.0`). It is kept for reference and for the comparison in the Oblig 5 report.

**It is not used.** The app stores all data in Neo4j (`app/models/neo4j/`), nothing in `app/` or
`tests/` imports this folder, and its imports (`app.models.sqlite...`) no longer resolve because the
package was moved here. To run the Oblig 4 version, check out the `v1.0` tag.

- `schema.sql`: the relational tables
- `db.py`: one SQLite connection per request
- `repositories.py`: the SQLite repositories
