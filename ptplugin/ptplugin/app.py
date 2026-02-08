import os

from mapproxy.wsgiapp import make_wsgi_app

from ptplugin.middleware import PtMiddleware

MAPPROXY_CONF = os.environ.get("MAPPROXY_CONF", "/mapproxy/mapproxy.yaml")

mapproxy_app = make_wsgi_app(MAPPROXY_CONF)
cache_dir = getattr(getattr(mapproxy_app, "base_config", None), "cache", None)
assert (
    cache_dir is not None
), "Cache directory must be configured in mapproxy.yaml for PtMiddleware"
cache_dir = cache_dir.base_dir

application = PtMiddleware(
    mapproxy_app,
    dev_mode=bool(os.environ.get("DEV_MODE")),
    cache_dir=cache_dir,
)
