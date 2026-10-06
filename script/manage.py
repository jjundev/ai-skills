from pathlib import Path
import argparse
import sys
import unittest

# Ensure repo root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from script import check, check_plugins, sync, link
from script.common import Color


def run_tests(extra_args: list[str] | None = None) -> int:
    print(Color.bold("=== Running AI Skills Test Suite ==="))
    argv = ["manage.py test"]
    if extra_args:
        argv.extend(extra_args)
    else:
        argv.extend(["discover", "-s", "tests"])
    try:
        unittest.main(module=None, argv=argv)
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="AI Skills unified management toolchain (check, sync, link, test).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to execute")

    # check
    check_parser = subparsers.add_parser("check", help="Check upstream repositories for updates")
    check_parser.add_argument("--json", action="store_true", help="Output JSON format")
    check_parser.add_argument("--target", help="Specific upstream target to check")

    # check-plugins
    check_plugins_parser = subparsers.add_parser(
        "check-plugins",
        help="Check update status for all AI plugins and skills",
    )
    check_plugins_parser.add_argument("--json", action="store_true", help="Output JSON format")
    check_plugins_parser.add_argument("--skills-only", action="store_true", help="Check only AI skills upstreams")
    check_plugins_parser.add_argument("--cli-only", action="store_true", help="Check only CLI plugins")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Sync curated skills from upstream repositories")
    sync_parser.add_argument("--target", help="Specific upstream target to sync")
    sync_parser.add_argument("--no-commit", action="store_true", help="Skip git commit after copying")

    # link
    link_parser = subparsers.add_parser("link", help="Link managed skills to global host directories")
    link_parser.add_argument("--dry-run", action="store_true", help="Dry run without filesystem changes")

    # test
    subparsers.add_parser("test", help="Run the test suite")

    if argv is None:
        argv = sys.argv[1:]

    args, unknown = parser.parse_known_args(argv)

    if args.command == "check":
        forward_args = []
        if args.json:
            forward_args.append("--json")
        if args.target:
            forward_args.extend(["--target", args.target])
        forward_args.extend(unknown)
        return check.main(forward_args)

    elif args.command == "check-plugins":
        forward_args = []
        if args.json:
            forward_args.append("--json")
        if args.skills_only:
            forward_args.append("--skills-only")
        if args.cli_only:
            forward_args.append("--cli-only")
        forward_args.extend(unknown)
        return check_plugins.main(forward_args)

    elif args.command == "sync":
        forward_args = []
        if args.target:
            forward_args.extend(["--target", args.target])
        if args.no_commit:
            forward_args.append("--no-commit")
        forward_args.extend(unknown)
        return sync.main(forward_args)

    elif args.command == "link":
        forward_args = []
        if args.dry_run:
            forward_args.append("--dry-run")
        forward_args.extend(unknown)
        return link.main(forward_args)

    elif args.command == "test":
        return run_tests(unknown)

    return 1


if __name__ == "__main__":
    sys.exit(main())
