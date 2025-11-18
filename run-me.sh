#!/bin/bash

cd "$(dirname "$0")"
set -ex

# tmp mappa létrehozása, ha nincs
if [ ! -d tmp ] ; then
  mkdir tmp
fi

# Alapértelmezett config létrehozása
if [ ! -f .env ] ; then
  cp env.template .env
  echo "Default config created!"
fi
