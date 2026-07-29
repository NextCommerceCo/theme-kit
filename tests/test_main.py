import unittest
from unittest.mock import MagicMock, patch

from ntk.__main__ import main
from ntk.exceptions import NTKNotFoundError


class TestMain(unittest.TestCase):
    @patch('ntk.__main__.Parser', autospec=True)
    def test_main_exits_1_on_ntk_error(self, mock_parser):
        args = MagicMock()
        args.func.side_effect = NTKNotFoundError(
            'Not found: http://simple.com/api/admin/themes/6/templates/ — check the store URL and theme id.')
        mock_parser.return_value.create_parser.return_value.parse_args.return_value = args

        with self.assertRaises(SystemExit) as exit_context:
            with self.assertLogs(level='ERROR') as log:
                main()

        self.assertEqual(exit_context.exception.code, 1)
        self.assertTrue(any('Not found' in line for line in log.output))

    @patch('ntk.__main__.Parser', autospec=True)
    def test_main_prints_help_hint_on_attribute_error(self, mock_parser):
        args = MagicMock()
        args.func.side_effect = AttributeError()
        mock_parser.return_value.create_parser.return_value.parse_args.return_value = args

        # No command supplied — should print the help hint and not raise.
        main()

    @patch('ntk.__main__.Parser', autospec=True)
    def test_main_logs_theme_kit_version(self, mock_parser):
        args = MagicMock()
        args.func.return_value = None
        mock_parser.return_value.create_parser.return_value.parse_args.return_value = args

        with self.assertLogs(level='INFO') as log:
            main()

        self.assertTrue(any('NEXT Theme Kit version' in line for line in log.output))


if __name__ == '__main__':
    unittest.main()
