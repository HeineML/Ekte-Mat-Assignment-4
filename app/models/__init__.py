"""Model layer: domain entities, repository interfaces, domain rules and storage.

Controllers and views import only from this package, never from the storage
implementation, so SQLite can later be replaced by Neo4j. Filled in phase 2.
"""
