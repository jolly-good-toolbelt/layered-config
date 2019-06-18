#!/usr/bin/env python3
"""
Setup the development environment.

Runs the following commands:
{}
"""
import argparse
from subprocess import check_call

commands_to_run = [
    ["poetry", "run", "pip", "install", "--upgrade", "pip<19"],
    ["poetry", "install", "-E", "munch"],
    ["poetry", "run", "pre-commit", "install"],
]

__doc__ = __doc__.format("\n".join(map(" ".join, commands_to_run)))


def env_setup(verbose):
    """Prepare environment for running."""
    for command in commands_to_run:
        if verbose:
            print(" ".join(command))
        check_call(command)


def main():
    """Execute env_setup using command line args."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show each command before it is executed",
    )
    args = parser.parse_args()
    env_setup(args.verbose)


if __name__ == "__main__":
    main()
