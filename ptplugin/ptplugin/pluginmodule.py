from mapproxy.config.loader import register_source_configuration
from mapproxy.wsgiapp import MapProxyApp, register_request_interceptor
from mapproxy.request.base import Request

from ptplugin.s3tile import S3TileSourceConfiguration

import logging
import os

l = logging.getLogger("mapproxy.pt")

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


def plugin_entrypoint():
    register_source_configuration(
        config_name="s3tile",
        config_class=S3TileSourceConfiguration,
        yaml_spec_source_name="s3tile",
        yaml_spec_source_def=S3TileSourceConfiguration.spec_source_def,
    )

    register_request_interceptor(interceptor)

    if os.environ.get("DEV_MODE"):
        _patch_no_cache()
        l.info("DEV_MODE: response caching disabled")

    l.info("ptplugin loaded")


def _patch_no_cache():
    _original_call = MapProxyApp.__call__

    def __call__(self, environ, start_response):
        def start_response_no_cache(status, headers, exc_info=None):
            headers = [
                (k, v)
                for k, v in headers
                if k.lower() not in ("cache-control", "pragma", "expires")
            ]
            for k, v in NO_CACHE_HEADERS.items():
                headers.append((k, v))
            return start_response(status, headers, exc_info)

        return _original_call(self, environ, start_response_no_cache)

    MapProxyApp.__call__ = __call__


def interceptor(req):
    return req
