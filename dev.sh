#!/usr/bin/env bash
# if arg --prod-server is set, do not set DEV_SERVER
if [ "$1" == "--prod-server" ]; then
    dev_server_arg=""
else
    dev_server_arg="--env DEV_SERVER=1"
fi
docker-compose run --build --rm --remove-orphans --service-ports $dev_server_arg dev
