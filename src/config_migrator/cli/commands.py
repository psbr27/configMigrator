"""
CLI commands for config migrator.

Implements the main command-line interface following the flowchart steps.
"""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from config_migrator.core.merger import ConfigMerger
from config_migrator.core.parser import YAMLParser
from config_migrator.utils.logging import setup_logging


def _show_integrated_summary(
    console: Console,
    nstf_data: dict,
    etf_data: dict,
    newtf_data: dict,
    final_config: dict,
):
    """Show detailed merge summary for integrated workflow."""
    console.print("\n[bold blue]Complete Workflow Summary[/bold blue]")

    # Count keys at each level
    def count_keys(data: dict) -> int:
        count = 0
        for value in data.values():
            if isinstance(value, dict):
                count += count_keys(value)
            else:
                count += 1
        return count

    # Stage 1 stats
    etf_keys = count_keys(etf_data)
    nstf_overrides = count_keys(nstf_data)
    stage1_keys = count_keys(ConfigMerger.merge_configs_stage1(nstf_data, etf_data))

    # Stage 2 stats
    newtf_keys = count_keys(newtf_data)
    modifications = 0
    for key in nstf_data:
        if key in newtf_data:
            modifications += 1

    final_keys = count_keys(final_config)

    # Create summary table
    table = Table(title="Complete Migration Workflow Statistics")
    table.add_column("Stage", style="cyan")
    table.add_column("Metric", style="magenta")
    table.add_column("Count", style="green")

    table.add_row("Stage 1", "ETF Base Keys", str(etf_keys))
    table.add_row("Stage 1", "NSTF Overrides", str(nstf_overrides))
    table.add_row("Stage 1", "Stage 1 Result", str(stage1_keys))
    table.add_row("Stage 2", "NEWTF Base Keys", str(newtf_keys))
    table.add_row("Stage 2", "Modifications", str(modifications))
    table.add_row("Final", "Final Merged Keys", str(final_keys))

    console.print(table)

    # Show precedence explanation
    console.print("\n[bold blue]Complete Workflow Precedence Rules:[/bold blue]")
    console.print("Stage 1:")
    console.print("  1. ETF (Engineering Template) - Base template")
    console.print(
        "  2. NSTF (Namespace Template) - Site-specific values (highest precedence)"
    )
    console.print("Stage 2:")
    console.print("  3. NEWTF (New Template) - New features and updates")
    console.print(
        "  4. Diff File (NSTF precedence) - Site-specific values override NEWTF"
    )
    console.print("  5. New Keys - Include new keys from either file")
    console.print("  6. Deletions - Ignore deletions (preserve all keys)")


@click.command()
@click.argument("nstf_file", type=click.Path(exists=True, path_type=Path))
@click.argument("etf_file", type=click.Path(exists=True, path_type=Path))
@click.argument("newtf_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    default="migrated_new_eng_template.yml",
    help="Output file name (default: migrated_new_eng_template.yml)",
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--debug", is_flag=True, help="Debug output")
@click.option("--summary", is_flag=True, help="Show merge summary")
def migrate(
    nstf_file: Path,
    etf_file: Path,
    newtf_file: Path,
    output: str,
    verbose: bool,
    debug: bool,
    summary: bool,
):
    """
    Config Migration Tool - Complete Workflow: Stage 1 + Stage 2.

    Runs both stages in sequence:
    1. Stage 1: Merge NSTF and ETF files
    2. Stage 2: Merge result with NEWTF file

    Final output: migrated_new_eng_template.yml
    """
    # Setup logging
    log_level = "DEBUG" if debug else "INFO" if verbose else "WARNING"
    logger = setup_logging(log_level)
    console = Console()

    try:
        # Initialize YAML parser
        parser = YAMLParser()

        # Validate all three files
        logger.info("Step 1: Validating all input files")

        file_paths = [str(nstf_file), str(etf_file), str(newtf_file)]
        is_valid, error_msg = parser.validate_all_files(file_paths)

        if not is_valid:
            logger.error(f"Validation failed: {error_msg}")
            console.print(f"[bold red]Validation failed: {error_msg}[/bold red]")
            raise click.Abort()

        logger.info("All YAML files have valid syntax")

        # Load all files
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Processing files...", total=None)

            progress.update(task, description="Loading NSTF file...")
            logger.debug(f"Loading NSTF file: {nstf_file}")
            nstf_data = parser.load_yaml_file(str(nstf_file))

            progress.update(task, description="Loading ETF file...")
            logger.debug(f"Loading ETF file: {etf_file}")
            etf_data = parser.load_yaml_file(str(etf_file))

            progress.update(task, description="Loading NEWTF file...")
            logger.debug(f"Loading NEWTF file: {newtf_file}")
            newtf_data = parser.load_yaml_file(str(newtf_file))

        # STAGE 1: Merge NSTF and ETF
        logger.info("Stage 1: Merging NSTF and ETF")

        progress.update(task, description="Stage 1: Merging NSTF and ETF...")
        diff_data = ConfigMerger.merge_configs_stage1(nstf_data, etf_data)

        logger.info("Stage 1 completed: diff_nstf_etf.yaml created")

        # STAGE 2: Merge diff with NEWTF
        logger.info("Stage 2: Merging with NEWTF")

        progress.update(task, description="Stage 2: Merging with NEWTF...")
        final_config = ConfigMerger.merge_configs_stage2(diff_data, newtf_data)

        # Save final output
        progress.update(task, description=f"Saving final output to {output}...")
        logger.debug(f"Saving final configuration to: {output}")
        parser.save_yaml_file(final_config, output)

        # Success message
        logger.info("Complete Migration Workflow Successful")
        console.print(
            Panel.fit(
                f"[bold green]Complete Migration Workflow Successful![/bold green]\n"
                f"Stage 1: NSTF + ETF → diff_nstf_etf.yaml\n"
                f"Stage 2: diff + NEWTF → {output}",
                title="Config Migration Tool - Complete Workflow",
                border_style="green",
            )
        )

        # Show summary if requested
        if summary:
            _show_integrated_summary(
                console, nstf_data, etf_data, newtf_data, final_config
            )

        logger.info("Complete workflow finished successfully")

    except Exception as e:
        logger.error(f"Error: {e}")
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise click.Abort()


@click.group()
def cli():
    """Config Migration Tool - YAML Configuration Merger with NSTF Precedence."""


# Add the migrate command to the CLI group
cli.add_command(migrate)
