#!/usr/bin/env bash

# docker run -e ACTIVATE_DATABASE=True -e ARTICLE_DATABASE_NAME='research' -e ARTICLE_DATABASE_HOST='sozindb.vaatu.co' -e ARTICLE_DATABASE_PORT='1214' chazzcoin/microcrawler:GoogleForever
# --tag chazzcoin/hark-api:latest
docker buildx build --push --platform linux/arm64,linux/amd64 --tag chazzcoin/rai-api:canary .