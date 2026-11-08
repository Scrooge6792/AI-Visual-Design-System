import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from avds.cli import main as full_main
from avds.commands import REMOTE_COMMAND_DESCRIPTIONS
from avds.server import COMMANDS
from avds.user_cli import main as user_main


class CliHelpTests(unittest.TestCase):
    def capture_help(self, main, arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(arguments)
        self.assertEqual(raised.exception.code, 0)
        return output.getvalue()

    def test_user_help_only_lists_common_commands(self):
        help_text = self.capture_help(user_main, ["--help"])
        for expected in ("-h, --help", "--version", "serve", "status", "config", "查看某个命令的参数", "avds serve -h"):
            self.assertIn(expected, help_text)
        for internal in ("import.stage", "review.action", "--json-file"):
            self.assertNotIn(internal, help_text)

    def test_config_help_lists_show_get_and_set(self):
        help_text = self.capture_help(user_main, ["config", "--help"])
        for expected in ("show", "get", "set", "打印或修改当前用户的应用配置", "avds config set -h"):
            self.assertIn(expected, help_text)

    def test_internal_help_and_server_share_full_command_catalog(self):
        help_text = self.capture_help(full_main, ["-h"])
        self.assertIn("review.action", help_text)
        self.assertIn("绑定提案版本和哈希", help_text)
        self.assertEqual(COMMANDS, tuple(REMOTE_COMMAND_DESCRIPTIONS))

    def test_user_config_set_get_and_show(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            with mock.patch.dict(os.environ, {"AVDS_CONFIG": str(config_path)}, clear=False):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    user_main(["config", "set", "port", "8877"])
                self.assertEqual(json.loads(output.getvalue())["result"]["value"], 8877)

                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    user_main(["config", "get", "port"])
                self.assertEqual(json.loads(output.getvalue())["result"]["value"], 8877)

                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    user_main(["config", "show"])
                shown = json.loads(output.getvalue())["result"]
                self.assertEqual(shown["values"]["port"], 8877)
                self.assertEqual(shown["config_file"], str(config_path))

    def test_user_shortcuts_forward_to_full_cli(self):
        with mock.patch("avds.user_cli.full_main") as forwarded:
            user_main(["serve", "--open"])
            forwarded.assert_called_once_with(["serve", "--open"])
        with mock.patch("avds.user_cli.full_main") as forwarded:
            user_main(["status"])
            forwarded.assert_called_once_with(["status"])


if __name__ == "__main__":
    unittest.main()
