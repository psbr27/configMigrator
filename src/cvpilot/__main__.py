"""
Main entry point for cvpilot.

Usage: python -m cvpilot <command> [options]
"""

from cvpilot.cli.commands import cli


def main():
    """Main entry point for the cvpilot CLI."""
    cli()


if __name__ == "__main__":
    main()
