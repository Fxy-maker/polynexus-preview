"""PolyNexus sample management database SQLite backend (v2.0)."""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class SampleDB:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent / "polynexus_samples.db"
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS samples (
                id TEXT PRIMARY KEY, polymer_name TEXT NOT NULL,
                family TEXT, aliases TEXT, tags TEXT, metadata TEXT,
                temp INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                sample_id TEXT NOT NULL REFERENCES samples(id) ON DELETE CASCADE,
                label TEXT NOT NULL, instrument TEXT,
                condition_type TEXT, condition_values TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS data_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
                file_path TEXT NOT NULL, technique TEXT NOT NULL,
                submodule TEXT, file_type TEXT,
                import_order INTEGER DEFAULT 0, file_hash TEXT
            );
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
                technique TEXT NOT NULL, submodule TEXT,
                parameters TEXT, results_summary TEXT, analysis_evidence TEXT, plot_edits TEXT,
                output_dir TEXT, status TEXT DEFAULT 'pending',
                ai_tuned INTEGER DEFAULT 0,
                confirmed INTEGER DEFAULT 0,
                log TEXT, created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS scientific_release_reviews (
                record_id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
                record_json TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        self._ensure_column("analysis_runs", "ai_tuned", "INTEGER DEFAULT 0")
        self._ensure_column("analysis_runs", "confirmed", "INTEGER DEFAULT 0")
        self._ensure_column("analysis_runs", "analysis_evidence", "TEXT")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_batches_sample_id ON batches(sample_id)")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analysis_runs_batch_created_at ON analysis_runs(batch_id, created_at)"
        )
        self._conn.commit()

    def _ensure_column(self, table, column, definition):
        cols = {
            row["name"]
            for row in self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in cols:
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _uid():
        return uuid.uuid4().hex[:8]

    def _auto_detect_family(self, name):
        try:
            from .db_manager import MultiFamilyDB

            entry = MultiFamilyDB().find(name)
            return entry.family if entry else None
        except Exception:
            logger.warning("Failed to auto-detect sample family.", exc_info=True)
            return None

    def create_sample(self, polymer_name, aliases=None, tags=None, metadata=None, temp=False):
        sid = self._uid()
        family = self._auto_detect_family(polymer_name)
        tag_list = list(tags or [])
        if family:
            try:
                family_db = globals().get("MultiFamilyDB")
                entry = family_db().find(polymer_name) if family_db is not None else None
                if hasattr(entry, "tags") and entry.tags:
                    tag_list = list(set(tag_list) | set(entry.tags))
            except Exception:
                logger.warning("Failed to merge family tags for sample creation.", exc_info=True)
        self._conn.execute(
            "INSERT INTO samples (id,polymer_name,family,aliases,tags,metadata,temp) VALUES (?,?,?,?,?,?,?)",
            (
                sid,
                polymer_name,
                family,
                json.dumps(aliases or [], ensure_ascii=False),
                json.dumps(tag_list),
                json.dumps(metadata or {}),
                1 if temp else 0,
            ),
        )
        self._conn.commit()
        return sid

    def get_sample(self, sample_id):
        row = self._conn.execute("SELECT * FROM samples WHERE id=?", (sample_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        for col in ("aliases", "tags", "metadata"):
            try:
                data[col] = json.loads(data[col]) if data[col] else ([] if col != "metadata" else {})
            except Exception:
                data[col] = [] if col != "metadata" else {}
                logger.warning("Failed to decode stored sample JSON.", exc_info=True)
        return data

    def find_sample_by_name(self, polymer_name):
        row = self._conn.execute(
            "SELECT id FROM samples WHERE lower(polymer_name)=lower(?) LIMIT 1",
            (polymer_name.strip(),),
        ).fetchone()
        if not row:
            return None
        return self.get_sample(row["id"])

    def list_samples(self, family=None, search=None, limit=50):
        query = "SELECT * FROM samples WHERE 1=1"
        params = []
        if family:
            query += " AND family=?"
            params.append(family)
        if search:
            query += " AND (polymer_name LIKE ? OR aliases LIKE ? OR tags LIKE ?)"
            needle = f"%{search}%"
            params.extend([needle, needle, needle])
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            data = dict(row)
            for col in ("aliases", "tags", "metadata"):
                try:
                    data[col] = json.loads(data[col]) if data[col] else ([] if col != "metadata" else {})
                except Exception:
                    data[col] = [] if col != "metadata" else {}
                    logger.warning("Failed to decode stored sample JSON.", exc_info=True)
            results.append(data)
        return results

    def update_sample(self, sample_id, **kw):
        allowed = {"polymer_name", "family", "aliases", "tags", "metadata"}
        updates = {}
        for key, value in kw.items():
            if key in allowed:
                if key in ("aliases", "tags", "metadata"):
                    value = json.dumps(value, ensure_ascii=False)
                updates[key] = value
        polymer_name = updates.get("polymer_name")
        if polymer_name and "family" not in updates:
            updates["family"] = self._auto_detect_family(str(polymer_name))
        if not updates:
            return False
        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{key}=?" for key in updates)
        self._conn.execute(
            f"UPDATE samples SET {set_clause} WHERE id=?",
            list(updates.values()) + [sample_id],
        )
        self._conn.commit()
        return True

    def promote_temp(self, sample_id):
        self._conn.execute(
            "UPDATE samples SET temp=0,updated_at=? WHERE id=?",
            (datetime.now().isoformat(), sample_id),
        )
        self._conn.commit()
        return True

    def create_batch(self, sample_id, label, instrument="", condition_type="", condition_values=None):
        bid = self._uid()
        self._conn.execute(
            "INSERT INTO batches (id,sample_id,label,instrument,condition_type,condition_values) VALUES (?,?,?,?,?,?)",
            (bid, sample_id, label, instrument, condition_type, json.dumps(condition_values or {})),
        )
        self._conn.execute(
            "UPDATE samples SET updated_at=? WHERE id=?",
            (datetime.now().isoformat(), sample_id),
        )
        self._conn.commit()
        return bid

    def update_batch(self, batch_id, **kw):
        allowed = {"label", "instrument", "condition_type", "condition_values"}
        updates = {}
        for key, value in kw.items():
            if key in allowed:
                if key == "condition_values":
                    value = json.dumps(value or {}, ensure_ascii=False)
                updates[key] = value
        if not updates:
            return False

        self._conn.execute(
            f"UPDATE batches SET {', '.join(f'{key}=?' for key in updates)} WHERE id=?",
            list(updates.values()) + [batch_id],
        )
        self._touch_batch_sample(batch_id)
        self._conn.commit()
        return True

    def get_batches(self, sample_id):
        rows = self._conn.execute(
            "SELECT * FROM batches WHERE sample_id=? ORDER BY created_at DESC",
            (sample_id,),
        ).fetchall()
        results = []
        for row in rows:
            data = dict(row)
            try:
                data["condition_values"] = json.loads(data["condition_values"]) if data["condition_values"] else {}
            except Exception:
                data["condition_values"] = {}
                logger.warning("Failed to decode stored batch condition values.", exc_info=True)
            results.append(data)
        return results

    def get_batch(self, batch_id):
        row = self._conn.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        try:
            data["condition_values"] = json.loads(data["condition_values"]) if data["condition_values"] else {}
        except Exception:
            data["condition_values"] = {}
            logger.warning("Failed to decode stored batch condition values.", exc_info=True)
        return data

    def find_batch_for_source(self, sample_id, label, technique="", file_path=""):
        label_text = str(label or "").strip().lower()
        technique_text = str(technique or "").strip().lower()
        file_text = str(Path(file_path).expanduser().resolve()) if file_path else ""

        for batch in self.get_batches(sample_id):
            batch_label = str(batch.get("label", "")).strip().lower()
            if batch_label != label_text:
                continue

            data_files = self.get_data_files(batch.get("id", ""))
            if file_text:
                for data_file in data_files:
                    existing_file = str(
                        Path(str(data_file.get("file_path", "")).strip()).expanduser().resolve()
                    )
                    existing_technique = str(data_file.get("technique", "")).strip().lower()
                    if existing_file == file_text and (
                        not technique_text or existing_technique == technique_text
                    ):
                        return batch
                continue

            if technique_text:
                condition_values = batch.get("condition_values")
                if isinstance(condition_values, dict):
                    batch_technique = str(condition_values.get("technique", "")).strip().lower()
                    if batch_technique == technique_text:
                        return batch

        return None

    def find_batch_by_file(self, sample_id, file_path, technique=""):
        file_text = str(Path(file_path).expanduser().resolve()) if file_path else ""
        if not file_text:
            return None

        for batch in self.get_batches(sample_id):
            for data_file in self.get_data_files(batch.get("id", "")):
                existing_file = str(
                    Path(str(data_file.get("file_path", "")).strip()).expanduser().resolve()
                )
                if existing_file != file_text:
                    continue
                return batch

        return None

    def add_data_file(self, batch_id, file_path, technique, submodule="", file_type="", import_order=0):
        cur = self._conn.execute(
            "INSERT INTO data_files (batch_id,file_path,technique,submodule,file_type,import_order) VALUES (?,?,?,?,?,?)",
            (batch_id, file_path, technique, submodule, file_type, import_order),
        )
        self._touch_batch_sample(batch_id)
        self._conn.commit()
        return cur.lastrowid

    def update_data_file(self, file_id, **kw):
        allowed = {"file_path", "technique", "submodule", "file_type", "import_order", "file_hash"}
        updates = {key: value for key, value in kw.items() if key in allowed}
        if not updates:
            return False

        row = self._conn.execute(
            "SELECT batch_id FROM data_files WHERE id=?",
            (file_id,),
        ).fetchone()
        if not row:
            return False
        batch_id = row["batch_id"]

        self._conn.execute(
            f"UPDATE data_files SET {', '.join(f'{key}=?' for key in updates)} WHERE id=?",
            list(updates.values()) + [file_id],
        )
        self._touch_batch_sample(batch_id)
        self._conn.commit()
        return True

    def remove_data_file(self, file_id):
        row = self._conn.execute(
            "SELECT batch_id FROM data_files WHERE id=?",
            (file_id,),
        ).fetchone()
        if not row:
            return False
        batch_id = row["batch_id"]
        self._conn.execute("DELETE FROM data_files WHERE id=?", (file_id,))
        self._reindex_batch_files(batch_id)
        self._touch_batch_sample(batch_id)
        self._conn.commit()
        return True

    def get_data_files(self, batch_id):
        return [
            dict(row)
            for row in self._conn.execute(
                "SELECT * FROM data_files WHERE batch_id=? ORDER BY import_order",
                (batch_id,),
            ).fetchall()
        ]

    def create_analysis_run(
        self,
        batch_id,
        technique,
        submodule="",
        parameters=None,
        results_summary=None,
        analysis_evidence=None,
        output_dir="",
        ai_tuned=False,
        confirmed=False,
    ):
        rid = self._uid()
        self._conn.execute(
            "INSERT INTO analysis_runs (id,batch_id,technique,submodule,parameters,results_summary,analysis_evidence,output_dir,status,ai_tuned,confirmed) VALUES (?,?,?,?,?,?,?,?,'completed',?,?)",
            (
                rid,
                batch_id,
                technique,
                submodule,
                json.dumps(parameters or {}, ensure_ascii=False),
                json.dumps(results_summary or {}, ensure_ascii=False),
                json.dumps(analysis_evidence or {}, ensure_ascii=False),
                output_dir,
                1 if ai_tuned else 0,
                1 if confirmed else 0,
            ),
        )
        self._conn.commit()
        return rid

    def get_analysis_runs(self, batch_id):
        rows = self._conn.execute(
            "SELECT * FROM analysis_runs WHERE batch_id=? ORDER BY created_at DESC",
            (batch_id,),
        ).fetchall()
        results = []
        for row in rows:
            data = dict(row)
            for col in ("parameters", "results_summary", "analysis_evidence", "plot_edits"):
                try:
                    data[col] = json.loads(data[col]) if data[col] else {}
                except Exception:
                    data[col] = {}
                    logger.warning("Failed to decode stored analysis run JSON.", exc_info=True)
            release = self.get_latest_scientific_release_review_for_run(data.get("id"))
            if release is not None:
                data["scientific_release"] = release
            results.append(data)
        return results

    def list_analysis_run_headers(self, *, limit: int = 500) -> list[dict]:
        """Return recent analysis-run fields needed to populate History."""
        rows = self._conn.execute(
            "SELECT id,batch_id,technique,submodule,output_dir,status,ai_tuned,confirmed,created_at "
            "FROM analysis_runs ORDER BY created_at DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_analysis_run_headers_for_batch(self, batch_id, *, limit: int = 500) -> list[dict]:
        """Return recent header fields for one batch without decoding JSON payloads."""
        rows = self._conn.execute(
            "SELECT id,batch_id,technique,submodule,output_dir,status,ai_tuned,confirmed,created_at "
            "FROM analysis_runs WHERE batch_id=? ORDER BY created_at DESC LIMIT ?",
            (batch_id, max(1, int(limit))),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_analysis_run(self, run_id):
        row = self._conn.execute(
            "SELECT * FROM analysis_runs WHERE id=?",
            (run_id,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        for col in ("parameters", "results_summary", "analysis_evidence", "plot_edits"):
            try:
                data[col] = json.loads(data[col]) if data[col] else {}
            except Exception:
                data[col] = {}
                logger.warning("Failed to decode stored analysis run JSON.", exc_info=True)
        release = self.get_latest_scientific_release_review_for_run(data.get("id"))
        if release is not None:
            data["scientific_release"] = release
        return data

    def update_plot_edits(self, run_id, plot_edits_json):
        self._conn.execute("UPDATE analysis_runs SET plot_edits=? WHERE id=?", (plot_edits_json, run_id))
        self._conn.commit()
        return True

    def update_analysis_status(self, run_id, status, log_msg=None):
        updates = {"status": status}
        if log_msg is not None:
            updates["log"] = log_msg
        set_clause = ", ".join(f"{key}=?" for key in updates)
        self._conn.execute(
            f"UPDATE analysis_runs SET {set_clause} WHERE id=?",
            list(updates.values()) + [run_id],
        )
        self._conn.commit()
        return True

    def update_analysis_parameters(self, run_id, parameters):
        """Replace only one run's persisted parameters JSON."""

        row = self._conn.execute(
            "SELECT id FROM analysis_runs WHERE id=?",
            (run_id,),
        ).fetchone()
        if not row:
            return False
        if not isinstance(parameters, dict):
            raise ValueError("analysis parameters must be a mapping")
        parameters_json = json.dumps(parameters, ensure_ascii=False, allow_nan=False)
        self._conn.execute(
            "UPDATE analysis_runs SET parameters=? WHERE id=?",
            (parameters_json, run_id),
        )
        self._conn.commit()
        return True

    def update_analysis_confirmation(self, run_id, confirmed=True):
        row = self._conn.execute(
            "SELECT results_summary FROM analysis_runs WHERE id=?",
            (run_id,),
        ).fetchone()
        if not row:
            return False

        summary = {}
        try:
            summary = json.loads(row["results_summary"]) if row["results_summary"] else {}
        except Exception:
            logger.warning("Failed to decode stored analysis run summary while updating confirmation.", exc_info=True)
            summary = {}
        if not isinstance(summary, dict):
            summary = {}

        summary["confirmed"] = bool(confirmed)
        self._conn.execute(
            "UPDATE analysis_runs SET confirmed=?, results_summary=? WHERE id=?",
            (1 if confirmed else 0, json.dumps(summary, ensure_ascii=False), run_id),
        )
        self._conn.commit()
        return True

    def update_analysis_scientific_review(self, run_id, record_payload, decision_snapshot):
        """Attach one JSON-safe scientific review to exactly one analysis run."""

        if not isinstance(record_payload, dict) or not isinstance(decision_snapshot, dict):
            raise ValueError("scientific review payloads must be mappings")

        record_json = json.dumps(record_payload, ensure_ascii=False, allow_nan=False)
        snapshot_json = json.dumps(decision_snapshot, ensure_ascii=False, allow_nan=False)
        row = self._conn.execute(
            "SELECT analysis_evidence, results_summary FROM analysis_runs WHERE id=?",
            (run_id,),
        ).fetchone()
        if not row:
            return False

        try:
            evidence = json.loads(row["analysis_evidence"]) if row["analysis_evidence"] else {}
            summary = json.loads(row["results_summary"]) if row["results_summary"] else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("Failed to decode analysis run while attaching scientific review.")
            return False
        if not isinstance(evidence, dict):
            evidence = {}
        if not isinstance(summary, dict):
            summary = {}

        evidence["scientific_review_record"] = json.loads(record_json)
        evidence["scientific_review"] = json.loads(snapshot_json)
        result = summary.get("result")
        if not isinstance(result, dict):
            result = {}
        metadata = result.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["scientific_review"] = json.loads(record_json)
        metadata["scientific_review_decision"] = json.loads(snapshot_json)
        result["metadata"] = metadata
        summary["result"] = result
        summary["scientific_review"] = json.loads(snapshot_json)

        with self._conn:
            self._conn.execute(
                "UPDATE analysis_runs SET analysis_evidence=?, results_summary=? WHERE id=?",
                (
                    json.dumps(evidence, ensure_ascii=False, allow_nan=False),
                    json.dumps(summary, ensure_ascii=False, allow_nan=False),
                    run_id,
                ),
            )
        return True

    def save_scientific_release_review(self, batch_id, record_payload, decision_snapshot):
        """Append one validated project-level release record to a batch."""

        if not isinstance(record_payload, dict) or not isinstance(decision_snapshot, dict):
            raise ValueError("scientific release payloads must be mappings")
        from ..core.scientific_review import (
            review_decision_snapshot,
            review_record_from_payload,
            validate_review_record,
        )

        record = review_record_from_payload(record_payload)
        if record is None:
            raise ValueError("scientific release record is invalid")
        validate_review_record(record)
        if record.scope != "release":
            raise ValueError("scientific release record must use release scope")
        canonical_source = record.source_refs[0] if record.source_refs else ""
        expected_snapshot = review_decision_snapshot(
            record,
            expected_scope="release",
            source_ref=canonical_source,
        )
        if decision_snapshot != expected_snapshot:
            raise ValueError("scientific release snapshot does not match record")

        batch_key = str(batch_id or "").strip()
        row = self._conn.execute("SELECT id FROM batches WHERE id=?", (batch_key,)).fetchone()
        if not row:
            return False
        record_json = json.dumps(record.to_dict(), ensure_ascii=False, allow_nan=False)
        snapshot_json = json.dumps(expected_snapshot, ensure_ascii=False, allow_nan=False)
        with self._conn:
            self._conn.execute(
                "INSERT INTO scientific_release_reviews (record_id,batch_id,record_json,snapshot_json) VALUES (?,?,?,?)",
                (record.record_id, batch_key, record_json, snapshot_json),
            )
        return True

    @staticmethod
    def _decode_scientific_release_row(row):
        if not row:
            return None
        try:
            return {
                "record": json.loads(row["record_json"]),
                "snapshot": json.loads(row["snapshot_json"]),
                "created_at": str(row["created_at"] or ""),
            }
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("Failed to decode stored scientific release review.")
            return None

    def list_scientific_release_reviews(self, batch_id):
        """Return all batch release records in append order."""

        rows = self._conn.execute(
            "SELECT record_json,snapshot_json,created_at FROM scientific_release_reviews WHERE batch_id=? ORDER BY rowid",
            (str(batch_id or "").strip(),),
        ).fetchall()
        return [decoded for row in rows if (decoded := self._decode_scientific_release_row(row)) is not None]

    def get_latest_scientific_release_review_for_run(self, run_id):
        """Return the newest release projection for an analysis run."""

        row = self._conn.execute(
            """
            SELECT review.record_json,review.snapshot_json,review.created_at
            FROM scientific_release_reviews AS review
            JOIN analysis_runs AS run ON run.batch_id=review.batch_id
            WHERE run.id=?
            ORDER BY review.rowid DESC
            LIMIT 1
            """,
            (str(run_id or "").strip(),),
        ).fetchone()
        return self._decode_scientific_release_row(row)

    def cleanup_temp(self, days=30):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cur = self._conn.execute("DELETE FROM samples WHERE temp=1 AND created_at < ?", (cutoff,))
        self._conn.commit()
        return cur.rowcount

    def resolve_file_path(self, relative_path, data_roots=None):
        if os.path.isabs(relative_path) and os.path.exists(relative_path):
            return relative_path
        for root in reversed(data_roots or []):
            candidate = os.path.join(root, relative_path)
            if os.path.exists(candidate):
                return candidate
        return relative_path

    def _touch_batch_sample(self, batch_id):
        self._conn.execute(
            """
            UPDATE samples
            SET updated_at=?
            WHERE id=(
                SELECT sample_id FROM batches WHERE id=?
            )
            """,
            (datetime.now().isoformat(), batch_id),
        )

    def _reindex_batch_files(self, batch_id):
        rows = self._conn.execute(
            "SELECT id FROM data_files WHERE batch_id=? ORDER BY import_order, id",
            (batch_id,),
        ).fetchall()
        for index, row in enumerate(rows):
            self._conn.execute(
                "UPDATE data_files SET import_order=? WHERE id=?",
                (index, row["id"]),
            )

    def close(self):
        self._conn.close()
