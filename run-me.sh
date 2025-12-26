#!/bin/bash

cd "$(dirname "$0")"
set -ex

# Alapértelmezett config létrehozása
if [ ! -f .env ] ; then
  cp env.template .env
  echo "Default config created!"
fi

#Upgrade the database
if [ -f migrations/alembic.ini ] ; then
  /home/$USER/.local/bin/uvuv run flask db upgrade
fi