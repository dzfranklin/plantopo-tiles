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

RUN python3 -m pip install boto3~=1.42.35

RUN python3 -c "from pyproj.transformer import TransformerGroup; \
    tg = TransformerGroup('EPSG:27700', 'EPSG:3857', always_xy=True); \
    tg.download_grids(verbose=True);"

COPY --from=tile-builder /tiles /static-tiles

COPY mapproxy_template.yaml /mapproxy/mapproxy_template.yaml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT [ "/entrypoint.sh"]
