ts: 2026-08-04T21:00:30Z
commit: a290d17 (HEAD = baseline main; restructure UNCOMMITTED on `restructure/intent-plane` at capture)
session: intent-plane repositioning, Task 10 acceptance (closer run, same day)
status: verified

fact: The first real execution of `treasury/quickstart.sh` (under WSL -- the
`.ps1` twin had run many times, the `.sh` twin never) destroyed the Windows
scorer venv. Chain: the script tested for `.venv/bin/python`; a venv built by
the Windows twin has a `Scripts/` layout and no `bin/`, so the script judged a
perfectly healthy venv absent -- and then ran `python3 -m venv` INTO that same
existing directory. This WSL has no ensurepip, so the bootstrap failed, but
not before venv creation had rewritten `pyvenv.cfg` (`home = /usr/bin`) and
injected `bin/` and a `lib64` symlink into the Windows venv. The damage was
INVISIBLE to `git status`: `.venv` is gitignored, so a bootstrap writing into
a shared gitignored directory can break the OTHER platform's lane without
touching a single tracked file. The general lesson: the second platform's
first execution is where cross-platform bootstrap assumptions get audited --
"portable twin maintained since T7" meant nothing until the `.sh` twin
actually ran, and its first run was destructive.

Fix pattern (applied in `treasury/quickstart.sh`, closer-fixed, re-verified):
(1) never re-venv an existing directory -- guard on `.venv` existing at all,
not on the platform-specific interpreter path; (2) on bootstrap failure leave
no half-built venv behind (`rm -rf` the partial); (3) fall back EXPLICITLY --
system `python3` with `src/` on `PYTHONPATH`, only after proving the deps
import -- or exit red; never fall through silently.

Detection pattern: after the FIRST cross-platform execution of any bootstrap,
re-run the other platform's lane before trusting the tree. Only the lane-2
re-run (Windows pytest) could show the damage here, and only because the venv
had been backed up (`pyvenv.cfg`) before the run on the anticipated risk.

basis: T10 closer transcripts (`.git/sdd/task-10-gates-report.md`, lane 7),
2026-08-04. First attempt: failed at "ensurepip is not available";
`pyvenv.cfg` afterwards read `home = /usr/bin` with injected `bin/` + `lib64`.
Recovery: original `pyvenv.cfg` restored, injected entries removed, Windows
lane re-run -> `42 passed, 5 skipped` (repair confirmed). Second attempt,
post-fix: `RESULT: 6/6 probes passed`, `EXITCODE=0`, and the post-run venv
state confirmed clean (Windows layout, Windows `pyvenv.cfg`). Line endings,
curl, and fractional sleep were each ruled OUT first.

re-verify: with a Windows-built `core/scorer/.venv` present, run
`wsl -e bash -lc 'cd /mnt/c/Users/hossa/dev/treasury-intent-controller && PATH=/usr/local/go/bin:$PATH ./treasury/quickstart.sh'`
-- expect the `[setup] no POSIX venv here - using python3 with src/ on
PYTHONPATH` fallback line, `RESULT: 6/6 probes passed`, exit 0, and
`core/scorer/.venv/pyvenv.cfg` still naming the Windows home afterwards; then
the Windows lane still at `42 passed, 5 skipped`.
