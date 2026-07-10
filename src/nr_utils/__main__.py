"""Command-line interface."""

import click


@click.command()
@click.version_option()
def main() -> None:
    """SSB Nr Utils."""


if __name__ == "__main__":
    main(prog_name="ssb-nr-utils")  # pragma: no cover
