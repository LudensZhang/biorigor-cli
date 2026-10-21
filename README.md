# biorigor-cli

Command-line client for a **self-hosted BioRigor** paper-audit server.

BioRigor runs a four-dimension review of a scientific paper — conceptual novelty,
dry-lab methods, wet-lab figures, source-data forensics — and returns an HTML report
with a risk rating.

This CLI lets you drive it from a terminal or a script instead of a browser:

```console
$ biorigor submit paper.pdf
queued: abc123def456
  main: paper.pdf
  next: biorigor wait abc123def456 --download ./reports

$ biorigor wait abc123def456 --download ./reports
  .. abc123def456  running    reviewing methods
  OK abc123def456  done       risk MEDIUM    paper.pdf
  report saved: ./reports/abc123def456.html (48.2KB)
```

It's a **single file** using only the Python standard library — no `pip install`.

> **This is a client, not the server.** You need a BioRigor deployment to talk to.
> The CLI has no built-in default address; you supply yours.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/LudensZhang/biorigor-cli/main/biorigor -o biorigor
chmod +x biorigor
sudo mv biorigor /usr/local/bin/     # or anywhere on your PATH
```

Requires **Python 3.8+**.

## Point it at your server

```bash
biorigor login --host https://biorigor.example.org
```

The URL is checked against `/api/health` before the login is attempted, so a typo
fails immediately instead of silently storing a bad config.

Credentials land in `~/.config/biorigor/config.json` with mode `0600`.
Override the location with `BIORIGOR_CONF_DIR`.

Alternatives to interactive login:

```bash
# per-session
export BIORIGOR_HOST=https://biorigor.example.org

# fully non-interactive (CI)
export BIORIGOR_HOST=https://biorigor.example.org
export BIORIGOR_TOKEN=<token>

# password on stdin, for scripts
printf '%s\n' "$PW" | biorigor login --host https://biorigor.example.org -u alice --password-stdin
```

## Commands

| Command | What it does |
|---|---|
| `login [--host URL]` | Authenticate, store the token |
| `logout` | Forget the local token |
| `whoami` | Current user, role, server |
| `ping [URL...]` | Probe `/api/health` on one or more URLs |
| `models` | List models, engines, and which pairings are supported |
| `submit MAIN [-s SUPP]...` | Submit one paper |
| `batch PATTERN... [--wait]` | Submit many (globs allowed) |
| `list [--limit N]` | Your tasks |
| `status [ID...]` | Progress — active tasks if no id given |
| `wait ID... [--download DIR]` | Block until finished |
| `report ID [-o DIR]` | Download the HTML report |
| `cancel ID...` / `cancel all` | Stop tasks |
| `delete ID...` | Delete records and artifacts |

## Scripting

Every command accepts `--json`, and exit codes are meaningful:

| Exit code | Meaning |
|---|---|
| `0` | success |
| `1` | the audit failed or ended in a non-`done` state (`wait`, `batch`) |
| `2` | usage, authentication, or network problem |

### Grab the task id

```bash
TID=$(biorigor submit paper.pdf --json \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["taskId"])')
```

### Process a directory, one paper at a time

```bash
#!/usr/bin/env bash
set -uo pipefail
OUT=./reports; mkdir -p "$OUT"

for pdf in ~/papers/*.pdf; do
  echo "== $(basename "$pdf")"
  TID=$(biorigor submit "$pdf" --json \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["taskId"])') || continue
  biorigor wait "$TID" --interval 120 --download "$OUT" --json >> "$OUT/tasks.jsonl"
done
```

### Submit in bulk, wait later

```bash
biorigor batch 'papers/*.pdf' --json > submitted.json

biorigor wait $(python3 -c '
import json
d = json.load(open("submitted.json"))
print(" ".join(x["taskId"] for x in d["submitted"]))') --download ./reports
```

### Poll active tasks

```bash
biorigor status --json | python3 -c '
import json, sys
for t in json.load(sys.stdin):
    print(t["id"], t["status"], t["stage"])'
```

More in [`examples/`](examples/) — a bash loop, a Python client, and a CI-style
submit-and-wait script.

## Choosing a model and engine

```bash
biorigor models
```

```
models:
  * local-model-a    Model A           vision  no-key      engines: pi,claude
    local-model-b    Model B           text    no-key      engines: pi,claude
    remote-model     Model C (remote)  vision  needs-key   engines: pi,claude

engines:
    pi               pi
    claude           Claude Code
```

`--model` / `--harness` default to whatever the server marks as default.
Remote or paid models need `--key`. Both the available models and the engine
names are decided by **your** deployment's `config.json`, not by this client.

## How long does an audit take

| Input | Typical |
|---|---|
| Main PDF only | 20–60 min |
| Main PDF + supplementary + source data | 1–2.5 h |

The server processes **one task at a time** — extra submissions queue.
Runs have a per-task time limit (default 4 h on the reference deployment).
If a run is cut off, the partial report is kept and `report` flags it as incomplete.

## Troubleshooting

```bash
biorigor ping                      # is the server reachable?
biorigor ping https://other.host   # try another URL
biorigor whoami                    # is the token still valid?
```

| Symptom | Fix |
|---|---|
| `no server configured` | pass `--host`, or export `BIORIGOR_HOST` |
| `does not look like a BioRigor server` | wrong URL/scheme, or `/api/health` is blocked by a proxy |
| `HTTP 401` | token expired — `biorigor logout && biorigor login` |
| `HTTP 403` | you can only act on your own tasks (admins can act on all) |
| task ends `error` | `biorigor status <id>` prints the `error` field |

## Development

The whole client is one file. To hack on it:

```bash
git clone git@github.com:LudensZhang/biorigor-cli.git
cd biorigor-cli
./biorigor --help
python3 -m py_compile biorigor
```

There is no build step and no dependency to install.

## License

MIT — see [LICENSE](LICENSE).
