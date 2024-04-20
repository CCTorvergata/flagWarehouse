#!/bin/sh

cd ./server
docker compose up -d --build --force-recreate
cd .././client
docker compose up -d --build --force-recreate