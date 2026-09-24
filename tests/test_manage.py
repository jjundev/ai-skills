import sys
import unittest
from unittest.mock import patch
from script.manage import main, run_tests


class TestManage(unittest.TestCase):
    @patch("script.check.main")
    def test_route_check(self, mock_check):
        mock_check.return_value = 0
        code = main(["check", "--json"])
        self.assertEqual(code, 0)
        mock_check.assert_called_once_with(["--json"])

    @patch("script.check.main")
    def test_route_check_with_target(self, mock_check):
        mock_check.return_value = 0
        code = main(["check", "--json", "--target", "superpowers"])
        self.assertEqual(code, 0)
        mock_check.assert_called_once_with(["--json", "--target", "superpowers"])

    @patch("script.sync.main")
    def test_route_sync(self, mock_sync):
        mock_sync.return_value = 0
        code = main(["sync", "--target", "ecc", "--no-commit"])
        self.assertEqual(code, 0)
        mock_sync.assert_called_once_with(["--target", "ecc", "--no-commit"])

    @patch("script.sync.main")
    def test_route_sync_default_args(self, mock_sync):
        mock_sync.return_value = 0
        code = main(["sync"])
        self.assertEqual(code, 0)
        mock_sync.assert_called_once_with([])

    @patch("script.link.main")
    def test_route_link(self, mock_link):
        mock_link.return_value = 0
        code = main(["link", "--dry-run"])
        self.assertEqual(code, 0)
        mock_link.assert_called_once_with(["--dry-run"])

    @patch("script.link.main")
    def test_route_link_no_args(self, mock_link):
        mock_link.return_value = 0
        code = main(["link"])
        self.assertEqual(code, 0)
        mock_link.assert_called_once_with([])

    @patch("unittest.main")
    def test_route_test(self, mock_unittest):
        # mock unittest.main exit
        mock_unittest.side_effect = SystemExit(0)
        code = main(["test"])
        self.assertEqual(code, 0)

    @patch("unittest.main")
    def test_route_test_failure(self, mock_unittest):
        mock_unittest.side_effect = SystemExit(1)
        code = main(["test"])
        self.assertEqual(code, 1)

    @patch("sys.argv", ["manage.py", "link", "--dry-run"])
    @patch("script.link.main")
    def test_default_argv_from_sys(self, mock_link):
        mock_link.return_value = 0
        code = main()
        self.assertEqual(code, 0)
        mock_link.assert_called_once_with(["--dry-run"])

    def test_unknown_subcommand(self):
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                main(["unknown-command"])


if __name__ == "__main__":
    unittest.main()
