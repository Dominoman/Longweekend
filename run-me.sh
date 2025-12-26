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
  /home/$USER/.local/bin/uv run flask db upgrade
fi

#Replace old cron job
currentpath=$(pwd)
username=$(whoami)
groupname=$(id -gn)
crontab -l | grep -v "LongWeekend" > newcron
echo "30 */6 * * * cd $currentpath && /home/$username/.local/bin/uv run flask scan >> $currentpath/log.log 2>&1" >> newcron
crontab newcron
rm newcron