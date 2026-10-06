#!/bin/sh
set -eu

if [ -z "${MODEL_URL:-}" ]; then
  exec ninfer-serve "$@"
fi

: "${MODEL_SHA256:?MODEL_SHA256 is required with MODEL_URL}"
: "${MODEL_FILE:?MODEL_FILE is required with MODEL_URL}"

part="${MODEL_FILE}.part"
marker="${MODEL_FILE}.ok"
mkdir -p "$(dirname "$MODEL_FILE")"

size_of() { stat -c %s "$1"; }

verified() {
  [ -f "$MODEL_FILE" ] && [ -f "$marker" ] || return 1
  [ "$(cat "$marker")" = "${MODEL_SHA256} $(size_of "$MODEL_FILE")" ] || return 1
  [ "${MODEL_VERIFY:-fast}" != "full" ] || [ "$(sha256sum "$MODEL_FILE" | cut -d' ' -f1)" = "$MODEL_SHA256" ]
}

if verified; then
  echo "model present and verified: $MODEL_FILE"
else
  echo "model missing or unverified, downloading $MODEL_URL"
  rm -f "$marker"
  curl -fL --retry 8 --retry-delay 10 --retry-all-errors -C - -o "$part" "$MODEL_URL"
  got="$(sha256sum "$part" | cut -d' ' -f1)"
  if [ "$got" != "$MODEL_SHA256" ]; then
    echo "ERROR: sha256 mismatch for $MODEL_URL: expected $MODEL_SHA256 got $got" >&2
    rm -f "$part"
    exit 1
  fi
  mv "$part" "$MODEL_FILE"
  echo "${MODEL_SHA256} $(size_of "$MODEL_FILE")" > "$marker"
  echo "model downloaded and verified: $MODEL_FILE"
fi

if [ -n "${MODEL_REPO:-}" ] && [ -n "${MODEL_REVISION:-}" ]; then
  latest="$(curl -fsS --max-time 15 "https://huggingface.co/api/models/${MODEL_REPO}" 2>/dev/null | grep -o '"sha":"[0-9a-f]*"' | head -1 | cut -d'"' -f4 || true)"
  if [ -n "$latest" ] && [ "$latest" != "$MODEL_REVISION" ]; then
    echo "WARNING: ${MODEL_REPO} has a newer upstream revision ${latest}; pinned ${MODEL_REVISION}" >&2
  fi
fi

exec ninfer-serve "$@"
