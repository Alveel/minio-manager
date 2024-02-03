#!/usr/bin/env bash
set -eu

for cluster in */; do
  cluster=$(basename $cluster)

  for group in $cluster/*/; do
    (
      group=$(basename $group)
      if [ -s "$cluster/$group/.env" ]; then
        cd "$cluster/$group"
        source .env
        echo "Running minio-manager for $cluster/$group"
        minio-manager
      else
        echo "Skipping $cluster/$group because .env is missing"
      fi
    )
  done
done
