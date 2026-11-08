"""JSON diagnostics on stdout, including third-party warnings."""
import json
import logging
import sys
import time


def log(msg: str, **fields: object) -> None:
    print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "logger": "rahbar.indexer", "msg": msg, **fields}), flush=True)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"logger": record.name, "level": record.levelname,
                           "msg": record.getMessage()})


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(handlers=[handler], level=logging.WARNING, force=True)
    logging.captureWarnings(True)
