import logging
import os
import re
import time
from urllib.parse import urlparse

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
    CONTENT_TYPE_LATEST,
)

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

# Matches /tiles/{layer}/{grid}/{z}/{x}/{y}.{format}
# or /tiles/{layer}/{z}/{x}/{y}.{format} (grid may be absent)
_tile_path_re = re.compile(
    r"^/(?:tiles|tms)/(?P<layer>[^/]+)/(?:[^/]+/)?(?P<z>\d+)/\d+/\d+\.\w+$"
)
_service_re = re.compile(r"^/(\w+)")


# OS Maps API: zoom levels at which data becomes premium
# https://docs.os.uk/os-apis/accessing-os-apis/os-maps-api/layers-and-styles
# Outdoor_3857: open 7-16, premium 17-20
# Leisure_27700: open 0-5, premium 6-9
_OS_PREMIUM_MIN_ZOOM = {
    "Outdoor_3857": 17,
    "Road_3857": 17,
    "Light_3857": 17,
    "Outdoor_27700": 10,
    "Road_27700": 10,
    "Light_27700": 10,
    "Leisure_27700": 6,
}

# Matches e.g. /zxy/Outdoor_3857/13/4018/2504.png
_os_zxy_re = re.compile(r"/zxy/(\w+)/(\d+)/")


def _source_label_from_url(url):
    """Extract a short source label from an upstream request URL."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
    except Exception:
        return "unknown"
    if host == "api.os.uk":
        m = _os_zxy_re.search(parsed.path)
        if m:
            layer, zoom = m.group(1), int(m.group(2))
            premium_min = _OS_PREMIUM_MIN_ZOOM.get(layer)
            if premium_min is not None and zoom >= premium_min:
                return "os_premium"
        return "os_open"
    if host == "tile.openstreetmap.org":
        return "osm"
    if "backblazeb2.com" in host:
        return "b2"
    if host == "" or host == "localhost":
        return "local"
    return host


class _UpstreamMetricsHandler(logging.Handler):
    """Logging handler that captures mapproxy.source.request log records
    and feeds them into Prometheus metrics.

    Log format (from mapproxy/client/log.py):
        METHOD URL STATUS SIZE_KB DURATION_MS
    """

    def __init__(self, upstream_requests, upstream_request_duration):
        super().__init__(level=logging.INFO)
        self.upstream_requests = upstream_requests
        self.upstream_request_duration = upstream_request_duration

    def emit(self, record):
        try:
            parts = record.getMessage().split()
            if len(parts) < 5:
                return
            url = parts[1]
            status = parts[2]
            duration_ms = parts[4]

            source = _source_label_from_url(url)
            self.upstream_requests.labels(source=source, status=status).inc()
            if duration_ms != "-":
                self.upstream_request_duration.labels(source=source).observe(
                    float(duration_ms) / 1000.0
                )
        except Exception:
            pass


_TILEJSON_DIR = os.environ.get("TILEJSON_DIR", "/tilejson")
_tilejson_re = re.compile(r"^/tilejson/([a-z0-9_-]+)\.json$")


class PtMiddleware:
    def __init__(self, app, dev_mode=False, cache_dir=None):
        assert cache_dir is not None, "cache_dir must be provided for cache metrics"

        self.app = app
        self.dev_mode = dev_mode
        self.cache_dir = cache_dir
        self.multiprocess = "PROMETHEUS_MULTIPROC_DIR" in os.environ

        self.tile_requests = Counter(
            "mapproxy_tile_requests_total",
            "Tile requests by layer, zoom, and status",
            ["layer", "zoom", "status"],
        )
        self.tile_request_duration = Histogram(
            "mapproxy_tile_request_duration_seconds",
            "Tile request duration by layer and zoom",
            ["layer", "zoom"],
        )
        self.other_requests = Counter(
            "mapproxy_other_requests_total",
            "Non-tile requests by service and status",
            ["service", "status"],
        )

        self.cache_size_bytes = Gauge(
            "mapproxy_cache_size_bytes",
            "Total size of cached tiles in bytes",
            ["cache"],
            multiprocess_mode="mostrecent",
        )
        self.cache_tile_count = Gauge(
            "mapproxy_cache_tiles_total",
            "Number of cached tiles",
            ["cache"],
            multiprocess_mode="mostrecent",
        )

        self.upstream_requests = Counter(
            "mapproxy_upstream_requests_total",
            "Upstream source requests by source and status",
            ["source", "status"],
        )
        self.upstream_request_duration = Histogram(
            "mapproxy_upstream_request_duration_seconds",
            "Upstream source request duration by source",
            ["source"],
        )

        source_logger = logging.getLogger("mapproxy.source.request")
        source_logger.setLevel(logging.INFO)
        source_logger.propagate = False
        source_logger.addHandler(
            _UpstreamMetricsHandler(
                self.upstream_requests, self.upstream_request_duration
            )
        )

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")

        if path == "/metrics":
            self._update_cache_metrics()
            return self._serve_metrics(environ, start_response)

        tilejson_match = _tilejson_re.match(path)
        if tilejson_match:
            return self._serve_tilejson(tilejson_match.group(1), start_response)

        tile_match = _tile_path_re.match(path)
        start = time.monotonic()
        status_code = [None]

        def capturing_start_response(status, headers, exc_info=None):
            status_code[0] = status[:3]

            headers = [
                (k, v)
                for k, v in headers
                if k.lower() not in ("cache-control", "pragma", "expires")
            ]

            if self.dev_mode:
                headers.append(("Cache-Control", "no-cache"))
            else:
                # 24 hours (from OS terms): 24 * 3600 = 86400 seconds
                headers.append(("Cache-Control", "public, max-age=86400, immutable"))

            return start_response(status, headers, exc_info)

        result = self.app(environ, capturing_start_response)
        duration = time.monotonic() - start

        if tile_match:
            layer = tile_match.group("layer")
            zoom = tile_match.group("z")
            self.tile_requests.labels(
                layer=layer, zoom=zoom, status=status_code[0]
            ).inc()
            self.tile_request_duration.labels(layer=layer, zoom=zoom).observe(duration)
        else:
            service = _service_re.match(path)
            service_name = service.group(1) if service else "other"
            self.other_requests.labels(
                service=service_name, status=status_code[0]
            ).inc()

        return result

    def _update_cache_metrics(self):
        if not self.cache_dir or not os.path.isdir(self.cache_dir):
            return
        for entry in os.scandir(self.cache_dir):
            if not entry.is_dir() or entry.name == "tile_locks":
                continue
            cache_name = entry.name
            total_size = 0
            tile_count = 0
            for dirpath, _, filenames in os.walk(entry.path):
                for f in filenames:
                    filepath = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(filepath)
                        tile_count += 1
                    except OSError:
                        pass
            self.cache_size_bytes.labels(cache=cache_name).set(total_size)
            self.cache_tile_count.labels(cache=cache_name).set(tile_count)

    def _serve_tilejson(self, name, start_response):
        filepath = os.path.join(_TILEJSON_DIR, name + ".json")
        try:
            with open(filepath, "rb") as f:
                data = f.read()
        except FileNotFoundError:
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"Not Found"]
        start_response(
            "200 OK",
            [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(data))),
                ("Access-Control-Allow-Origin", "*"),
            ],
        )
        return [data]

    def _serve_metrics(self, environ, start_response):
        if self.multiprocess:
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
            data = generate_latest(registry)
        else:
            data = generate_latest()
        start_response(
            "200 OK",
            [
                ("Content-Type", CONTENT_TYPE_LATEST),
                ("Content-Length", str(len(data))),
            ],
        )
        return [data]
