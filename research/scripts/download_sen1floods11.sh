#!/usr/bin/env bash
set -euo pipefail

# Downloads only the hand-labelled Sentinel-1 benchmark subset.  When Google
# Cloud tools are unavailable, aria2c queries the public GCS object listing and
# downloads the same files with parallel, resumable HTTP transfers.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DESTINATION="${FLOODLENS_RESEARCH_DATA:-${ROOT_DIR}/data/research/sen1floods11}"
BUCKET="gs://sen1floods11/v1.1"

mkdir -p "${DESTINATION}/v1.1/data/flood_events/HandLabeled"

COPY=()
if command -v gcloud >/dev/null 2>&1; then
  COPY=(gcloud storage rsync --recursive)
elif command -v gsutil >/dev/null 2>&1; then
  COPY=(gsutil -m rsync -r)
fi

for layer in S1Hand LabelHand JRCWaterHand; do
  echo "Syncing ${layer} ..."
  if [[ ${#COPY[@]} -gt 0 ]]; then
    "${COPY[@]}" \
      "${BUCKET}/data/flood_events/HandLabeled/${layer}" \
      "${DESTINATION}/v1.1/data/flood_events/HandLabeled/${layer}"
  elif command -v aria2c >/dev/null 2>&1; then
    TARGET="${DESTINATION}/v1.1/data/flood_events/HandLabeled/${layer}"
    mkdir -p "${TARGET}"
    MANIFEST="$(mktemp)"
    python - "${layer}" "${TARGET}" > "${MANIFEST}" <<'PY'
import json
import sys
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import urlopen

layer, destination = sys.argv[1:]
prefix = f"v1.1/data/flood_events/HandLabeled/{layer}/"
token = None
while True:
    params = {"prefix": prefix, "maxResults": "1000"}
    if token:
        params["pageToken"] = token
    url = "https://storage.googleapis.com/storage/v1/b/sen1floods11/o?" + urlencode(params)
    with urlopen(url, timeout=60) as response:
        payload = json.load(response)
    for item in payload.get("items", []):
        name = item["name"]
        if name.endswith("/"):
            continue
        relative = name.removeprefix(prefix)
        path = Path(destination) / relative
        print(item["mediaLink"])
        print(f"  dir={path.parent}")
        print(f"  out={path.name}")
    token = payload.get("nextPageToken")
    if not token:
        break
PY
    aria2c --continue=true --max-connection-per-server=8 --split=8 --min-split-size=1M \
      --max-tries=10 --retry-wait=3 --summary-interval=30 --input-file="${MANIFEST}"
    rm -f "${MANIFEST}"
  else
    echo "Install aria2 (or Google Cloud CLI), then retry." >&2
    exit 1
  fi
done

if command -v gcloud >/dev/null 2>&1; then
  gcloud storage cp "${BUCKET}/Sen1Floods11_Metadata.geojson" "${DESTINATION}/v1.1/Sen1Floods11_Metadata.geojson"
elif command -v gsutil >/dev/null 2>&1; then
  gsutil cp "${BUCKET}/Sen1Floods11_Metadata.geojson" "${DESTINATION}/v1.1/Sen1Floods11_Metadata.geojson"
else
  mkdir -p "${DESTINATION}/v1.1"
  aria2c --continue=true --max-connection-per-server=8 --split=8 --min-split-size=1M --max-tries=10 --retry-wait=3 \
    --dir="${DESTINATION}/v1.1" --out="Sen1Floods11_Metadata.geojson" \
    "https://storage.googleapis.com/sen1floods11/v1.1/Sen1Floods11_Metadata.geojson"
fi

echo "Finished. Files are in: ${DESTINATION}"
