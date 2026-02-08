#!/bin/bash
set -euo pipefail

# Inject environment variables into AWS config
# Write to /etc/aws so it's accessible regardless of which user runs the app

mkdir -p /etc/aws

cat <<EOF >/etc/aws/config
[profile tiles-my-personalb]
region=eu-central-003
endpoint_url=https://s3.eu-central-003.backblazeb2.com
EOF

cat <<EOF >/etc/aws/credentials
[tiles-my-personalb]
aws_access_key_id=${TILES_MY_PERSONALB_ACCESS_KEY_ID}
aws_secret_access_key=${TILES_MY_PERSONALB_SECRET_ACCESS_KEY}
EOF

chmod 644 /etc/aws/config /etc/aws/credentials
export AWS_CONFIG_FILE=/etc/aws/config
export AWS_SHARED_CREDENTIALS_FILE=/etc/aws/credentials

# Clear stale prometheus multiprocess files
rm -rf "${PROMETHEUS_MULTIPROC_DIR:?}"/*

# Inject environment variables into MapProxy config

sed "s|{{OS_API_KEY}}|${OS_API_KEY}|g" /mapproxy/mapproxy_template.yaml > /mapproxy/mapproxy.yaml

# Launch

exec "$@"
