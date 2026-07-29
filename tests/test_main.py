import unittest
import json
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import MagicMock, patch

from ntk.__main__ import main


class TestMain(unittest.TestCase):
    @patch('ntk.__main__.Parser', autospec=True)
    def test_main_exits_1_for_failed_command_result(self, mock_parser):
        args = MagicMock()
        args.func.return_value = {'ok': False}
        mock_parser.return_value.create_parser.return_value.parse_args.return_value = args
        with self.assertRaises(SystemExit) as exit_context:
            main()
        self.assertEqual(exit_context.exception.code, 1)

    @patch('ntk.__main__.Parser', autospec=True)
    def test_main_writes_one_json_error_for_machine_mode(self, mock_parser):
        args = MagicMock()
        args.json = True
        args.quiet = False
        args.no_progress = False
        args.command = 'validate'
        args.func.side_effect = TypeError('invalid input')
        mock_parser.return_value.create_parser.return_value.parse_args.return_value = args
        stdout = StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stdout(stdout):
                main()
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['command'], 'validate')
        self.assertEqual(payload['error']['type'], 'TypeError')

if __name__ == '__main__':
    unittest.main()
