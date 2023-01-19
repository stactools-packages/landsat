import stactools.core
from stactools.cli.registry import Registry

stactools.core.use_fsspec()


def register_plugin(registry: Registry) -> None:
    from stactools.landsat import commands

    registry.register_subcommand(commands.create_landsat_command)


__version__ = "0.3.0"
