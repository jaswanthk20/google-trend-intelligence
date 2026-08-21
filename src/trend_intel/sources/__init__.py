"""Network I/O only.

Modules here call external APIs and return raw payloads. They must not
reshape data (that is transform/) and must not write files (that is
storage.py). Keeping the boundary strict is what makes the rest of the
package testable without a network connection.
"""
