"""
Main entry point for cvpilot.

Usage: python -m cvpilot <nsprev_file> <engprev_file> <engnew_file>
"""

from cvpilot.cli.commands import migrate


def main():
    """Main entry point for the cvpilot CLI."""
    migrate()


if __name__ == "__main__":
    main()
