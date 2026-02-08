import os
import re
import time

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

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")

        if path == "/metrics":
            self._update_cache_metrics()
            return self._serve_metrics(environ, start_response)

        tile_match = _tile_path_re.match(path)
        start = time.monotonic()
        status_code = [None]

        def capturing_start_response(status, headers, exc_info=None):
            status_code[0] = status[:3]
            if self.dev_mode:
                headers = [
                    (k, v)
                    for k, v in headers
                    if k.lower() not in ("cache-control", "pragma", "expires")
                ]
                for k, v in NO_CACHE_HEADERS.items():
                    headers.append((k, v))
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
