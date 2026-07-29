import json
import logging
import sys


SCHEMA_VERSION = "1"


class Output:
    """Keep human diagnostics on stderr and machine results on stdout."""

    def __init__(self):
        self.json = False
        self.quiet = False
        self.no_progress = False

    def configure(self, parser):
        self.json = getattr(parser, "json", False) is True
        self.quiet = getattr(parser, "quiet", False) is True
        self.no_progress = getattr(parser, "no_progress", False) is True
        if self.quiet or self.json:
            logging.getLogger().setLevel(logging.WARNING)
        else:
            logging.getLogger().setLevel(logging.INFO)

    @property
    def progress_enabled(self):
        return not (self.json or self.quiet or self.no_progress) and sys.stderr.isatty()

    def result(self, command, ok=True, **data):
        payload = {
            "schema_version": SCHEMA_VERSION,
            "command": command,
            "ok": bool(ok),
            **data,
        }
        if self.json:
            print(json.dumps(payload, sort_keys=True))
        return payload

    def error(self, command, message, error_type="error"):
        return self.result(
            command,
            ok=False,
            error={"type": error_type, "message": str(message)},
        )
