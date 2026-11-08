import contextlib
import io
import unittest

from avds.cli import main
from avds.commands import REMOTE_COMMAND_DESCRIPTIONS
from avds.server import COMMANDS


class CliHelpTests(unittest.TestCase):
    def test_help_lists_parameters_commands_and_purposes(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        help_text = output.getvalue()
        for expected in (
            "-h, --help",
            "--vault PATH",
            "--json-file PATH",
            "serve",
            "启动同时承载 API 与 WebUI",
            "review.action",
            "绑定提案版本和哈希",
        ):
            self.assertIn(expected, help_text)

    def test_short_help_and_server_command_list_share_catalog(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["-h"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(COMMANDS, tuple(REMOTE_COMMAND_DESCRIPTIONS))


if __name__ == "__main__":
    unittest.main()
