from __future__ import annotations

import sys
from typing import List


def _usage() -> int:
    print("usage: python -m swengineer <command> [args]")
    print("commands:")
    print("  parity-probe    run python -I import+schema parity probe and emit JSON report")
    return 2


def main(argv: List[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return _usage()

    cmd = args[0]
    rest = args[1:]

    if cmd == "parity-probe":
        from swengineer.cli_parity_probe import main as _pp
        return int(_pp(rest))

    return _usage()


if __name__ == "__main__":
    raise SystemExit(main())

