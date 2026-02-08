"""Dev server entry point. Replicates mapproxy-util serve-develop but wraps
the app in PtMiddleware."""

import logging
import os
import sys


def setup_logging():
    mapproxy_log = logging.getLogger("mapproxy")
    mapproxy_log.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(name)s - %(levelname)s - %(message)s"))
    mapproxy_log.addHandler(ch)


def main():
    setup_logging()

    from mapproxy.wsgiapp import make_wsgi_app
    from mapproxy.util.ext.serving import run_simple

    from ptplugin.middleware import PtMiddleware

    mapproxy_conf = os.environ.get("MAPPROXY_CONF", "/mapproxy/mapproxy.yaml")
    dev_mode = bool(os.environ.get("DEV_MODE"))

    inner_app = make_wsgi_app(mapproxy_conf)
    extra_files = inner_app.config_files.keys()
    cache_dir = inner_app.base_config.cache.base_dir

    app = PtMiddleware(inner_app, dev_mode=dev_mode, cache_dir=cache_dir)

    host = "0.0.0.0"
    port = 8080

    run_simple(
        host,
        port,
        app,
        use_reloader=True,
        processes=1,
        threaded=True,
        passthrough_errors=True,
        extra_files=extra_files,
    )


if __name__ == "__main__":
    main()
