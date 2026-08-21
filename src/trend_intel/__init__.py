"""Live search-demand vs content-supply intelligence.

Collects Google Trends search interest and YouTube video performance for a
shared basket of topics, so the two can be compared on the same grain.

Layering rule enforced throughout this package:

    sources/     network in, raw payload out.   Does I/O. Never reshapes.
    transform/   payload in, DataFrame out.     Pure. Never does I/O.
    storage.py   DataFrame in, file out.        Does I/O. Never reshapes.
    pipeline.py  wires the three together.

Keeping transform/ pure is what lets Phase 2 import it unchanged inside a
Cloud Function, and what lets tests run without a network connection.
"""

__version__ = "0.1.0"
