"""
Main entry point for config migrator.

Usage: python -m config_migrator <nstf_file> <etf_file> <newtf_file>
"""

from config_migrator.cli.commands import migrate


def main():
    """Main entry point for the config migrator CLI."""
    migrate()


if __name__ == "__main__":
    main()
