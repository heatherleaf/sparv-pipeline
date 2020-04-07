"""Main Sparv executable."""
import argparse
import os
import sys

import snakemake

from sparv.core.paths import sparv_path

# Set up command line arguments
parser = argparse.ArgumentParser(prog="sparv",
                                 description="Sparv Pipeline",
                                 allow_abbrev=False)

subparsers = parser.add_subparsers(dest="command")
subparsers.required = True

target_parser = subparsers.add_parser("target")
target_parser.add_argument("targets", nargs="*", help="Annotation file(s) to create.")
target_parser.add_argument("--dir", help="Path to working directory.")
target_parser.add_argument("--j", type=int, help="Number of cores to use.", default=1)
target_parser.add_argument("--dry-run", action="store_true", help="Only dry-run the workflow.")
target_parser.add_argument("--list-targets", action="store_true", help="List available targets.")
target_parser.add_argument("--debug", action="store_true", help="Show debug messages.")

annotations_parser = subparsers.add_parser("annotations", help="List available modules and annotations.")
config_parser = subparsers.add_parser("config", help="Display corpus config.")
run_parser = subparsers.add_parser("run", help="Run annotator module independently.", add_help=False)

# Parse arguments. We allow unknown arguments for the 'run' command which is handled separately.
args, unknown_args = parser.parse_known_args(args=None if sys.argv[1:] else ["--help"])

if args.command == "run":
    from sparv.core import run
    run.main(unknown_args)
    sys.exit()
else:
    args = parser.parse_args()

snakemake_args = {}
config = {}

if args.command in ("annotations", "config"):
    snakemake_args["targets"] = [args.command]
    snakemake_args["force_use_threads"] = True
elif args.command == "target":
    snakemake_args = {
        "workdir": args.dir,
        "dryrun": args.dry_run,
        "cores": args.j,
        "targets": args.targets
    }
    if args.list_targets:
        snakemake_args["targets"].append("list_targets")
        # Suppress some of the chatty output when only printing targets
        if len(snakemake_args["targets"]) == 1:
            snakemake_args["force_use_threads"] = True
    config = {"debug": args.debug}
    # List available targets if no target was specified
    if not snakemake_args["targets"]:
        print("\nNo targets provided!\n")
        snakemake_args["targets"].append("list_targets")
        snakemake_args["force_use_threads"] = True

snakemake.snakemake(os.path.join(sparv_path, "core", "Snakefile"), **snakemake_args, quiet=True, config=config)
