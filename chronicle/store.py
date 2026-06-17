"""
chronicle/store.py — the persistence seam, so adopters don't write glue to wire a ledger into their stack.

A chronicle ledger is an APPEND-ONLY sequence of receipts. That maps cleanly onto append-only stores
people already run: a file, an object store with versioning/object-lock (S3), an append-only table
(Postgres), or a log (Kafka). Rather than ship fake integrations, we ship ONE real, dependency-free
implementation (JSONL file) behind a tiny ABC, plus documented adapter sketches so a corporate team
writes ~15 lines, not a framework.

Contract (4 methods):

    append(receipt) -> None        # durably add one receipt at the tail
    __iter__()      -> receipts    # yield receipts in commit order (for court.verify_chain)
    head()          -> str         # committed_hash of the last receipt, or core.GENESIS if empty
    seq()           -> int         # next sequence number (== count of receipts)

The store NEVER validates — that is the court's job. A store that silently drops or reorders is caught
by verify_chain (the prev-hash/seq checks), which is the whole point: trust is in the math, not the DB.
"""
import json
import os
import core


class LedgerStore:
    """Abstract append-only receipt store."""
    def append(self, receipt): raise NotImplementedError
    def __iter__(self):        raise NotImplementedError
    def head(self):            raise NotImplementedError
    def seq(self):             raise NotImplementedError

    def to_list(self):
        return list(self)


class MemoryStore(LedgerStore):
    """In-process list. For tests and embedding."""
    def __init__(self, receipts=None):
        self._r = list(receipts or [])

    def append(self, receipt):
        self._r.append(receipt)

    def __iter__(self):
        return iter(self._r)

    def head(self):
        return self._r[-1]["committed_hash"] if self._r else core.GENESIS

    def seq(self):
        return len(self._r)


class JsonlStore(LedgerStore):
    """Append-only newline-delimited JSON file. One receipt per line; the file is opened in append mode
    and fsync'd, so a crash can lose only the in-flight tail line, never rewrite history. This is the
    reference durable backend and needs no dependencies."""

    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            open(path, "a").close()

    def append(self, receipt):
        line = json.dumps(receipt, separators=(",", ":"), sort_keys=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    def __iter__(self):
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def head(self):
        last = None
        for r in self:
            last = r
        return last["committed_hash"] if last else core.GENESIS

    def seq(self):
        return sum(1 for _ in self)


# --------------------------------------------------------------------------------------------------
# ADAPTER SKETCHES (not imported; documented so a team can wire their own in ~15 lines).
#
# S3 with Object Lock (WORM compliance — the natural fit for an immutable audit log):
#
#   class S3Store(LedgerStore):
#       def __init__(self, bucket, prefix, s3=None):
#           self.s3 = s3 or boto3.client("s3"); self.bucket = bucket; self.prefix = prefix
#       def append(self, receipt):
#           key = f"{self.prefix}/{receipt['frame']['seq']:012d}.json"
#           self.s3.put_object(Bucket=self.bucket, Key=key,            # bucket has Object Lock = WORM
#                              Body=json.dumps(receipt).encode())       # so even an admin cannot rewrite
#       def __iter__(self):
#           pages = self.s3.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=self.prefix)
#           for p in pages:
#               for o in sorted(p.get("Contents", []), key=lambda x: x["Key"]):
#                   yield json.loads(self.s3.get_object(Bucket=self.bucket, Key=o["Key"])["Body"].read())
#
# Postgres (append-only table; let the DB enforce ordering, let the court enforce integrity):
#
#   CREATE TABLE chronicle_ledger (seq BIGINT PRIMARY KEY, receipt JSONB NOT NULL);
#   -- REVOKE UPDATE, DELETE so the table is insert-only at the role level.
#   class PgStore(LedgerStore):
#       def append(self, r): self.cur.execute(
#           "INSERT INTO chronicle_ledger(seq, receipt) VALUES (%s, %s)",
#           (r["frame"]["seq"], json.dumps(r)))
#       def __iter__(self):
#           self.cur.execute("SELECT receipt FROM chronicle_ledger ORDER BY seq")
#           for (row,) in self.cur: yield row
#
# Kafka (the ledger IS the topic; partition by session so order is preserved per stream):
#
#   class KafkaStore(LedgerStore):
#       def append(self, r): self.producer.produce(self.topic, key=self.session,
#                                                   value=json.dumps(r)); self.producer.flush()
#       # __iter__: consume the topic from offset 0 to current high-water mark.
#
# In every case the store only moves bytes; correctness is re-derived by court.verify_chain. That is the
# adoption story: any append-only store you already operate becomes a verifiable decision log.
