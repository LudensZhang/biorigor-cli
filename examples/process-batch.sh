#!/usr/bin/env bash
# Process a directory of PDFs one at a time: submit, wait, keep going.
#
#   ./process-batch.sh ~/papers/*.pdf
#   BIORIGOR_MODEL=my-model ./process-batch.sh papers/*.pdf
#
# Each result is appended to ./reports/tasks.jsonl so you can post-process it.
set -uo pipefail

OUT="${OUT:-./reports}"
INTERVAL="${INTERVAL:-120}"                 # seconds between polls
MODEL="${BIORIGOR_MODEL:-}"                 # empty = server default
mkdir -p "$OUT"
: > "$OUT/tasks.jsonl"

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <file.pdf> [more.pdf ...]" >&2
  exit 2
fi

ok=0 fail=0

for pdf in "$@"; do
  name=$(basename "$pdf")
  printf '== %s\n' "$name"

  model_arg=()
  [ -n "$MODEL" ] && model_arg=(--model "$MODEL")

  tid=$(biorigor submit "$pdf" "${model_arg[@]}" --json \
        | python3 -c 'import json,sys; print(json.load(sys.stdin).get("taskId") or "")')
  if [ -z "$tid" ]; then
    printf '   submit failed\n' >&2
    fail=$((fail+1))
    continue
  fi
  printf '   task %s\n' "$tid"

  # --json prints the final task objects; append them verbatim
  if biorigor wait "$tid" --interval "$INTERVAL" --download "$OUT" --json >> "$OUT/tasks.jsonl"; then
    ok=$((ok+1))
    risk=$(biorigor status "$tid" --json \
           | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("risk") or "-")')
    printf '   done  risk=%s\n' "$risk"
  else
    fail=$((fail+1))
    printf '   FAILED\n' >&2
  fi
done

printf '\n%d succeeded, %d failed. Results: %s/tasks.jsonl\n' "$ok" "$fail" "$OUT"
[ "$fail" -eq 0 ]
