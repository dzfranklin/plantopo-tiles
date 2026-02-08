from mapproxy.config.loader import register_source_configuration

from ptplugin.s3tile import S3TileSourceConfiguration

import logging

l = logging.getLogger("mapproxy.pt")


def plugin_entrypoint():
    register_source_configuration(
        config_name="s3tile",
        config_class=S3TileSourceConfiguration,
        yaml_spec_source_name="s3tile",
        yaml_spec_source_def=S3TileSourceConfiguration.spec_source_def,
    )
    l.info("ptplugin loaded")
