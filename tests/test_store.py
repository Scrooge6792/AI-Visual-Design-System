import json
import shutil
import tempfile
import unittest
from pathlib import Path

from avds.errors import AVDSError
from avds.store import Store


FIXTURE = Path(__file__).parents[1] / ".build/phase0/account-analysis-fixture.png"


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="avds-tests-"))
        self.store = Store(self.temp / "vault")

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.temp)

    def stage(self, operation="import-1"):
        return self.store.stage({"operation_id": operation, "batch_id": "batch-1", "source_path": str(FIXTURE),
                                 "source": {"original_name": "fixture.png", "user_note": "later"}})

    def proposal(self, staged, operation="proposal-1"):
        return self.store.create_proposal({"operation_id": operation, "operation": "asset.create",
            "queue_item_id": staged["queue_item_id"], "concept_ids": [], "candidate_concept_refs": [],
            "changes": {"title": "蓝黄测试", "description": "左蓝右黄", "design_value": "构图测试"}})

    def approve(self, proposal, operation="review-1"):
        body = proposal["body"]
        return self.store.review_action({"action": "approve", "proposal_id": proposal["proposal_id"],
            "revision": proposal["revision"], "proposal_hash": proposal["proposal_hash"], "file_hash": body["file_hash"],
            "target_revision": 0, "operation_id": operation}, "/trusted/reviewer")

    def test_stage_is_idempotent_and_survives_reopen(self):
        staged = self.stage()
        self.assertEqual(staged, self.stage())
        self.store.defer({"operation_id": "defer-1", "queue_item_id": staged["queue_item_id"]})
        preview = self.store.queue_preview(staged["queue_item_id"])
        self.assertTrue(Path(preview["content_path"]).is_file())
        self.store.close(); self.store = Store(self.temp / "vault")
        self.assertEqual(self.store.queue_get(staged["queue_item_id"])["state"], "deferred")

    def test_idempotency_conflict(self):
        self.stage()
        with self.assertRaises(AVDSError) as error:
            self.store.stage({"operation_id": "import-1", "batch_id": "different", "source_path": str(FIXTURE)})
        self.assertEqual(error.exception.code, "IDEMPOTENCY_CONFLICT")

    def test_approval_binding_commit_and_search_isolation(self):
        staged = self.stage(); proposal = self.proposal(staged)
        self.assertEqual(self.store.search_assets({"text": "蓝黄"})["items"], [])
        bad = {"action": "approve", "proposal_id": proposal["proposal_id"], "revision": 1,
               "proposal_hash": "sha256:" + "0" * 64, "file_hash": staged["file_hash"],
               "target_revision": 0, "operation_id": "bad-review"}
        with self.assertRaises(AVDSError) as error: self.store.review_action(bad, "/trusted/reviewer")
        self.assertEqual(error.exception.code, "STALE_PROPOSAL")
        committed = self.approve(proposal)
        self.assertEqual(committed["state"], "active")
        self.assertEqual(committed, self.approve(proposal))
        found = self.store.search_assets({"text": "蓝黄"})["items"]
        self.assertEqual(found[0]["asset_id"], committed["asset_id"])
        self.assertTrue(Path(self.store.asset_preview(committed["asset_id"])["content_path"]).is_file())

    def test_unresolved_concept_blocks_asset(self):
        staged = self.stage(); proposal = self.store.create_proposal({"operation_id": "proposal-candidate",
            "operation": "asset.create", "queue_item_id": staged["queue_item_id"], "concept_ids": [],
            "candidate_concept_refs": [{"candidate_id": "candidate-x", "proposal_id": "p", "revision": 1,
                                        "proposal_hash": "sha256:" + "1" * 64}], "changes": {"title": "测试"}})
        with self.assertRaises(AVDSError) as error: self.approve(proposal)
        self.assertEqual(error.exception.code, "DEPENDENCY_UNRESOLVED")

    def test_revision_supersedes_old_approval(self):
        staged = self.stage(); first = self.proposal(staged)
        second = self.store.create_proposal({"operation_id": "proposal-2", "proposal_id": first["proposal_id"],
            "revision": 2, "operation": "asset.create", "queue_item_id": staged["queue_item_id"],
            "concept_ids": [], "candidate_concept_refs": [], "changes": {"title": "修订标题"}})
        with self.assertRaises(AVDSError) as error: self.approve(first)
        self.assertEqual(error.exception.code, "STALE_PROPOSAL")
        self.assertEqual(self.approve(second, "review-2")["revision"], 1)

    def test_archive_preserves_original_and_leaves_search(self):
        staged = self.stage(); committed = self.approve(self.proposal(staged)); asset_id = committed["asset_id"]
        archive = self.store.create_proposal({"operation_id": "archive-proposal", "operation": "asset.archive",
            "asset_id": asset_id, "target_revision": 1, "changes": {"state": "archived", "reason": "测试归档"}})
        body = archive["body"]
        result = self.store.review_action({"action": "approve", "proposal_id": archive["proposal_id"], "revision": 1,
            "proposal_hash": archive["proposal_hash"], "file_hash": body["file_hash"], "target_revision": 1,
            "operation_id": "archive-review"}, "/trusted/reviewer")
        self.assertEqual(result["state"], "archived")
        self.assertEqual(self.store.search_assets({"text": "蓝黄"})["items"], [])
        self.assertTrue(Path(self.store.asset_preview(asset_id)["content_path"]).is_file())

    def test_concept_candidate_isolated_then_resolved(self):
        concept = self.store.create_proposal({"operation_id": "concept-proposal", "operation": "concept.create",
            "source": {"note": "test"}, "changes": {"preferred_name": "逆光", "terms": {"zh": "逆光", "en": "backlight"},
            "definition": "光源位于主体后方", "facet": "lighting", "aliases": ["背光"], "relations": []}})
        self.assertEqual(self.store.search_concepts({"text": "逆光"})["items"], [])
        approved = self.store.review_action({"action": "approve", "proposal_id": concept["proposal_id"], "revision": 1,
            "proposal_hash": concept["proposal_hash"], "target_revision": 0, "operation_id": "concept-review"}, "/trusted/reviewer")
        candidate = self.store.candidate_get(concept["candidate_id"])
        self.assertEqual(candidate["resolved_concept_id"], approved["concept_id"])
        self.assertEqual(self.store.search_concepts({"text": "背光"})["items"][0]["concept_id"], approved["concept_id"])
        with self.assertRaises(AVDSError) as error:
            self.store.create_proposal({"operation_id": "duplicate-concept", "operation": "concept.create",
                "changes": {"preferred_name": "背光", "terms": {"zh": "背光", "en": None},
                "definition": "duplicate", "facet": "lighting", "aliases": [], "relations": []}})
        self.assertEqual(error.exception.code, "CONCEPT_DUPLICATE")

    def test_defer_remaining_batch_preserves_resolved_items(self):
        first = self.stage("batch-import-1")
        second = self.store.stage({"operation_id": "batch-import-2", "batch_id": "batch-1", "source_path": str(FIXTURE),
                                   "source": {"original_name": "second.png"}})
        self.approve(self.proposal(first, "batch-proposal-1"), "batch-review-1")
        result = self.store.defer({"operation_id": "batch-defer", "batch_id": "batch-1"}, remaining=True)
        self.assertEqual(result["deferred"], [second["queue_item_id"]])
        self.assertEqual(self.store.queue_get(first["queue_item_id"])["state"], "resolved")
        self.assertEqual(self.store.queue_get(second["queue_item_id"])["state"], "deferred")
        self.assertEqual(result, self.store.defer({"operation_id": "batch-defer", "batch_id": "batch-1"}, remaining=True))

    def test_hierarchy_expansion_and_strict_exclusion(self):
        parent = self.store.create_proposal({"operation_id": "parent-p", "operation": "concept.create", "changes": {
            "preferred_name": "光线", "terms": {"zh": "光线", "en": "light"}, "definition": "光照类别",
            "facet": "lighting", "aliases": [], "relations": []}})
        parent_result = self.store.review_action({"action": "approve", "proposal_id": parent["proposal_id"], "revision": 1,
            "proposal_hash": parent["proposal_hash"], "target_revision": 0, "operation_id": "parent-r"}, "/trusted/reviewer")
        child = self.store.create_proposal({"operation_id": "child-p", "operation": "concept.create", "changes": {
            "preferred_name": "逆光", "terms": {"zh": "逆光", "en": "backlight"}, "definition": "背后光源",
            "facet": "lighting", "aliases": [], "relations": [{"kind": "broader", "concept_id": parent_result["concept_id"]}]}})
        child_result = self.store.review_action({"action": "approve", "proposal_id": child["proposal_id"], "revision": 1,
            "proposal_hash": child["proposal_hash"], "target_revision": 0, "operation_id": "child-r"}, "/trusted/reviewer")
        staged = self.stage("hierarchy-import")
        proposal = self.store.create_proposal({"operation_id": "hierarchy-proposal", "operation": "asset.create",
            "queue_item_id": staged["queue_item_id"], "concept_ids": [child_result["concept_id"]],
            "candidate_concept_refs": [], "changes": {"title": "逆光蓝黄图"}})
        self.approve(proposal, "hierarchy-review")
        strict = {"must": [{"concept_id": parent_result["concept_id"]}], "expand_narrower": False}
        expanded = {"must": [{"concept_id": parent_result["concept_id"]}], "expand_narrower": True}
        excluded = {"must_not": [{"concept_id": child_result["concept_id"]}]}
        self.assertEqual(self.store.search_assets(strict)["items"], [])
        self.assertEqual(len(self.store.search_assets(expanded)["items"]), 1)
        self.assertEqual(self.store.search_assets(excluded)["items"], [])
        self.assertEqual(len(self.store.search_assets({"must": [{"text": "蓝黄"}], "filters": {"orientation": "square"}})["items"]), 1)

    def test_reviewed_knowledge_and_prompt_render(self):
        knowledge = self.store.create_proposal({"operation_id": "knowledge-p", "operation": "knowledge.create", "changes": {
            "title": "逆光观察", "summary": "逆光的观察要点", "content_markdown": "# 逆光\n观察轮廓与主体明暗。", "links": []}})
        self.assertEqual(self.store.knowledge_search({"text": "逆光"})["items"], [])
        knowledge_result = self.store.review_action({"action": "approve", "proposal_id": knowledge["proposal_id"], "revision": 1,
            "proposal_hash": knowledge["proposal_hash"], "target_revision": 0, "operation_id": "knowledge-r"}, "/trusted/reviewer")
        self.assertEqual(self.store.knowledge_search({"text": "逆光"})["items"][0]["knowledge_id"], knowledge_result["knowledge_id"])
        prompt = self.store.create_proposal({"operation_id": "prompt-p", "operation": "prompt.create", "changes": {
            "name": "构图分析", "description": "生成构图观察问题", "template": "分析 {{subject}} 的构图。",
            "variables": {"subject": {"type": "string", "required": True}}, "knowledge_ids": [knowledge_result["knowledge_id"]], "concept_ids": []}})
        prompt_result = self.store.review_action({"action": "approve", "proposal_id": prompt["proposal_id"], "revision": 1,
            "proposal_hash": prompt["proposal_hash"], "target_revision": 0, "operation_id": "prompt-r"}, "/trusted/reviewer")
        rendered = self.store.prompt_render({"prompt_id": prompt_result["prompt_id"], "variables": {"subject": "人物"}})
        self.assertEqual(rendered["rendered"], "分析 人物 的构图。")
        self.assertEqual(rendered["knowledge"][0]["knowledge_id"], knowledge_result["knowledge_id"])
        update = self.store.create_proposal({"operation_id": "knowledge-update-p", "operation": "knowledge.update",
            "knowledge_id": knowledge_result["knowledge_id"], "target_revision": 1, "changes": {
                "title": "逆光观察修订", "summary": "补充曝光关系", "content_markdown": "# 逆光\n先看轮廓，再看曝光。", "links": []}})
        updated = self.store.review_action({"action": "approve", "proposal_id": update["proposal_id"], "revision": 1,
            "proposal_hash": update["proposal_hash"], "target_revision": 1, "operation_id": "knowledge-update-r"}, "/trusted/reviewer")
        self.assertEqual(updated["revision"], 2)
        archive = self.store.create_proposal({"operation_id": "prompt-archive-p", "operation": "prompt.archive",
            "prompt_id": prompt_result["prompt_id"], "target_revision": 1, "changes": {"state": "archived", "reason": "测试"}})
        archived = self.store.review_action({"action": "approve", "proposal_id": archive["proposal_id"], "revision": 1,
            "proposal_hash": archive["proposal_hash"], "target_revision": 1, "operation_id": "prompt-archive-r"}, "/trusted/reviewer")
        self.assertEqual(archived["state"], "archived")
        self.assertEqual(self.store.prompt_list({})["items"], [])

    def test_native_visual_similarity_is_derived_and_local(self):
        first = self.stage("visual-import-1"); first_asset = self.approve(self.proposal(first, "visual-p-1"), "visual-r-1")["asset_id"]
        second = self.store.stage({"operation_id": "visual-import-2", "batch_id": "batch-1", "source_path": str(FIXTURE), "source": {"original_name": "same.png"}})
        second_asset = self.approve(self.proposal(second, "visual-p-2"), "visual-r-2")["asset_id"]
        try:
            result = self.store.visual_search({"asset_id": first_asset, "limit": 5})
        except AVDSError as error:
            if error.code == "ASSET_UNAVAILABLE": self.skipTest("Apple Vision 在 Codex 沙盒内不可创建像素缓冲；安装后 Core 在沙盒外运行")
            raise
        self.assertEqual(result["items"][0]["asset_id"], second_asset)
        self.assertLess(result["items"][0]["distance"], 0.00001)


if __name__ == "__main__":
    unittest.main()
