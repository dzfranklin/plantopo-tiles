FROM ghcr.io/osgeo/gdal:ubuntu-full-3.12.1 AS tile-builder

RUN apt-get update && \
    apt-get install -y wget unzip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /scratch
RUN mkdir /tiles

RUN wget "https://naciscdn.org/naturalearth/50m/raster/NE1_50M_SR_W.zip" -O ne1_50m_sr_w.zip && \
    unzip ne1_50m_sr_w.zip && \
    gdal2tiles.py -z 0-4 --xyz -r bilinear --tilesize 256 --tiledriver PNG -w none -a 0,0,0 NE1_50M_SR_W/NE1_50M_SR_W.tif /tiles/ne1 && \
    rm -r ne1_50m_sr_w.zip NE1_50M_SR_W

FROM kartoza/mapproxy:6.0.1--v2025.12.01

# Avoid cluttering logs with ascii art printed by kartoza/mapproxy
RUN printf '#!/bin/sh\ntrue'>/usr/bin/figlet

RUN python3 -m pip install ipdb boto3~=1.42.35 prometheus_client

RUN python3 -c "from pyproj.transformer import TransformerGroup; \
    tg = TransformerGroup('EPSG:27700', 'EPSG:3857', always_xy=True); \
    tg.download_grids(verbose=True);"

RUN printf '#!/bin/sh\nexec python3 -m ptplugin.serve\n' \
    >/scripts/serve-develop.sh && chmod +x /scripts/serve-develop.sh

# After kartoza's start.sh generates app.py, overwrite it with ours
RUN mkdir -p /docker-entrypoint-mapproxy.d && \
    printf '#!/bin/sh\ncp /mapproxy/ptplugin/ptplugin/app.py ${MAPPROXY_APP_DIR:-/opt/mapproxy}/app.py\n' \
    >/docker-entrypoint-mapproxy.d/01-install-app.sh && chmod +x /docker-entrypoint-mapproxy.d/01-install-app.sh

COPY --from=tile-builder /tiles /static-tiles

COPY ptplugin /mapproxy/ptplugin
RUN python3 -m pip install /mapproxy/ptplugin

COPY mapproxy_template.yaml /mapproxy/mapproxy_template.yaml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV AWS_CONFIG_FILE=/etc/aws/config
ENV AWS_SHARED_CREDENTIALS_FILE=/etc/aws/credentials
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
RUN mkdir -p /tmp/prometheus_multiproc && chmod 777 /tmp/prometheus_multiproc

EXPOSE 8080

ENTRYPOINT [ "/entrypoint.sh"]
CMD [ "/scripts/start.sh" ]
