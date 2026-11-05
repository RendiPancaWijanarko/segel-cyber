"""
SEGEL Core - Security-critical verification library.

This is the trusted core (Zone Z2) that implements all cryptographic
and verification logic. It has no network imports, no I/O beyond
what callers provide, and minimal dependencies.

Design principles:
- Fail closed: any error is a rejection with a reason
- Standards before invention: Ed25519, DSSE, in-toto, SHA-256, RFC 6962
- Deterministic: same inputs always produce the same result
- No wall-clock time dependency for security decisions
"""

__version__ = "0.1.0"

