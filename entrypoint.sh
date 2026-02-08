#!/bin/bash
set -euo pipefail

# Inject environment variables into AWS config

mkdir -p "$HOME/.aws"

cat <<EOF >"$HOME/.aws/config"
[profile tiles-my-personalb]
region=eu-central-003
endpoint_url=https://s3.eu-central-003.backblazeb2.com
EOF

cat <<EOF >"$HOME/.aws/credentials"
[tiles-my-personalb]
aws_access_key_id=${TILES_MY_PERSONALB_ACCESS_KEY_ID}
aws_secret_access_key=${TILES_MY_PERSONALB_SECRET_ACCESS_KEY}
EOF

# Inject environment variables into MapProxy config

sed "s|{{OS_API_KEY}}|${OS_API_KEY}|g" /mapproxy/mapproxy_template.yaml > /mapproxy/mapproxy.yaml

# Launch

exec "$@"
