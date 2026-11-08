import argparse
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from avds.cli import request
from avds.config import Config, load_config
from avds.platform import inspect_native, visual_capability
from avds.server import Server
from test_store import write_fixture


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="avds-http-")
        self.config = Config(vault=str(Path(self.temp.name) / "vault"), port=0, visual_provider="none")
        self.server = Server(self.config)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01})
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.thread.join(3); self.server.server_close()
        self.temp.cleanup()

    def call(self, command, **payload):
        return request(self.config, {"command": command, **payload})

    def test_single_service_and_configured_port(self):
        self.assertGreater(self.server.server_port, 0)
        service = self.call("status")["result"]["service"]
        self.assertEqual(service["url"], self.server.url)
        self.assertEqual(service["version"], "2.0.0")
        with self.assertRaisesRegex(ValueError, "同一 Vault"):
            Server(Config(vault=self.config.vault, port=0))
        other = Server(Config(vault=str(Path(self.temp.name) / "other"), port=0))
        self.assertNotEqual(other.server_port, self.server.server_port)
        other.server_close()

    def test_both_entries_share_review_and_search_isolation(self):
        fixture = Path(self.temp.name) / "sample.png"; write_fixture(fixture)
        staged = self.call("import.stage", source_path=str(fixture), operation_id="i")["result"]
        proposal = self.call("proposal.create", operation_id="p", operation="asset.create",
            queue_item_id=staged["queue_item_id"], changes={"title": "已审蓝黄"}, concept_ids=[])["result"]
        self.assertEqual(self.call("search.assets")["result"]["items"], [])
        review = {"action": "approve", "proposal_id": proposal["proposal_id"], "revision": proposal["revision"],
            "proposal_hash": proposal["proposal_hash"], "target_revision": 0, "file_hash": staged["file_hash"], "operation_id": "r"}
        self.assertEqual(self.call("review.action", **review)["error"]["code"], "CONFIRMATION_REQUIRED")
        review["confirmed"] = True
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("POST", "/api/command", json.dumps({"command": "review.action", **review}), {
            "Content-Type": "application/json", "Cookie": "avds_session=" + self.server.token, "Origin": self.server.url})
        response = connection.getresponse(); value = json.load(response); connection.close()
        self.assertTrue(value["ok"], value)
        self.assertEqual(len(self.call("search.assets")["result"]["items"]), 1)
        self.assertEqual(self.call("review.action", **review), value)
        self.assertFalse(self.call("status")["result"]["service"]["review_identity_isolated"])

    def test_cross_origin_and_host_denied(self):
        for headers in ({}, {"Cookie": "avds_session=" + self.server.token, "Origin": "https://example.org"},
                        {"Authorization": "Bearer " + self.server.token, "Host": "evil.example"}):
            connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
            connection.request("POST", "/api/command", '{"command":"status"}', headers)
            response = connection.getresponse(); response.read()
            self.assertIn(response.status, {401, 403}); connection.close()

    def test_commit_failure_rolls_back_approval(self):
        proposal = self.call("proposal.create", operation_id="kp", operation="knowledge.create",
            changes={"title": "草案", "content_markdown": "仅草案", "links": []})["result"]
        with patch.object(self.server.store, "_commit", side_effect=ValueError("test failure")):
            result = self.call("review.action", operation_id="kr", action="approve", confirmed=True,
                proposal_id=proposal["proposal_id"], revision=1, proposal_hash=proposal["proposal_hash"], target_revision=0)
        self.assertFalse(result["ok"])
        self.assertEqual(self.call("proposal.get", proposal_id=proposal["proposal_id"])["result"]["state"], "in_review")
        self.assertEqual(self.call("knowledge.search")["result"]["items"], [])

    def test_browser_upload_is_persistent(self):
        fixture = Path(self.temp.name) / "sample.png"; write_fixture(fixture)
        values = []
        for _ in range(2):
            connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
            connection.request("POST", "/api/import", fixture.read_bytes(), {"Cookie": "avds_session=" + self.server.token,
                "Origin": self.server.url, "X-File-Name": "sample.png", "X-Batch-Id": "browser-import",
                "X-Operation-Id": "browser-import-retry"})
            response = connection.getresponse(); values.append(json.load(response)); connection.close()
        self.assertTrue(values[0]["ok"], values[0])
        self.assertEqual(values[0], values[1])
        result = self.call("queue.get", queue_item_id=values[0]["result"]["queue_item_id"])["result"]
        self.assertEqual(result["state"], "pending")
        self.assertEqual(list((self.config.root / "staging/.uploads").iterdir()), [])

    def test_content_revision_keeps_identity_and_rejects_invalid_draft(self):
        first = self.call("proposal.create", operation_id="first", operation="knowledge.create",
            changes={"title": "知识一", "content_markdown": "正文一", "links": []})["result"]
        second = self.call("proposal.revise", operation_id="second", operation="knowledge.create",
            proposal_id=first["proposal_id"], revision=2,
            changes={"title": "知识二", "content_markdown": "正文二", "links": []})["result"]
        self.assertEqual(first["knowledge_id"], second["knowledge_id"])
        invalid = self.call("proposal.revise", operation_id="invalid", operation="knowledge.create",
            proposal_id=first["proposal_id"], revision=3, uncertainties=[123],
            changes={"title": "知识三", "content_markdown": "正文三", "links": []})
        self.assertFalse(invalid["ok"])
        self.assertEqual(self.call("proposal.get", proposal_id=first["proposal_id"])["result"]["state"], "in_review")

    def test_revision_cannot_change_asset_or_content_target(self):
        fixture = Path(self.temp.name) / "sample.png"; write_fixture(fixture)
        staged = [self.call("import.stage", source_path=str(fixture), operation_id=f"i-{index}")["result"] for index in range(2)]
        first = self.call("proposal.create", operation_id="asset-first", operation="asset.create",
            queue_item_id=staged[0]["queue_item_id"], changes={"title": "第一张"}, concept_ids=[])["result"]
        moved = self.call("proposal.revise", operation_id="asset-moved", operation="asset.create",
            proposal_id=first["proposal_id"], revision=2, queue_item_id=staged[1]["queue_item_id"],
            changes={"title": "错误换目标"}, concept_ids=[])
        self.assertEqual(moved["error"]["code"], "VALIDATION_FAILED")
        self.assertEqual(self.call("proposal.get", proposal_id=first["proposal_id"])["result"]["revision"], 1)

        knowledge_ids = []
        for index in range(2):
            proposal = self.call("proposal.create", operation_id=f"knowledge-{index}", operation="knowledge.create",
                changes={"title": f"知识 {index}", "content_markdown": "正文", "links": []})["result"]
            approved = self.call("review.action", operation_id=f"knowledge-review-{index}", action="approve", confirmed=True,
                proposal_id=proposal["proposal_id"], revision=1, proposal_hash=proposal["proposal_hash"], target_revision=0)
            self.assertTrue(approved["ok"], approved)
            knowledge_ids.append(proposal["knowledge_id"])
        update = self.call("proposal.create", operation_id="knowledge-update", operation="knowledge.update",
            knowledge_id=knowledge_ids[0], target_revision=1,
            changes={"title": "知识一修订", "content_markdown": "新正文", "links": []})["result"]
        moved_content = self.call("proposal.revise", operation_id="knowledge-moved", operation="knowledge.update",
            proposal_id=update["proposal_id"], revision=2, knowledge_id=knowledge_ids[1], target_revision=1,
            changes={"title": "错误换知识", "content_markdown": "错误正文", "links": []})
        self.assertEqual(moved_content["error"]["code"], "VALIDATION_FAILED")
        self.assertEqual(self.call("proposal.get", proposal_id=update["proposal_id"])["result"]["revision"], 1)


class ConfigPlatformTests(unittest.TestCase):
    def test_configuration_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"port": 1234, "vault": directory}), encoding="utf-8")
            with patch.dict(os.environ, {"AVDS_PORT": "2345"}, clear=True):
                args = argparse.Namespace(config=str(path), port=3456)
                self.assertEqual(load_config(args).port, 3456)
                args.port = None
                self.assertEqual(load_config(args).port, 2345)
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(load_config(args).port, 1234)
                args.host = "0.0.0.0"
                with self.assertRaises(ValueError): load_config(args)

    def test_windows_does_not_invoke_apple_tools(self):
        with patch("avds.platform.platform.system", return_value="Windows"):
            self.assertFalse(visual_capability("auto", Path(__file__))["available"])
            fake = type("Result", (), {"returncode": 0, "stdout": '{"format":"png","width":64,"height":64}'})()
            with patch("avds.platform.subprocess.run", return_value=fake) as run:
                self.assertEqual(inspect_native(Path("C:/Pictures/image.png")), ("png", 64, 64))
                self.assertEqual(run.call_args.args[0][0], "powershell.exe")
                self.assertNotIn("C:/Pictures/image.png", run.call_args.args[0][-1])
                self.assertEqual(run.call_args.kwargs["env"]["AVDS_INSPECT_PATH"], str(Path("C:/Pictures/image.png")))
