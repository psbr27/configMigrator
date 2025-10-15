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

from cvpilot.core.merger import ConfigMerger
from cvpilot.core.parser import YAMLParser
from cvpilot.core.analyzer import ConflictAnalyzer, generate_rulebook_from_analysis
from cvpilot.core.transformer import PathTransformationDetector
from cvpilot.utils.logging import setup_logging


def _show_integrated_summary(
    console: Console,
    nsprev_data: dict,
    engprev_data: dict,
    engnew_data: dict,
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
    engprev_keys = count_keys(engprev_data)
    nsprev_overrides = count_keys(nsprev_data)
    stage1_keys = count_keys(
        ConfigMerger.merge_configs_stage1(nsprev_data, engprev_data)
    )

    # Stage 2 stats
    engnew_keys = count_keys(engnew_data)
    modifications = 0
    for key in nsprev_data:
        if key in engnew_data:
            modifications += 1

    final_keys = count_keys(final_config)

    # Create summary table
    table = Table(title="Complete Migration Workflow Statistics")
    table.add_column("Stage", style="cyan")
    table.add_column("Metric", style="magenta")
    table.add_column("Count", style="green")

    table.add_row("Stage 1", "ENGPREV Base Keys", str(engprev_keys))
    table.add_row("Stage 1", "NSPREV Overrides", str(nsprev_overrides))
    table.add_row("Stage 1", "Stage 1 Result", str(stage1_keys))
    table.add_row("Stage 2", "ENGNEW Base Keys", str(engnew_keys))
    table.add_row("Stage 2", "Modifications", str(modifications))
    table.add_row("Final", "Final Merged Keys", str(final_keys))

    console.print(table)

    # Show precedence explanation
    console.print("\n[bold blue]Complete Workflow Precedence Rules:[/bold blue]")
    console.print("Stage 1:")
    console.print("  1. ENGPREV (Engineering Previous) - Base template")
    console.print(
        "  2. NSPREV (Namespace Previous) - Site-specific values (highest precedence)"
    )
    console.print("Stage 2:")
    console.print("  3. ENGNEW (Engineering New) - New features and updates")
    console.print(
        "  4. Diff File (NSPREV precedence) - Site-specific values override ENGNEW"
    )
    console.print("  5. New Keys - Include new keys from either file")
    console.print("  6. Deletions - Ignore deletions (preserve all keys)")


def _generate_output_filename(nsprev_file: Path, engnew_data: dict) -> str:
    """
    Generate output filename based on nsprev filename + engnew version.

    Format: {nsprev_basename_without_version}_{engnew_version}.yaml
    Example: rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.200.yaml
    """
    # Get the base name without extension
    nsprev_stem = nsprev_file.stem

    # Extract version from engnew
    engnew_version = engnew_data.get("global", {}).get("image", {}).get("tag")
    if not engnew_version:
        # Fallback: try to get version from global.version
        engnew_version = engnew_data.get("global", {}).get("version")
    if not engnew_version:
        # If still no version found, use 'unknown'
        engnew_version = "unknown"

    # Remove version from nsprev filename if it exists
    # Pattern: remove _X.Y.Z from the end
    import re

    base_name = re.sub(r"_\d+\.\d+\.\d+$", "", nsprev_stem)

    # Generate new filename
    return f"{base_name}_{engnew_version}.yaml"


def _display_transformation_report(
    console: Console,
    transformations: list,
) -> None:
    """
    Display detected transformations in a formatted table.
    
    Args:
        console: Rich console instance
        transformations: List of TransformationRecord objects
    """
    console.print("\n")
    console.print(Panel.fit(
        f"[bold yellow]Stage 3: Path Transformation Detection[/bold yellow]\n"
        f"Found {len(transformations)} potential structural transformation(s)",
        border_style="yellow"
    ))
    
    # Create table
    table = Table(
        title="Detected Path Transformations",
        show_header=True,
        header_style="bold cyan"
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Old Path", style="red", overflow="fold")
    table.add_column("New Path", style="green", overflow="fold")
    table.add_column("Value", style="yellow", overflow="fold", max_width=30)
    table.add_column("Recommendation", style="magenta")
    table.add_column("Confidence", style="blue")
    
    for i, t in enumerate(transformations, 1):
        # Truncate value if too long
        value_str = str(t.value)
        if len(value_str) > 30:
            value_str = value_str[:27] + "..."
        
        table.add_row(
            str(i),
            t.old_path,
            t.new_path,
            value_str,
            t.recommendation,
            t.confidence
        )
    
    console.print(table)
    console.print()


def _prompt_user_selection(
    console: Console,
    transformations: list,
    auto_apply: bool = False,
) -> list:
    """
    Prompt user to select which transformations to apply.
    
    Args:
        console: Rich console instance
        transformations: List of TransformationRecord objects
        auto_apply: If True, automatically apply high-confidence transformations
        
    Returns:
        List of selected TransformationRecord objects
    """
    # Auto-apply mode for non-interactive environments (tests)
    if auto_apply:
        selected = [
            t for t in transformations
            if t.recommendation == 'move' and t.confidence == 'high'
        ]
        console.print(f"[green]Auto-applying {len(selected)} high-confidence transformations[/green]")
        return selected
    
    console.print("[bold blue]Select transformations to apply:[/bold blue]")
    console.print("Options:")
    console.print("  [green]a[/green] - Apply all high-confidence 'move' recommendations")
    console.print("  [yellow]n[/yellow] - Skip all transformations (manual review)")
    console.print("  [cyan]s[/cyan] - Select specific transformations (enter numbers separated by commas)")
    console.print()
    
    try:
        choice = console.input("[bold]Your choice [a/n/s]:[/bold] ").strip().lower()
    except EOFError:
        # Handle non-interactive environments gracefully
        console.print("[yellow]Non-interactive environment detected - auto-applying high-confidence transformations[/yellow]")
        choice = 'a'
    
    if choice == 'a':
        # Apply all high-confidence move recommendations
        selected = [
            t for t in transformations
            if t.recommendation == 'move' and t.confidence == 'high'
        ]
        console.print(f"[green]Applying {len(selected)} high-confidence transformations[/green]")
        return selected
    
    elif choice == 'n':
        console.print("[yellow]Skipping all transformations - manual review recommended[/yellow]")
        return []
    
    elif choice == 's':
        # Let user select specific transformations
        console.print("\nEnter transformation numbers (comma-separated, e.g., 1,2,5):")
        selection = console.input("[bold]Numbers:[/bold] ").strip()
        
        try:
            # Parse selection
            indices = [int(x.strip()) for x in selection.split(',') if x.strip()]
            selected = []
            
            for idx in indices:
                if 1 <= idx <= len(transformations):
                    selected.append(transformations[idx - 1])
                else:
                    console.print(f"[yellow]Warning: Skipping invalid index {idx}[/yellow]")
            
            console.print(f"[green]Applying {len(selected)} selected transformation(s)[/green]")
            return selected
        
        except ValueError:
            console.print("[red]Invalid input - skipping all transformations[/red]")
            return []
    
    else:
        console.print("[yellow]Invalid choice - skipping all transformations[/yellow]")
        return []


@click.command()
@click.argument("nsprev_file", type=click.Path(exists=True, path_type=Path))
@click.argument("engprev_file", type=click.Path(exists=True, path_type=Path))
@click.argument("engnew_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    default="",
    help="Output file name (default: auto-generated from nsprev filename + engnew version)",
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--debug", is_flag=True, help="Debug output")
@click.option("--summary", is_flag=True, help="Show merge summary")
@click.option(
    "--rules",
    type=click.Path(path_type=Path),
    help="Path to merge rules YAML file for rulebook-based merging"
)
def migrate(
    nsprev_file: Path,
    engprev_file: Path,
    engnew_file: Path,
    output: str,
    verbose: bool,
    debug: bool,
    summary: bool,
    rules: Path,
):
    """
    CVPilot Configuration Migration - Complete Workflow: Stage 1 + Stage 2 + Stage 3.

    Runs all three stages in sequence:
    1. Stage 1: Extract differences between NSPREV and ENGPREV files
    2. Stage 2: Apply differences to ENGNEW with proper precedence
    3. Stage 3: Detect and resolve path transformations (duplicate values in different paths)

    Arguments:
        NSPREV_FILE: Namespace previous configuration file
        ENGPREV_FILE: Engineering previous template file
        ENGNEW_FILE: Engineering new template file

    Final output: Auto-generated filename based on NSPREV + ENGNEW version
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

        file_paths = [str(nsprev_file), str(engprev_file), str(engnew_file)]
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

            progress.update(task, description="Loading NSPREV file...")
            logger.debug(f"Loading NSPREV file: {nsprev_file}")
            nsprev_data = parser.load_yaml_file(str(nsprev_file))

            progress.update(task, description="Loading ENGPREV file...")
            logger.debug(f"Loading ENGPREV file: {engprev_file}")
            engprev_data = parser.load_yaml_file(str(engprev_file))

            progress.update(task, description="Loading ENGNEW file...")
            logger.debug(f"Loading ENGNEW file: {engnew_file}")
            engnew_data = parser.load_yaml_file(str(engnew_file))

        # Generate output filename if not provided
        if not output:
            output = _generate_output_filename(nsprev_file, engnew_data)
            logger.info(f"Auto-generated output filename: {output}")

        # STAGE 1: Merge NSPREV and ENGPREV
        logger.info("Stage 1: Merging NSPREV and ENGPREV")

        progress.update(task, description="Stage 1: Merging NSPREV and ENGPREV...")
        diff_data = ConfigMerger.merge_configs_stage1(nsprev_data, engprev_data)

        # Save stage1 diff file
        diff_filename = "diff_nsprev_engprev.yaml"
        progress.update(task, description=f"Saving stage1 diff to {diff_filename}...")
        logger.debug(f"Saving stage1 differences to: {diff_filename}")
        parser.save_yaml_file(diff_data, diff_filename)

        logger.info(f"Stage 1 completed: {diff_filename} created")

        # STAGE 2: Merge diff with ENGNEW
        logger.info("Stage 2: Merging with ENGNEW")

        progress.update(task, description="Stage 2: Merging with ENGNEW...")
        
        # Use rulebook-based merging if rules file is provided
        if rules and rules.exists():
            logger.info(f"Using rulebook-based merging with rules: {rules}")
            final_config = ConfigMerger.merge_with_rulebook(diff_data, engnew_data, str(rules), nsprev_data)
        else:
            final_config = ConfigMerger.merge_configs_stage2(diff_data, engnew_data)

        # Apply version replacement to ensure consistency
        progress.update(task, description="Applying version normalization...")
        logger.debug("Applying version replacement for consistency")
        target_version = ConfigMerger._extract_target_version(engnew_data)
        if target_version:
            final_config = ConfigMerger.replace_version_references(final_config, target_version)
            logger.info(f"Version references normalized to: {target_version}")

        # STAGE 3: Detect and resolve path transformations
        logger.info("Stage 3: Detecting path transformations")
        progress.update(task, description="Stage 3: Detecting path transformations...")
        
        detector = PathTransformationDetector()
        all_transformations = detector.detect_duplicate_values(final_config, engnew_data)
        
        # Filter to only show "move" recommendations (ignore keep_both)
        transformations = [t for t in all_transformations if t.recommendation == 'move']
        
        if transformations:
            logger.info(f"Detected {len(transformations)} path transformation(s) with 'move' recommendation")
            if len(all_transformations) > len(transformations):
                logger.debug(f"Filtered out {len(all_transformations) - len(transformations)} 'keep_both' recommendations")
            
            # Display transformations to user
            _display_transformation_report(console, transformations)
            
            # Get user selection
            selected_transformations = _prompt_user_selection(console, transformations)
            
            if selected_transformations:
                logger.info(f"Applying {len(selected_transformations)} selected transformation(s)")
                progress.update(task, description="Applying selected transformations...")
                
                # Check if any parent object transformations need manual review
                parent_transformations = [t for t in selected_transformations if "[Object with" in str(t.value)]
                
                # Apply selected transformations
                final_config = detector.apply_transformations(final_config, selected_transformations)
                
                console.print(f"[green]✓ Applied {len(selected_transformations)} transformation(s)[/green]\n")
                
                # Warn about parent objects that may have lost values
                if parent_transformations:
                    console.print("[yellow]⚠️  Warning: Parent object transformations detected![/yellow]")
                    console.print("[yellow]   The following objects were removed. Please verify that their values[/yellow]")
                    console.print("[yellow]   were properly transferred to the new structure:[/yellow]")
                    for t in parent_transformations:
                        console.print(f"[yellow]   - {t.old_path} → {t.new_path}[/yellow]")
                    console.print()
            else:
                logger.info("No transformations applied - user skipped")
                console.print("[yellow]No transformations applied - output may contain duplicate paths[/yellow]\n")
        else:
            logger.info("No path transformations detected")
            console.print("[green]✓ No path transformations detected[/green]\n")

        # Save final output
        progress.update(task, description=f"Saving final output to {output}...")
        logger.debug(f"Saving final configuration to: {output}")
        parser.save_yaml_file(final_config, output)

        # Success message
        logger.info("Complete Migration Workflow Successful")
        console.print(
            Panel.fit(
                f"[bold green]CVPilot Migration Workflow Successful![/bold green]\n"
                f"Stage 1: NSPREV + ENGPREV → {diff_filename}\n"
                f"Stage 2: diff + ENGNEW → intermediate result\n"
                f"Stage 3: Path transformation detection → {output}",
                title="CVPilot - Configuration Verification Pilot",
                border_style="green",
            )
        )

        # Show summary if requested
        if summary:
            _show_integrated_summary(
                console, nsprev_data, engprev_data, engnew_data, final_config
            )

        logger.info("Complete workflow finished successfully")

    except Exception as e:
        logger.error(f"Error: {e}")
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise click.Abort()


@click.command()
@click.argument("nsprev_file", type=click.Path(exists=True, path_type=Path))
@click.argument("engnew_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    default="merge_rules.yaml",
    help="Output file name for generated rulebook (default: merge_rules.yaml)",
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--debug", is_flag=True, help="Debug output")
def generate_rules(
    nsprev_file: Path,
    engnew_file: Path,
    output: str,
    verbose: bool,
    debug: bool,
):
    """
    Generate merge rules YAML file from analysis of NSPREV and ENGNEW files.
    
    Analyzes both files to detect conflicts in list-type fields (annotations, labels, etc.)
    and generates intelligent merge strategy suggestions.
    
    Arguments:
        NSPREV_FILE: Namespace previous configuration file
        ENGNEW_FILE: Engineering new template file
    """
    # Setup logging
    log_level = "DEBUG" if debug else "INFO" if verbose else "WARNING"
    logger = setup_logging(log_level)
    console = Console()

    try:
        # Initialize analyzer
        analyzer = ConflictAnalyzer()
        
        console.print("[bold blue]Analyzing files for conflicts...[/bold blue]")
        
        # Analyze files
        analysis = analyzer.analyze_files(str(nsprev_file), str(engnew_file))
        
        # Generate rulebook
        rulebook_content = generate_rulebook_from_analysis(analysis)
        
        # Save rulebook
        with open(output, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(rulebook_content, f, default_flow_style=False, sort_keys=False)
        
        # Show summary
        summary = analysis.get('summary', {})
        console.print(f"[bold green]✓ Generated rulebook: {output}[/bold green]")
        console.print(f"  - Total conflicts detected: {summary.get('total_conflicts', 0)}")
        console.print(f"  - Suggested merges: {summary.get('suggested_merges', 0)}")
        console.print(f"  - Suggested NSPREV preservations: {summary.get('suggested_nsprev', 0)}")
        console.print(f"  - Suggested ENGNEW replacements: {summary.get('suggested_engnew', 0)}")
        
        if summary.get('high_confidence', 0) > 0:
            console.print(f"  - High confidence suggestions: {summary.get('high_confidence', 0)}")
        
        console.print("\n[bold blue]Next steps:[/bold blue]")
        console.print(f"1. Review and customize {output}")
        console.print(f"2. Run: cvpilot migrate <nsprev> <engprev> <engnew> --rules {output}")
        
        logger.info(f"Rulebook generation completed: {output}")

    except Exception as e:
        logger.error(f"Error: {e}")
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise click.Abort()


@click.group()
def cli():
    """CVPilot - Configuration Verification Pilot for YAML merging with namespace precedence."""


# Add the commands to the CLI group
cli.add_command(migrate)
cli.add_command(generate_rules)
