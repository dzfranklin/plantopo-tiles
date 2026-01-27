#!/bin/bash
set -euo pipefail

mkdir -p $HOME/.aws
cat <<EOF >$HOME/.aws/config
[default]
region=eu-central-003
endpoint_url=https://s3.eu-central-003.backblazeb2.com

[tiles-my-personalb]
aws_access_key_id=${TILES_MY_PERSONALB_ACCESS_KEY_ID}
aws_secret_access_key=${TILES_MY_PERSONALB_SECRET_ACCESS_KEY}
EOF

sed "s|{{OS_API_KEY}}|${OS_API_KEY}|g" /mapproxy/mapproxy_template.yaml > /mapproxy/mapproxy.yaml

if [ ! -z "$DEV_SERVER" ]; then
    exec mapproxy-util serve-develop -b 0.0.0.0:8080 /mapproxy/mapproxy.yaml
fi

exec "/scripts/start.sh"
