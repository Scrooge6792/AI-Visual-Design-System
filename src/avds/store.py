from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path

from .errors import AVDSError
from .jsonschema import validate as validate_schema
from .platform import readonly, visual_capability, os_build, sync_directory
from .util import FACETS, canonical_json, digest_json, file_sha256, inspect_image, new_id, now, safe_relative


class TransactionConnection(sqlite3.Connection):
    """sqlite's autocommit mode needs an explicit BEGIN for `with db`."""
    def __enter__(self):
        self.execute("BEGIN IMMEDIATE")
        return self


class Store:
    def __init__(self, vault: Path, visual_provider: str = "auto"):
        self.vault = vault.resolve()
        self.data = self.vault / "data"
        self.staging = self.vault / "staging"
        self.objects = self.vault / "objects" / "sha256"
        self.cache = self.vault / "cache"
        for path in (self.data, self.staging, self.objects, self.cache):
            path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data / "visual-assets.sqlite3"
        self.db = sqlite3.connect(self.db_path, timeout=5, isolation_level=None, check_same_thread=False, factory=TransactionConnection)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA journal_mode=DELETE")
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        self.db.executescript(schema)
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('schema_version','1')")
        default_helper = Path(__file__).resolve().parents[2] / "bin" / "avds-vision"
        workspace_helper = Path(__file__).resolve().parents[2] / ".build" / "avds-vision"
        self.vision_helper = Path(os.environ.get("AVDS_VISION_HELPER", default_helper if default_helper.exists() else workspace_helper))
        self.visual_provider = visual_provider

    def close(self):
        self.db.close()

    def _one(self, sql, params=()):
        return self.db.execute(sql, params).fetchone()

    def _operation(self, operation_id: str, request: dict, work):
        if not operation_id:
            raise AVDSError("VALIDATION_FAILED", "缺少 operation_id")
        request_hash = digest_json(request)
        existing = self._one("SELECT request_hash,state,result_json FROM operations WHERE operation_id=?", (operation_id,))
        if existing:
            if existing["request_hash"] != request_hash:
                raise AVDSError("IDEMPOTENCY_CONFLICT", "相同 operation_id 对应不同请求")
            if existing["state"] == "committed":
                return json.loads(existing["result_json"])
            raise AVDSError("RECOVERY_REQUIRED", "操作尚未完成，需要恢复")
        stamp = now()
        self.db.execute("INSERT INTO operations VALUES(?,?, 'pending',NULL,?,?)", (operation_id, request_hash, stamp, stamp))
        try:
            result = work()
            self.db.execute("UPDATE operations SET state='committed',result_json=?,updated_at=? WHERE operation_id=?",
                            (json.dumps(result, ensure_ascii=False), now(), operation_id))
            return result
        except Exception:
            self.db.execute("UPDATE operations SET state='failed',updated_at=? WHERE operation_id=?", (now(), operation_id))
            raise

    def stage(self, req: dict):
        operation_id = req.get("operation_id")
        raw_source = Path(req.get("source_path", "")).expanduser()
        if raw_source.is_symlink():
            raise AVDSError("ACCESS_DENIED", "不允许通过符号链接导入")
        source = raw_source.resolve()
        batch_id = req.get("batch_id") or new_id("batch")

        def work():
            try:
                info = inspect_image(source)
            except (ValueError, OSError) as exc:
                raise AVDSError("UNSUPPORTED_FORMAT", str(exc)) from exc
            file_hash = file_sha256(source)
            digest = file_hash.split(":", 1)[1]
            suffix = {"png": ".png", "jpeg": ".jpg", "heic": ".heic", "webp": ".webp"}[info["format"]]
            relative = f"staging/{digest}{suffix}"
            target = safe_relative(self.vault, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                temporary = target.with_suffix(target.suffix + ".partial")
                with source.open("rb") as input_stream, temporary.open("xb") as output_stream:
                    shutil.copyfileobj(input_stream, output_stream, 1024 * 1024)
                    output_stream.flush()
                    os.fsync(output_stream.fileno())
                if file_sha256(temporary) != file_hash:
                    temporary.unlink(missing_ok=True)
                    raise AVDSError("HASH_MISMATCH", "暂存复制后的哈希不一致")
                os.replace(temporary, target)
            stamp = now()
            asset_id, queue_id, source_id = new_id("asset"), new_id("queue"), new_id("source")
            with self.db:
                self.db.execute("INSERT OR IGNORE INTO import_batches VALUES(?,?)", (batch_id, stamp))
                self.db.execute("INSERT OR IGNORE INTO files VALUES(?,?,?,?,?,?,?,?)",
                                (file_hash, relative, info["format"], info["mime_type"], info["size"], info["width"], info["height"], stamp))
                self.db.execute("INSERT INTO assets VALUES(?,?, 'staged',0,NULL,NULL,NULL,?,?)", (asset_id, file_hash, stamp, stamp))
                src = req.get("source") or {}
                self.db.execute("INSERT INTO asset_sources VALUES(?,?,?,?,?,?,?,?,?,?)", (
                    source_id, asset_id, src.get("original_name") or source.name, src.get("origin"), src.get("url"),
                    src.get("author"), src.get("copyright"), src.get("license"), src.get("user_note"), stamp))
                position = self._one("SELECT COALESCE(MAX(position),0)+1 AS n FROM review_queue_items WHERE batch_id=?", (batch_id,))["n"]
                self.db.execute("INSERT INTO review_queue_items VALUES(?,?,?,?,'pending',?,?)",
                                (queue_id, batch_id, asset_id, position, stamp, stamp))
            return {"queue_item_id": queue_id, "asset_id": asset_id, "batch_id": batch_id,
                    "file_hash": file_hash, **info}
        return self._operation(operation_id, req, work)

    def queue_get(self, queue_id: str):
        row = self._one("""SELECT q.*,a.file_hash,f.format,f.mime_type,f.width,f.height,f.byte_size,
          s.original_name,s.origin,s.user_note FROM review_queue_items q JOIN assets a USING(asset_id)
          JOIN files f USING(file_hash) LEFT JOIN asset_sources s USING(asset_id) WHERE q.queue_item_id=?""", (queue_id,))
        if not row:
            raise AVDSError("NOT_FOUND", "待审项不存在")
        result = dict(row)
        result["unreviewed"] = True
        return result

    def queue_preview(self, queue_id: str):
        item = self.queue_get(queue_id)
        file_row = self._one("SELECT relative_path FROM files WHERE file_hash=?", (item["file_hash"],))
        path = safe_relative(self.vault, file_row["relative_path"])
        if not path.exists():
            raise AVDSError("FILE_MISSING", "待审原图缺失")
        if file_sha256(path) != item["file_hash"]:
            raise AVDSError("HASH_MISMATCH", "待审原图指纹异常")
        return {"queue_item_id": queue_id, "batch_id": item["batch_id"], "queue_state": item["state"],
                "file_hash": item["file_hash"], "content_path": str(path), "access": "read-only",
                "mime_type": item["mime_type"], "unreviewed": True}

    def defer(self, req: dict, remaining=False):
        operation_id = req.get("operation_id")
        def work():
            stamp = now()
            if remaining:
                batch_id = req.get("batch_id")
                rows = self.db.execute("SELECT queue_item_id FROM review_queue_items WHERE batch_id=? AND state IN ('pending','in_review') ORDER BY position", (batch_id,)).fetchall()
                with self.db:
                    self.db.execute("UPDATE review_queue_items SET state='deferred',updated_at=? WHERE batch_id=? AND state IN ('pending','in_review')", (stamp, batch_id))
                return {"batch_id": batch_id, "deferred": [r[0] for r in rows]}
            queue_id = req.get("queue_item_id")
            changed = self.db.execute("UPDATE review_queue_items SET state='deferred',updated_at=? WHERE queue_item_id=? AND state IN ('pending','in_review','deferred')", (stamp, queue_id)).rowcount
            if not changed:
                raise AVDSError("NOT_FOUND", "待审项不存在或已经解决")
            return {"queue_item_id": queue_id, "state": "deferred"}
        return self._operation(operation_id, req, work)

    def pending(self, req: dict):
        clauses, params = ["q.state IN ('pending','in_review','deferred')"], []
        if req.get("batch_id"):
            clauses.append("q.batch_id=?"); params.append(req["batch_id"])
        if req.get("status"):
            marks = ",".join("?" for _ in req["status"]); clauses.append(f"q.state IN ({marks})"); params.extend(req["status"])
        limit = min(max(int(req.get("limit", 30)), 1), 100)
        rows = self.db.execute(f"""SELECT q.queue_item_id,q.batch_id,q.state,q.created_at,a.file_hash,
          s.original_name,s.origin,s.user_note,f.format,f.width,f.height FROM review_queue_items q
          JOIN assets a USING(asset_id) JOIN files f USING(file_hash) LEFT JOIN asset_sources s USING(asset_id)
          WHERE {' AND '.join(clauses)} ORDER BY q.created_at LIMIT ?""", (*params, limit)).fetchall()
        result = {"scope": "pending", "items": [dict(r) for r in rows]}
        if req.get("include_stats"):
            result["total_pending"] = self._one("SELECT count(*) AS n FROM review_queue_items WHERE state IN ('pending','in_review','deferred')")["n"]
            result["oldest_pending_at"] = self._one("SELECT min(created_at) AS value FROM review_queue_items WHERE state IN ('pending','in_review','deferred')")["value"]
            result["counts_by_batch"] = {r["batch_id"]: r["n"] for r in self.db.execute(
                "SELECT batch_id,count(*) AS n FROM review_queue_items WHERE state IN ('pending','in_review','deferred') GROUP BY batch_id")}
        return result

    def record_analysis(self, req: dict):
        operation_id = req.get("operation_id")
        def work():
            analysis_id = new_id("analysis")
            body = req.get("body") or {}
            self.db.execute("INSERT INTO analysis_runs VALUES(?,?,?,?,?,?,?,?)", (
                analysis_id, req.get("queue_item_id"), req.get("asset_id"), req.get("model", "Codex account vision"),
                req.get("prompt_version", "v1"), req.get("execution_location", "Codex Desktop"),
                json.dumps(body, ensure_ascii=False), now()))
            return {"analysis_run_id": analysis_id}
        return self._operation(operation_id, req, work)

    def create_proposal(self, req: dict):
        operation_id = req.get("operation_id")
        def work():
            operation = req.get("operation")
            if operation not in {"asset.create", "asset.update", "asset.archive", "concept.create",
                                 "knowledge.create", "knowledge.update", "knowledge.archive",
                                 "prompt.create", "prompt.update", "prompt.archive"}:
                raise AVDSError("OPERATION_NOT_SUPPORTED", "V1 不支持该操作")
            with self.db:
                if operation == "concept.create":
                    return self._create_concept_proposal(req)
                if operation.startswith("knowledge.") or operation.startswith("prompt."):
                    return self._create_content_proposal(req)
                return self._create_asset_proposal(req)
        return self._operation(operation_id, req, work)

    def _create_asset_proposal(self, req):
        operation, changes = req["operation"], req.get("changes") or {}
        concept_ids = req.get("concept_ids", [])
        candidate_refs = req.get("candidate_concept_refs", [])
        if operation == "asset.create":
            target_id, target_revision = req.get("queue_item_id"), 0
            if not target_id or req.get("asset_id") or not changes.get("title"):
                raise AVDSError("VALIDATION_FAILED", "asset.create 目标或标题不合法")
            item = self.queue_get(target_id)
            file_hash = item["file_hash"]
        else:
            target_id, target_revision = req.get("asset_id"), int(req.get("target_revision", 0))
            if not target_id or req.get("queue_item_id") or target_revision < 1:
                raise AVDSError("VALIDATION_FAILED", "update/archive 目标不合法")
            asset = self._one("SELECT * FROM assets WHERE asset_id=? AND state='active'", (target_id,))
            if not asset:
                raise AVDSError("NOT_FOUND", "正式资产不存在或不是 active")
            file_hash = asset["file_hash"]
            if asset["revision"] != target_revision:
                raise AVDSError("TARGET_REVISION_CONFLICT", "目标修订已变化")
            if operation == "asset.archive" and (set(changes) != {"state", "reason"} or changes.get("state") != "archived"):
                raise AVDSError("VALIDATION_FAILED", "归档变更不合法")
        for concept_id in concept_ids:
            if not self._one("SELECT 1 FROM concepts WHERE concept_id=?", (concept_id,)):
                raise AVDSError("UNKNOWN_CONCEPT", f"未知概念：{concept_id}")
        proposal_id = req.get("proposal_id") or new_id("proposal")
        revision = int(req.get("revision", 1))
        if revision > 1:
            previous = self._one("SELECT revision,state,operation,target_id FROM change_proposals WHERE proposal_id=? ORDER BY revision DESC LIMIT 1", (proposal_id,))
            if not previous or previous["revision"] + 1 != revision or previous["state"] not in {"draft", "in_review"}:
                raise AVDSError("STALE_PROPOSAL", "修订号不是当前版本的下一版")
            if previous["operation"] != operation or previous["target_id"] != target_id:
                raise AVDSError("VALIDATION_FAILED", "修订不能更换操作类型或目标对象")
            self.db.execute("UPDATE change_proposals SET state='superseded' WHERE proposal_id=? AND revision=?", (proposal_id, previous["revision"]))
        body = {"contract_version": "1.0", "operation_id": req["operation_id"], "proposal_id": proposal_id,
                "revision": revision, "operation": operation, "target_revision": target_revision,
                "file_hash": file_hash, "source": req.get("source", {"origin": "agent-analysis"}),
                "analysis_run_id": req.get("analysis_run_id"), "concept_ids": concept_ids,
                "candidate_concept_refs": candidate_refs, "uncertainties": req.get("uncertainties", []), "changes": changes}
        body["queue_item_id" if operation == "asset.create" else "asset_id"] = target_id
        if operation == "asset.archive":
            body.pop("concept_ids", None); body.pop("candidate_concept_refs", None)
        validate_schema("asset-proposal", body)
        proposal_hash = digest_json(body)
        self.db.execute("INSERT INTO change_proposals VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
            proposal_id, revision, operation, req["operation_id"], "queue" if operation == "asset.create" else "asset",
            target_id, target_revision, file_hash, json.dumps(body, ensure_ascii=False), proposal_hash, "in_review", now()))
        if operation == "asset.create":
            self.db.execute("UPDATE review_queue_items SET state='in_review',updated_at=? WHERE queue_item_id=?", (now(), target_id))
        return {"proposal_id": proposal_id, "revision": revision, "proposal_hash": proposal_hash, "body": body}

    def _normalize_term(self, value):
        return " ".join(value.casefold().strip().split())

    def _create_concept_proposal(self, req):
        changes = req.get("changes") or {}
        if changes.get("facet") not in FACETS or not changes.get("preferred_name") or not changes.get("definition"):
            raise AVDSError("VALIDATION_FAILED", "概念字段不合法")
        terms = [changes["preferred_name"], *(changes.get("aliases") or [])]
        for term in terms:
            normalized = self._normalize_term(term)
            if self._one("SELECT 1 FROM concept_terms WHERE normalized_term=?", (normalized,)):
                raise AVDSError("CONCEPT_DUPLICATE", f"词条已存在：{term}")
        candidate_id, proposal_id = req.get("candidate_id") or new_id("candidate"), req.get("proposal_id") or new_id("proposal")
        revision = int(req.get("revision", 1))
        if revision > 1:
            previous = self._one("SELECT revision,state,target_id FROM change_proposals WHERE proposal_id=? ORDER BY revision DESC LIMIT 1", (proposal_id,))
            if not previous or previous["revision"] + 1 != revision or previous["state"] not in {"draft", "in_review"}:
                raise AVDSError("STALE_PROPOSAL", "概念修订号不合法")
            if req.get("candidate_id") and req["candidate_id"] != previous["target_id"]:
                raise AVDSError("VALIDATION_FAILED", "修订不能更换候选概念身份")
            candidate_id = previous["target_id"]
            self.db.execute("UPDATE change_proposals SET state='superseded' WHERE proposal_id=? AND revision=?", (proposal_id, previous["revision"]))
        body = {"contract_version": "1.0", "operation_id": req["operation_id"], "proposal_id": proposal_id,
                "revision": revision, "operation": "concept.create", "candidate_id": candidate_id,
                "target_revision": 0, "source": req.get("source", {"note": "agent proposal"}),
                "uncertainties": req.get("uncertainties", []), "changes": changes}
        validate_schema("concept-proposal", body)
        proposal_hash = digest_json(body); stamp = now()
        self.db.execute("INSERT OR IGNORE INTO concept_candidates VALUES(?,?,'in_review',NULL,?,?)", (candidate_id, proposal_id, stamp, stamp))
        self.db.execute("UPDATE concept_candidates SET state='in_review',updated_at=? WHERE candidate_id=?", (stamp, candidate_id))
        self.db.execute("INSERT INTO change_proposals VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
            proposal_id, revision, "concept.create", req["operation_id"], "candidate", candidate_id, 0, None,
            json.dumps(body, ensure_ascii=False), proposal_hash, "in_review", stamp))
        return {"candidate_id": candidate_id, "proposal_id": proposal_id, "revision": revision,
                "proposal_hash": proposal_hash, "body": body}

    def _create_content_proposal(self, req):
        operation = req["operation"]; kind, action = operation.split(".", 1); changes = req.get("changes") or {}
        target_id = req.get(f"{kind}_id") or new_id(kind); target_revision = int(req.get("target_revision", 0))
        proposal_id = req.get("proposal_id") or new_id("proposal"); revision = int(req.get("revision", 1))
        previous = None
        if revision > 1:
            previous = self._one("SELECT * FROM change_proposals WHERE proposal_id=? ORDER BY revision DESC LIMIT 1", (proposal_id,))
            if not previous or previous["revision"] + 1 != revision or previous["state"] not in {"draft", "in_review"}:
                raise AVDSError("STALE_PROPOSAL", "内容修订号不合法")
            if previous["operation"] != operation:
                raise AVDSError("VALIDATION_FAILED", "修订不能更换操作类型")
            if action == "create":
                target_id = previous["target_id"]
            elif previous["target_id"] != target_id:
                raise AVDSError("VALIDATION_FAILED", "修订不能更换目标对象")
        if action == "create":
            if req.get(f"{kind}_id") or target_revision != 0: raise AVDSError("VALIDATION_FAILED", f"{operation} 目标不合法")
        else:
            table, id_column = ("knowledge_articles", "knowledge_id") if kind == "knowledge" else ("prompt_modules", "prompt_id")
            current = self._one(f"SELECT revision,state FROM {table} WHERE {id_column}=?", (target_id,))
            if not current: raise AVDSError("NOT_FOUND", f"{kind} 不存在")
            if current["revision"] != target_revision: raise AVDSError("TARGET_REVISION_CONFLICT", "目标修订已变化")
        if action == "archive":
            if set(changes) != {"state", "reason"} or changes.get("state") != "archived": raise AVDSError("VALIDATION_FAILED", "归档正文不合法")
        elif kind == "knowledge":
            if not changes.get("title") or not changes.get("content_markdown"): raise AVDSError("VALIDATION_FAILED", "知识文章缺少标题或正文")
            for link in changes.get("links", []):
                if link.get("target_kind") not in {"asset", "concept", "prompt"} or not link.get("target_id"): raise AVDSError("VALIDATION_FAILED", "知识关联不合法")
                table = {"asset": ("assets", "asset_id"), "concept": ("concepts", "concept_id"), "prompt": ("prompt_modules", "prompt_id")}[link["target_kind"]]
                if not self._one(f"SELECT 1 FROM {table[0]} WHERE {table[1]}=?", (link["target_id"],)): raise AVDSError("NOT_FOUND", "知识关联目标不存在")
        else:
            if not changes.get("name") or not isinstance(changes.get("template"), str): raise AVDSError("VALIDATION_FAILED", "Prompt 缺少名称或模板")
            if not isinstance(changes.get("variables", {}), dict): raise AVDSError("VALIDATION_FAILED", "Prompt variables 必须是对象")
            referenced = set(re.findall(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}", changes["template"])); declared = set(changes.get("variables", {}))
            if referenced - declared: raise AVDSError("VALIDATION_FAILED", "模板引用未声明变量")
            for knowledge_id in changes.get("knowledge_ids", []):
                if not self._one("SELECT 1 FROM knowledge_articles WHERE knowledge_id=? AND state='active'", (knowledge_id,)): raise AVDSError("NOT_FOUND", "Prompt 引用知识不存在")
            for concept_id in changes.get("concept_ids", []):
                if not self._one("SELECT 1 FROM concepts WHERE concept_id=?", (concept_id,)): raise AVDSError("UNKNOWN_CONCEPT", "Prompt 引用概念不存在")
        if revision > 1:
            self.db.execute("UPDATE change_proposals SET state='superseded' WHERE proposal_id=? AND revision=?", (proposal_id, previous["revision"]))
        body = {"contract_version": "1.0", "operation_id": req["operation_id"], "proposal_id": proposal_id,
                "revision": revision, "operation": operation, "target_id": target_id, "target_revision": target_revision,
                "source": req.get("source", {"origin": "agent-analysis"}), "uncertainties": req.get("uncertainties", []), "changes": changes}
        validate_schema("content-proposal", body); proposal_hash = digest_json(body)
        self.db.execute("INSERT INTO change_proposals VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
            proposal_id, revision, operation, req["operation_id"], kind, target_id, target_revision, None,
            json.dumps(body, ensure_ascii=False), proposal_hash, "in_review", now()))
        return {f"{kind}_id": target_id, "proposal_id": proposal_id, "revision": revision, "proposal_hash": proposal_hash, "body": body}

    def review_list(self):
        rows = self.db.execute("SELECT proposal_id,revision,operation,target_kind,target_id,proposal_hash,body_json,created_at FROM change_proposals WHERE state='in_review' ORDER BY created_at").fetchall()
        return {"items": [{**dict(r), "body": json.loads(r["body_json"])} for r in rows]}

    def proposal_get(self, proposal_id: str, revision=None):
        if revision is None:
            row = self._one("SELECT * FROM change_proposals WHERE proposal_id=? ORDER BY revision DESC LIMIT 1", (proposal_id,))
        else:
            row = self._one("SELECT * FROM change_proposals WHERE proposal_id=? AND revision=?", (proposal_id, revision))
        if not row:
            raise AVDSError("NOT_FOUND", "提案不存在")
        value = dict(row); value["body"] = json.loads(value.pop("body_json")); return value

    def review_action(self, req: dict, reviewer_path: str):
        action = req.get("action")
        if action in {"defer_current", "defer_remaining_batch"}:
            result = self.defer(req, remaining=action == "defer_remaining_batch")
            event_id = "reviewevent_" + digest_json({"operation_id": req.get("operation_id"), "action": action}).split(":", 1)[1][:32]
            self.db.execute("INSERT OR IGNORE INTO review_events VALUES(?,?,?,?,?,?,?,?,?,?)", (
                event_id, action, None, None, None, None, None, reviewer_path, now(), json.dumps(req, ensure_ascii=False)))
            return {"review_event_id": event_id, **result}
        proposal = self.proposal_get(req.get("proposal_id", ""), req.get("revision"))
        if action == "request_changes":
            def request_changes():
                changed = self.db.execute("UPDATE change_proposals SET state='draft' WHERE proposal_id=? AND revision=? AND state='in_review'", (proposal["proposal_id"], proposal["revision"])).rowcount
                if changed == 0: raise AVDSError("STALE_PROPOSAL", "提案不再处于待审状态")
                event_id = new_id("review")
                self.db.execute("INSERT INTO review_events VALUES(?,?,?,?,?,?,?,?,?,?)", (event_id, action, proposal["proposal_id"], proposal["revision"], proposal["proposal_hash"], proposal["file_hash"], proposal["target_revision"], reviewer_path, now(), json.dumps(req, ensure_ascii=False)))
                return {"review_event_id": event_id, "proposal_id": proposal["proposal_id"], "state": "draft"}
            return self._operation(req.get("operation_id"), req, request_changes)
        if action == "reject":
            def reject():
                with self.db:
                    changed = self.db.execute("UPDATE change_proposals SET state='rejected' WHERE proposal_id=? AND revision=? AND state='in_review'", (proposal["proposal_id"], proposal["revision"])).rowcount
                    if changed == 0: raise AVDSError("STALE_PROPOSAL", "提案不再处于待审状态")
                    if proposal["target_kind"] == "queue":
                        self.db.execute("UPDATE review_queue_items SET state='resolved',updated_at=? WHERE queue_item_id=?", (now(), proposal["target_id"]))
                    event_id = new_id("review")
                    self.db.execute("INSERT INTO review_events VALUES(?,?,?,?,?,?,?,?,?,?)", (event_id, action, proposal["proposal_id"], proposal["revision"], proposal["proposal_hash"], proposal["file_hash"], proposal["target_revision"], reviewer_path, now(), json.dumps(req, ensure_ascii=False)))
                return {"review_event_id": event_id, "proposal_id": proposal["proposal_id"], "state": "rejected"}
            return self._operation(req.get("operation_id"), req, reject)
        if action != "approve":
            raise AVDSError("VALIDATION_FAILED", "未知审核动作")
        for field in ("proposal_hash", "target_revision"):
            if req.get(field) != proposal[field]:
                raise AVDSError("STALE_PROPOSAL", f"审批绑定字段不一致：{field}")
        if proposal["file_hash"] and req.get("file_hash") != proposal["file_hash"]:
            raise AVDSError("HASH_MISMATCH", "审批文件哈希不一致")
        body = proposal["body"]
        if body.get("candidate_concept_refs"):
            raise AVDSError("DEPENDENCY_UNRESOLVED", "候选概念尚未落实")
        review_id = new_id("review")
        operation_id = req.get("operation_id") or new_id("reviewop")
        request = dict(req)

        def work():
            with self.db:
                changed = self.db.execute("UPDATE change_proposals SET state='approved' WHERE proposal_id=? AND revision=? AND state='in_review'",
                                          (proposal["proposal_id"], proposal["revision"])).rowcount
                if changed == 0:
                    raise AVDSError("STALE_PROPOSAL", "提案不再处于待审状态")
                self.db.execute("INSERT INTO review_events VALUES(?,?,?,?,?,?,?,?,?,?)", (
                    review_id, "approve", proposal["proposal_id"], proposal["revision"], proposal["proposal_hash"],
                    proposal["file_hash"], proposal["target_revision"], reviewer_path, now(), json.dumps(req, ensure_ascii=False)))
                result = self._commit(proposal, review_id)
            return {"review_event_id": review_id, **result}
        return self._operation(operation_id, request, work)

    def _commit(self, proposal: dict, review_id: str):
        body, operation = proposal["body"], proposal["operation"]
        if operation.startswith("knowledge."): return self._commit_knowledge(proposal, review_id)
        if operation.startswith("prompt."): return self._commit_prompt(proposal, review_id)
        if operation == "concept.create":
            changes = body["changes"]
            for term in [changes["preferred_name"], *(changes.get("aliases") or [])]:
                if self._one("SELECT 1 FROM concept_terms WHERE normalized_term=?", (self._normalize_term(term),)):
                    raise AVDSError("CONCEPT_DUPLICATE", f"词条已存在：{term}")
            concept_id, stamp = new_id("concept"), now()
            self.db.execute("INSERT INTO concepts VALUES(?,?,?,?,1,?)", (concept_id, changes["preferred_name"], changes["facet"], changes["definition"], stamp))
            terms = changes.get("terms") or {}
            preferred_terms = [("zh", terms.get("zh") or changes["preferred_name"])]
            if terms.get("en"): preferred_terms.append(("en", terms["en"]))
            for language, term in preferred_terms:
                self.db.execute("INSERT INTO concept_terms VALUES(?,?,?,?,?, 'preferred')", (new_id("term"), concept_id, language, term, self._normalize_term(term)))
            for alias in changes.get("aliases") or []:
                self.db.execute("INSERT INTO concept_terms VALUES(?,?,?,?,?, 'alias')", (new_id("term"), concept_id, "und", alias, self._normalize_term(alias)))
            for relation in changes.get("relations") or []:
                if not self._one("SELECT 1 FROM concepts WHERE concept_id=?", (relation["concept_id"],)):
                    raise AVDSError("UNKNOWN_CONCEPT", "关系目标不存在")
                self.db.execute("INSERT INTO concept_relations VALUES(?,?,?)", (concept_id, relation["kind"], relation["concept_id"]))
            self.db.execute("INSERT INTO concept_revisions VALUES(?,1,?,?,?,?)", (concept_id, json.dumps(changes, ensure_ascii=False), proposal["proposal_id"], review_id, stamp))
            self.db.execute("UPDATE concept_candidates SET state='resolved',resolved_concept_id=?,updated_at=? WHERE candidate_id=?", (concept_id, stamp, proposal["target_id"]))
            return {"candidate_id": proposal["target_id"], "concept_id": concept_id, "state": "committed"}
        if operation == "asset.create":
            queue = self.queue_get(proposal["target_id"])
            if queue["file_hash"] != proposal["file_hash"]:
                raise AVDSError("HASH_MISMATCH", "待审文件已变化")
            asset_id, stamp = queue["asset_id"], now()
            changes = body["changes"]
            digest = proposal["file_hash"].split(":", 1)[1]
            file_row = self._one("SELECT relative_path,format FROM files WHERE file_hash=?", (proposal["file_hash"],))
            old_path = safe_relative(self.vault, file_row["relative_path"])
            suffix = old_path.suffix
            object_relative = f"objects/sha256/{digest[:2]}/{digest}{suffix}"
            object_path = safe_relative(self.vault, object_relative); object_path.parent.mkdir(parents=True, exist_ok=True)
            if not object_path.exists():
                os.replace(old_path, object_path)
                sync_directory(object_path.parent)
            readonly(object_path)
            if file_sha256(object_path) != proposal["file_hash"]:
                raise AVDSError("HASH_MISMATCH", "对象文件哈希异常")
            self.db.execute("UPDATE files SET relative_path=? WHERE file_hash=?", (object_relative, proposal["file_hash"]))
            self.db.execute("UPDATE assets SET state='active',revision=1,title=?,description=?,design_value=?,updated_at=? WHERE asset_id=? AND state='staged'",
                            (changes["title"], changes.get("description"), changes.get("design_value"), stamp, asset_id))
            self._set_asset_concepts(asset_id, body.get("concept_ids", []))
            self.db.execute("UPDATE review_queue_items SET state='resolved',updated_at=? WHERE queue_item_id=?", (stamp, proposal["target_id"]))
            self._reindex(asset_id)
            return {"asset_id": asset_id, "revision": 1, "state": "active"}
        asset = self._one("SELECT * FROM assets WHERE asset_id=?", (proposal["target_id"],))
        if not asset or asset["revision"] != proposal["target_revision"]:
            raise AVDSError("TARGET_REVISION_CONFLICT", "正式资产目标修订冲突")
        new_revision, stamp = asset["revision"] + 1, now()
        if operation == "asset.archive":
            self.db.execute("UPDATE assets SET state='archived',revision=?,updated_at=? WHERE asset_id=?", (new_revision, stamp, asset["asset_id"]))
            self.db.execute("DELETE FROM search_fts WHERE asset_id=?", (asset["asset_id"],))
            self.db.execute("DELETE FROM search_documents WHERE asset_id=?", (asset["asset_id"],))
            return {"asset_id": asset["asset_id"], "revision": new_revision, "state": "archived"}
        changes = body["changes"]
        self.db.execute("UPDATE assets SET title=?,description=?,design_value=?,revision=?,updated_at=? WHERE asset_id=?", (
            changes.get("title", asset["title"]), changes.get("description", asset["description"]),
            changes.get("design_value", asset["design_value"]), new_revision, stamp, asset["asset_id"]))
        self._set_asset_concepts(asset["asset_id"], body.get("concept_ids", [])); self._reindex(asset["asset_id"])
        return {"asset_id": asset["asset_id"], "revision": new_revision, "state": "active"}

    def _atomic_content_write(self, relative, data: bytes):
        target = safe_relative(self.vault, relative); target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".partial")
        if target.exists():
            if target.read_bytes() == data: return
            raise AVDSError("HASH_MISMATCH", "目标修订文件已存在但内容不同")
        if temporary.exists():
            if temporary.read_bytes() != data: raise AVDSError("RECOVERY_REQUIRED", "未完成文件与当前请求不一致")
            os.replace(temporary, target); readonly(target); return
        with temporary.open("xb") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, target); readonly(target)
        sync_directory(target.parent)

    def _commit_knowledge(self, proposal, review_id):
        body, action, knowledge_id = proposal["body"], proposal["operation"].split(".", 1)[1], proposal["target_id"]
        current = self._one("SELECT * FROM knowledge_articles WHERE knowledge_id=?", (knowledge_id,)); stamp = now()
        if action == "archive":
            revision = current["revision"] + 1; self.db.execute("UPDATE knowledge_articles SET state='archived',revision=?,updated_at=? WHERE knowledge_id=?", (revision, stamp, knowledge_id)); self.db.execute("DELETE FROM knowledge_fts WHERE knowledge_id=?", (knowledge_id,)); return {"knowledge_id": knowledge_id, "revision": revision, "state": "archived"}
        changes = body["changes"]; revision = 1 if current is None else current["revision"] + 1
        relative = f"knowledge/{knowledge_id}/r{revision}.md"; self._atomic_content_write(relative, changes["content_markdown"].encode())
        if current is None:
            self.db.execute("INSERT INTO knowledge_articles VALUES(?,'active',?,?,?,?,?,?)", (knowledge_id, revision, changes["title"], changes.get("summary", ""), relative, stamp, stamp))
        else:
            self.db.execute("UPDATE knowledge_articles SET state='active',revision=?,title=?,summary=?,relative_path=?,updated_at=? WHERE knowledge_id=?", (revision, changes["title"], changes.get("summary", ""), relative, stamp, knowledge_id))
        self.db.execute("INSERT INTO knowledge_revisions VALUES(?,?,?,?,?,?,?,?)", (knowledge_id, revision, changes["title"], changes.get("summary", ""), relative, proposal["proposal_id"], review_id, stamp))
        self.db.execute("DELETE FROM knowledge_links WHERE knowledge_id=?", (knowledge_id,))
        self.db.executemany("INSERT INTO knowledge_links VALUES(?,?,?)", [(knowledge_id, x["target_kind"], x["target_id"]) for x in changes.get("links", [])])
        self.db.execute("DELETE FROM knowledge_fts WHERE knowledge_id=?", (knowledge_id,)); self.db.execute("INSERT INTO knowledge_fts VALUES(?,?,?,?)", (knowledge_id, changes["title"], changes.get("summary", ""), changes["content_markdown"]))
        return {"knowledge_id": knowledge_id, "revision": revision, "state": "active"}

    def _commit_prompt(self, proposal, review_id):
        body, action, prompt_id = proposal["body"], proposal["operation"].split(".", 1)[1], proposal["target_id"]
        current = self._one("SELECT * FROM prompt_modules WHERE prompt_id=?", (prompt_id,)); stamp = now()
        if action == "archive":
            revision = current["revision"] + 1; self.db.execute("UPDATE prompt_modules SET state='archived',revision=?,updated_at=? WHERE prompt_id=?", (revision, stamp, prompt_id)); return {"prompt_id": prompt_id, "revision": revision, "state": "archived"}
        changes = body["changes"]; revision = 1 if current is None else current["revision"] + 1
        prompt_body = {"name": changes["name"], "description": changes.get("description", ""), "template": changes["template"],
                       "variables": changes.get("variables", {}), "knowledge_ids": changes.get("knowledge_ids", []), "concept_ids": changes.get("concept_ids", [])}
        relative = f"prompts/{prompt_id}/r{revision}.json"; encoded = json.dumps(prompt_body, ensure_ascii=False, sort_keys=True, indent=2).encode(); self._atomic_content_write(relative, encoded)
        body_json = encoded.decode()
        if current is None:
            self.db.execute("INSERT INTO prompt_modules VALUES(?,'active',?,?,?,?,?,?,?)", (prompt_id, revision, changes["name"], changes.get("description", ""), relative, body_json, stamp, stamp))
        else:
            self.db.execute("UPDATE prompt_modules SET state='active',revision=?,name=?,description=?,relative_path=?,body_json=?,updated_at=? WHERE prompt_id=?", (revision, changes["name"], changes.get("description", ""), relative, body_json, stamp, prompt_id))
        self.db.execute("INSERT INTO prompt_revisions VALUES(?,?,?,?,?,?,?,?)", (prompt_id, revision, changes["name"], relative, body_json, proposal["proposal_id"], review_id, stamp))
        return {"prompt_id": prompt_id, "revision": revision, "state": "active"}

    def _set_asset_concepts(self, asset_id, concept_ids):
        self.db.execute("DELETE FROM asset_concepts WHERE asset_id=?", (asset_id,))
        self.db.executemany("INSERT INTO asset_concepts(asset_id,concept_id) VALUES(?,?)", [(asset_id, cid) for cid in concept_ids])

    def _reindex(self, asset_id):
        row = self._one("SELECT * FROM assets WHERE asset_id=? AND state='active'", (asset_id,))
        terms = " ".join(r[0] for r in self.db.execute("SELECT ct.term FROM asset_concepts ac JOIN concept_terms ct USING(concept_id) WHERE ac.asset_id=?", (asset_id,)))
        values = (asset_id, row["title"] or "", row["description"] or "", row["design_value"] or "", terms)
        self.db.execute("INSERT OR REPLACE INTO search_documents VALUES(?,?,?,?,?)", values)
        self.db.execute("DELETE FROM search_fts WHERE asset_id=?", (asset_id,)); self.db.execute("INSERT INTO search_fts VALUES(?,?,?,?,?)", values)

    def asset_get(self, asset_id):
        row = self._one("SELECT a.*,f.relative_path,f.mime_type,f.width,f.height,f.byte_size FROM assets a JOIN files f USING(file_hash) WHERE a.asset_id=? AND a.state IN ('active','archived')", (asset_id,))
        if not row: raise AVDSError("NOT_FOUND", "正式资产不存在")
        result = dict(row)
        result["concept_ids"] = [r[0] for r in self.db.execute("SELECT concept_id FROM asset_concepts WHERE asset_id=?", (asset_id,))]
        return result

    def asset_preview(self, asset_id):
        asset = self.asset_get(asset_id); path = safe_relative(self.vault, asset["relative_path"])
        if not path.exists(): raise AVDSError("FILE_MISSING", "正式原图缺失")
        if file_sha256(path) != asset["file_hash"]: raise AVDSError("HASH_MISMATCH", "正式原图指纹异常")
        return {"asset_id": asset_id, "state": asset["state"], "file_hash": asset["file_hash"],
                "content_path": str(path), "access": "read-only", "mime_type": asset["mime_type"]}

    def candidate_get(self, candidate_id):
        row = self._one("SELECT * FROM concept_candidates WHERE candidate_id=?", (candidate_id,))
        if not row: raise AVDSError("NOT_FOUND", "概念候选不存在")
        return dict(row)

    def search_concepts(self, req):
        text = self._normalize_term(req.get("text", "")); limit = min(int(req.get("limit", 20)), 100)
        rows = self.db.execute("""SELECT DISTINCT c.* FROM concepts c JOIN concept_terms t USING(concept_id)
          WHERE t.normalized_term=? OR t.normalized_term LIKE ? ORDER BY (t.normalized_term=?) DESC,c.preferred_name LIMIT ?""",
          (text, f"%{text}%", text, limit)).fetchall()
        items = []
        for row in rows:
            value = dict(row)
            value["terms"] = [dict(r) for r in self.db.execute("SELECT language,term,kind FROM concept_terms WHERE concept_id=? ORDER BY kind,language", (row["concept_id"],))]
            value["relations"] = [dict(r) for r in self.db.execute("SELECT kind,target_concept_id AS concept_id FROM concept_relations WHERE source_concept_id=?", (row["concept_id"],))]
            items.append(value)
        return {"items": items}

    def _concept_set(self, concept_id, expand_narrower=False, expand_related=False):
        if not self._one("SELECT 1 FROM concepts WHERE concept_id=?", (concept_id,)):
            raise AVDSError("UNKNOWN_CONCEPT", f"未知概念：{concept_id}")
        found, queue = {concept_id}, [concept_id]
        if expand_narrower:
            while queue:
                current = queue.pop()
                children = [r[0] for r in self.db.execute(
                    "SELECT source_concept_id FROM concept_relations WHERE kind='broader' AND target_concept_id=? UNION SELECT target_concept_id FROM concept_relations WHERE kind='narrower' AND source_concept_id=?",
                    (current, current))]
                for child in children:
                    if child not in found: found.add(child); queue.append(child)
        if expand_related:
            related = [r[0] for r in self.db.execute(
                "SELECT target_concept_id FROM concept_relations WHERE kind='related' AND source_concept_id=? UNION SELECT source_concept_id FROM concept_relations WHERE kind='related' AND target_concept_id=?",
                (concept_id, concept_id))]
            found.update(related)
        return found

    def _text_asset_ids(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 200:
            raise AVDSError("VALIDATION_FAILED", "文本查询必须为 1～200 字符")
        text = text.strip(); escaped = '"' + text.replace('"', '""') + '"'; like = f"%{text}%"
        rows = self.db.execute("""SELECT asset_id FROM search_fts WHERE search_fts MATCH ?
          UNION SELECT asset_id FROM search_documents WHERE title LIKE ? OR description LIKE ? OR design_value LIKE ? OR terms LIKE ?""",
          (escaped, like, like, like, like)).fetchall()
        return {r[0] for r in rows}

    def search_assets(self, req):
        allowed = {"command", "contract_version", "scope", "must", "should", "must_not", "filters", "expand_narrower", "expand_related", "limit", "include_explanation", "text"}
        unknown = set(req) - allowed
        if unknown: raise AVDSError("VALIDATION_FAILED", f"未知查询字段：{', '.join(sorted(unknown))}")
        must, should, must_not = req.get("must", []), req.get("should", []), req.get("must_not", [])
        if req.get("text"): must = [*must, {"text": req["text"]}]
        expand_narrower, expand_related = bool(req.get("expand_narrower")), bool(req.get("expand_related"))
        rows = self.db.execute("""SELECT a.asset_id,a.title,a.revision,a.file_hash,a.updated_at,
          f.format,f.width,f.height FROM assets a JOIN files f USING(file_hash) WHERE a.state='active'""").fetchall()
        items = []
        for row in rows:
            value = dict(row); asset_id = value["asset_id"]
            concepts = {r[0] for r in self.db.execute("SELECT concept_id FROM asset_concepts WHERE asset_id=?", (asset_id,))}
            matches = True
            for condition in must:
                if condition.get("concept_id") and concepts.isdisjoint(self._concept_set(condition["concept_id"], expand_narrower, expand_related)): matches = False
                if condition.get("text") and asset_id not in self._text_asset_ids(condition["text"]): matches = False
            for condition in must_not:
                if condition.get("concept_id") and not concepts.isdisjoint(self._concept_set(condition["concept_id"], expand_narrower, False)): matches = False
                if condition.get("text") and asset_id in self._text_asset_ids(condition["text"]): matches = False
            filters = req.get("filters") or {}
            orientation = filters.get("orientation")
            actual_orientation = "square" if value["width"] == value["height"] else ("landscape" if value["width"] > value["height"] else "portrait")
            if orientation and orientation != actual_orientation: matches = False
            if filters.get("format") and filters["format"] != value["format"]: matches = False
            if filters.get("min_width") and value["width"] < int(filters["min_width"]): matches = False
            if filters.get("min_height") and value["height"] < int(filters["min_height"]): matches = False
            if not matches: continue
            score = 0
            for condition in should:
                if condition.get("concept_id") and not concepts.isdisjoint(self._concept_set(condition["concept_id"], expand_narrower, expand_related)): score += 10
                if condition.get("text") and asset_id in self._text_asset_ids(condition["text"]): score += 2
            value["score"] = score; value.pop("updated_at", None); items.append(value)
        items.sort(key=lambda item: (-item["score"], item["asset_id"]))
        limit = min(max(int(req.get("limit", 10)), 1), 100)
        for item in items: item.pop("score", None)
        return {"scope": "active", "items": items[:limit], "constraints_relaxed": False, "unresolved_conditions": []}

    def search_explain(self, req):
        asset = self.asset_get(req.get("asset_id", "")); query = req.get("query") or {}
        concept_ids = set(asset["concept_ids"]); reasons = []
        for bucket in ("must", "should"):
            for condition in query.get(bucket, []):
                if condition.get("concept_id") in concept_ids: reasons.append({"kind": bucket, "concept_id": condition["concept_id"]})
                if condition.get("text") and asset["asset_id"] in self._text_asset_ids(condition["text"]): reasons.append({"kind": bucket, "text": condition["text"]})
        return {"asset_id": asset["asset_id"], "matches": reasons}

    def search_related(self, req):
        asset_id = req.get("asset_id", "")
        self.asset_get(asset_id)
        rows = self.db.execute("""SELECT relation_type, CASE WHEN source_asset_id=? THEN target_asset_id ELSE source_asset_id END AS asset_id
          FROM asset_relations WHERE source_asset_id=? OR target_asset_id=?""", (asset_id, asset_id, asset_id)).fetchall()
        return {"asset_id": asset_id, "items": [dict(r) for r in rows]}

    def knowledge_get(self, knowledge_id):
        row = self._one("SELECT * FROM knowledge_articles WHERE knowledge_id=?", (knowledge_id,))
        if not row: raise AVDSError("NOT_FOUND", "知识文章不存在")
        result = dict(row); path = safe_relative(self.vault, row["relative_path"])
        if not path.exists(): raise AVDSError("FILE_MISSING", "知识正文缺失")
        result["content_markdown"] = path.read_text(encoding="utf-8"); result["links"] = [dict(r) for r in self.db.execute("SELECT target_kind,target_id FROM knowledge_links WHERE knowledge_id=?", (knowledge_id,))]
        return result

    def knowledge_search(self, req):
        text = (req.get("text") or "").strip(); limit = min(max(int(req.get("limit", 20)), 1), 100)
        if text:
            escaped = '"' + text.replace('"', '""') + '"'; like = f"%{text}%"
            rows = self.db.execute("""SELECT k.knowledge_id,k.title,k.summary,k.revision FROM knowledge_articles k WHERE k.state='active' AND
              (k.knowledge_id IN (SELECT knowledge_id FROM knowledge_fts WHERE knowledge_fts MATCH ?) OR k.title LIKE ? OR k.summary LIKE ? OR
               k.knowledge_id IN (SELECT knowledge_id FROM knowledge_fts WHERE body LIKE ?))
              ORDER BY k.updated_at DESC LIMIT ?""", (escaped, like, like, like, limit)).fetchall()
        else:
            rows = self.db.execute("SELECT knowledge_id,title,summary,revision FROM knowledge_articles WHERE state='active' ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return {"items": [dict(r) for r in rows]}

    def prompt_get(self, prompt_id):
        row = self._one("SELECT * FROM prompt_modules WHERE prompt_id=?", (prompt_id,))
        if not row: raise AVDSError("NOT_FOUND", "Prompt 模块不存在")
        result = dict(row); result["body"] = json.loads(result.pop("body_json")); return result

    def prompt_list(self, req):
        state = req.get("state", "active"); limit = min(max(int(req.get("limit", 50)), 1), 100)
        rows = self.db.execute("SELECT prompt_id,name,description,revision,state FROM prompt_modules WHERE state=? ORDER BY updated_at DESC LIMIT ?", (state, limit)).fetchall()
        return {"items": [dict(r) for r in rows]}

    def prompt_render(self, req):
        prompt = self.prompt_get(req.get("prompt_id", ""))
        if prompt["state"] != "active": raise AVDSError("NOT_FOUND", "Prompt 模块不是 active")
        body, values = prompt["body"], req.get("variables") or {}; definitions = body.get("variables", {})
        unknown = set(values) - set(definitions)
        if unknown: raise AVDSError("VALIDATION_FAILED", "未知 Prompt 变量：" + ", ".join(sorted(unknown)))
        resolved = {}
        for name, definition in definitions.items():
            if name in values: value = values[name]
            elif "default" in definition: value = definition["default"]
            elif definition.get("required"): raise AVDSError("VALIDATION_FAILED", f"缺少 Prompt 变量：{name}")
            else: value = ""
            expected = definition.get("type", "string")
            if expected == "string" and not isinstance(value, str): raise AVDSError("VALIDATION_FAILED", f"变量 {name} 必须是字符串")
            if expected == "number" and not isinstance(value, (int, float)): raise AVDSError("VALIDATION_FAILED", f"变量 {name} 必须是数字")
            resolved[name] = str(value)
        template = body["template"]
        referenced = set(re.findall(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}", template))
        if referenced - set(definitions): raise AVDSError("VALIDATION_FAILED", "模板引用未声明变量")
        rendered = re.sub(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}", lambda m: resolved[m.group(1)], template)
        knowledge = [self.knowledge_get(item) for item in body.get("knowledge_ids", [])]
        return {"prompt_id": prompt["prompt_id"], "revision": prompt["revision"], "rendered": rendered,
                "knowledge": [{"knowledge_id": x["knowledge_id"], "revision": x["revision"], "title": x["title"]} for x in knowledge],
                "concept_ids": body.get("concept_ids", [])}

    def _ensure_feature(self, asset_id, file_hash, image_path, force=False):
        digest = file_hash.split(":", 1)[1]; relative = f"cache/featureprints/{digest}.avdsfp"; output = safe_relative(self.vault, relative)
        row = self._one("SELECT * FROM visual_features WHERE asset_id=?", (asset_id,)) if asset_id else None
        capability = visual_capability(self.visual_provider, self.vision_helper)
        if not capability["available"]:
            raise AVDSError("CAPABILITY_UNAVAILABLE", capability["reason"])
        build = os_build()
        if not force and row and row["file_hash"] == file_hash and row["os_build"] == build and output.exists(): return output
        if not self.vision_helper.exists(): raise AVDSError("STORAGE_UNAVAILABLE", "Apple Vision helper 未安装")
        output.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([str(self.vision_helper), "encode", str(image_path), str(output)], capture_output=True, text=True, timeout=60)
        if result.returncode != 0: raise AVDSError("ASSET_UNAVAILABLE", "Apple Vision 无法生成图像特征")
        metadata = json.loads(result.stdout)
        if asset_id:
            self.db.execute("INSERT OR REPLACE INTO visual_features VALUES(?,?,?,?,?,?)", (asset_id, file_hash, relative, f"{metadata['engine']}-r{metadata['revision']}", build, now()))
        return output

    def visual_index(self, req):
        capability = visual_capability(self.visual_provider, self.vision_helper)
        if not capability["available"]:
            raise AVDSError("CAPABILITY_UNAVAILABLE", capability["reason"])
        force = bool(req.get("force")); indexed = []
        rows = self.db.execute("SELECT a.asset_id,a.file_hash,f.relative_path FROM assets a JOIN files f USING(file_hash) WHERE a.state='active'").fetchall()
        for row in rows:
            image_path = safe_relative(self.vault, row["relative_path"])
            self._ensure_feature(row["asset_id"], row["file_hash"], image_path, force); indexed.append(row["asset_id"])
        return {"indexed": indexed, "engine": "apple-vision-featureprint", "derived_only": True}

    def visual_search(self, req):
        asset_id, queue_id = req.get("asset_id"), req.get("queue_item_id")
        if bool(asset_id) == bool(queue_id): raise AVDSError("VALIDATION_FAILED", "必须且只能提供 asset_id 或 queue_item_id")
        if asset_id:
            item = self.asset_get(asset_id); image_path = safe_relative(self.vault, item["relative_path"]); file_hash = item["file_hash"]
            query_feature = self._ensure_feature(asset_id, file_hash, image_path)
        else:
            item = self.queue_get(queue_id); preview = self.queue_preview(queue_id); image_path = Path(preview["content_path"]); file_hash = item["file_hash"]
            query_feature = self._ensure_feature(None, file_hash, image_path)
        self.visual_index({})
        scored = []
        for row in self.db.execute("SELECT vf.*,a.title FROM visual_features vf JOIN assets a USING(asset_id) WHERE a.state='active'"):
            if row["asset_id"] == asset_id: continue
            feature_path = safe_relative(self.vault, row["relative_path"])
            result = subprocess.run([str(self.vision_helper), "distance", str(query_feature), str(feature_path)], capture_output=True, text=True, timeout=30)
            if result.returncode != 0: continue
            distance = float(result.stdout.strip())
            if req.get("max_distance") is None or distance <= float(req["max_distance"]): scored.append({"asset_id": row["asset_id"], "title": row["title"], "distance": distance})
        scored.sort(key=lambda item: (item["distance"], item["asset_id"])); limit = min(max(int(req.get("limit", 12)), 1), 50)
        return {"query": {"asset_id": asset_id, "queue_item_id": queue_id, "file_hash": file_hash}, "items": scored[:limit],
                "engine": "apple-vision-featureprint", "distance_order": "smaller_is_closer"}

    def rebuild_index(self):
        with self.db:
            self.db.execute("DELETE FROM search_fts"); self.db.execute("DELETE FROM search_documents")
            for row in self.db.execute("SELECT asset_id FROM assets WHERE state='active'").fetchall(): self._reindex(row[0])
        return {"rebuilt": True}

    def recover(self):
        recovered, pending = [], []
        rows = self.db.execute("SELECT operation_id,state FROM operations WHERE state IN ('pending','failed') ORDER BY created_at").fetchall()
        events = self.db.execute("SELECT * FROM review_events ORDER BY created_at").fetchall()
        event_by_operation = {}
        for event in events:
            detail = json.loads(event["detail_json"])
            if detail.get("operation_id"):
                event_by_operation[detail["operation_id"]] = (event, detail)
        for row in rows:
            pair = event_by_operation.get(row["operation_id"])
            if not pair:
                pending.append(row["operation_id"]); continue
            event, detail = pair
            proposal = self.proposal_get(event["proposal_id"], event["proposal_revision"])
            body = proposal["body"]
            result = None
            if proposal["operation"] == "asset.create":
                queue = self.queue_get(proposal["target_id"])
                asset = self._one("SELECT * FROM assets WHERE asset_id=?", (queue["asset_id"],))
                if asset["state"] == "active":
                    result = {"review_event_id": event["review_event_id"], "asset_id": asset["asset_id"],
                              "revision": asset["revision"], "state": asset["state"]}
            elif proposal["operation"] == "concept.create":
                candidate = self.candidate_get(proposal["target_id"])
                if candidate["resolved_concept_id"]:
                    result = {"review_event_id": event["review_event_id"], "candidate_id": candidate["candidate_id"],
                              "concept_id": candidate["resolved_concept_id"], "state": "committed"}
            elif proposal["operation"].startswith("knowledge."):
                value = self._one("SELECT * FROM knowledge_articles WHERE knowledge_id=?", (proposal["target_id"],))
                if value and value["revision"] == proposal["target_revision"] + 1:
                    result = {"review_event_id": event["review_event_id"], "knowledge_id": value["knowledge_id"], "revision": value["revision"], "state": value["state"]}
            elif proposal["operation"].startswith("prompt."):
                value = self._one("SELECT * FROM prompt_modules WHERE prompt_id=?", (proposal["target_id"],))
                if value and value["revision"] == proposal["target_revision"] + 1:
                    result = {"review_event_id": event["review_event_id"], "prompt_id": value["prompt_id"], "revision": value["revision"], "state": value["state"]}
            else:
                asset = self._one("SELECT * FROM assets WHERE asset_id=?", (proposal["target_id"],))
                if asset and asset["revision"] == proposal["target_revision"] + 1:
                    result = {"review_event_id": event["review_event_id"], "asset_id": asset["asset_id"],
                              "revision": asset["revision"], "state": asset["state"]}
            if result is None:
                with self.db:
                    result = {"review_event_id": event["review_event_id"], **self._commit(proposal, event["review_event_id"])}
            self.db.execute("UPDATE operations SET state='committed',result_json=?,updated_at=? WHERE operation_id=?",
                            (json.dumps(result, ensure_ascii=False), now(), row["operation_id"]))
            recovered.append(row["operation_id"])
        partials = []
        for partial in self.staging.glob("*.partial"):
            partials.append(partial.name)
        return {"recovered": recovered, "requires_manual_retry": pending, "orphan_partials": partials}

    def status(self):
        return {"vault": str(self.vault), "sqlite": sqlite3.sqlite_version,
                "journal_mode": self._one("PRAGMA journal_mode")[0], "synchronous": self._one("PRAGMA synchronous")[0],
                "foreign_keys": self._one("PRAGMA foreign_keys")[0], "busy_timeout": self._one("PRAGMA busy_timeout")[0]}
