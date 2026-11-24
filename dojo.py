#!/usr/bin/env python3
"""netsec-dojo: a local lab engine for learning networking and security.

Each lab is a folder under labs/ holding:
  lab.json            metadata, tasks, hints, solutions
  lesson.md           the teaching text
  docker-compose.yml  the lab network (containers = hosts, routers, targets)
  files/              scripts mounted read-only at /lab inside every node

Standard library only. Needs Docker Desktop running.
"""
import argparse
import html
import json
import os
import random
import re
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABS_DIR = ROOT / "labs"
STATE_DIR = ROOT / ".state"
PROGRESS_FILE = STATE_DIR / "progress.json"
TOOLBOX = "dojo-toolbox:latest"
UI_PORT = 8377
_lock = threading.Lock()


# ---------------------------------------------------------------- helpers

def run(cmd, timeout=120, env=None):
    """Run a command, return (exit_code, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=env)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"
    except FileNotFoundError:
        return 127, "", f"{cmd[0]} not found"


def docker_ok():
    return run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=20)[0] == 0


def load_labs():
    labs = []
    for d in sorted(LABS_DIR.iterdir()):
        f = d / "lab.json"
        if not f.is_file():
            continue
        lab = json.loads(f.read_text(encoding="utf-8"))
        lab["dir"] = d
        lab["id"] = d.name
        lab["num"] = d.name.split("-")[0]
        lab["project"] = f"dojo-{lab['num']}"
        labs.append(lab)
    return labs


def find_lab(key):
    labs = load_labs()
    key = str(key).lower()
    for lab in labs:
        if key == lab["id"] or key.lstrip("0") == lab["num"].lstrip("0"):
            return lab
    hits = [l for l in labs if key in l["id"]]
    if len(hits) == 1:
        return hits[0]
    raise SystemExit(f"No single lab matches '{key}'. Try: dojo list")


def container(lab, node):
    return f"{lab['project']}-{node}-1"


def running_projects():
    code, out, _ = run(["docker", "ps", "--format",
                        '{{.Label "com.docker.compose.project"}}'], timeout=20)
    return set(out.split()) if code == 0 else set()


def is_running(lab):
    return lab["project"] in running_projects()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def lab_state(lab):
    return load_json(STATE_DIR / f"{lab['id']}.json", {})


def lab_vars(lab):
    return lab_state(lab).get("vars", {})


def sub(text, variables):
    """Replace {{NAME}} placeholders with this run's generated values."""
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables.get(m.group(1), m.group(0))), text)


def gen_vars(lab):
    out = {}
    r = random.SystemRandom()
    for name, spec in lab.get("vars", {}).items():
        kind = spec["type"]
        if kind == "flag":
            out[name] = "DOJO{" + secrets.token_hex(6) + "}"
        elif kind == "int":
            out[name] = str(r.randint(spec["min"], spec["max"]))
        elif kind == "choice":
            out[name] = r.choice(spec["options"])
        elif kind == "ip":
            out[name] = "%d.%d.%d.%d" % (r.choice([45, 62, 91, 103, 141, 176, 185, 193]),
                                         r.randint(1, 254), r.randint(1, 254), r.randint(2, 254))
        else:
            raise SystemExit(f"unknown var type {kind}")
    return out


def exec_in(lab, node, cmd, timeout=40):
    return run(["docker", "exec", container(lab, node), "bash", "-c", cmd], timeout=timeout)


# ---------------------------------------------------------------- progress

def load_progress():
    return load_json(PROGRESS_FILE, {})


def mark_done(lab, task_id):
    with _lock:
        p = load_progress()
        p.setdefault(lab["id"], {}).setdefault(task_id, time.strftime("%Y-%m-%d %H:%M:%S"))
        save_json(PROGRESS_FILE, p)


def done_tasks(lab):
    return set(load_progress().get(lab["id"], {}))


# ---------------------------------------------------------------- lab lifecycle

def ensure_toolbox(log=print):
    if run(["docker", "image", "inspect", TOOLBOX], timeout=20)[0] == 0:
        return
    log("Building the lab tools image (first run only, takes a few minutes)...")
    code, out, err = run(["docker", "build", "-t", TOOLBOX, str(ROOT / "images" / "toolbox")],
                         timeout=1800)
    if code != 0:
        raise RuntimeError("tools image build failed:\n" + err[-2000:])


def start_lab(lab, log=print):
    if not docker_ok():
        raise RuntimeError("Docker is not running. Start Docker Desktop and try again.")
    ensure_toolbox(log)
    stop_lab(lab)
    variables = gen_vars(lab)
    save_json(STATE_DIR / f"{lab['id']}.json", {"vars": variables, "started": time.time()})
    env = dict(os.environ)
    env.update({f"DOJO_{k}": v for k, v in variables.items()})
    log(f"Starting lab {lab['id']}...")
    code, out, err = run(["docker", "compose", "-p", lab["project"], "-f",
                          str(lab["dir"] / "docker-compose.yml"), "up", "-d"],
                         timeout=600, env=env)
    if code != 0:
        raise RuntimeError("could not start lab:\n" + err[-2000:])
    deadline = time.time() + 45
    pending = list(lab.get("ready", []))
    while pending and time.time() < deadline:
        pending = [c for c in pending
                   if exec_in(lab, c["node"], sub(c["cmd"], variables), timeout=15)[0] != 0]
        if pending:
            time.sleep(1)
    if pending:
        raise RuntimeError("lab started but services did not come up: "
                           + ", ".join(c["node"] for c in pending))


def stop_lab(lab):
    run(["docker", "compose", "-p", lab["project"], "down", "-v", "--remove-orphans", "-t", "1"],
        timeout=180)


# ---------------------------------------------------------------- checking

def normalize(value, task):
    v = str(value).strip().strip("\"'").lower()
    v = re.sub(r"\s+", "" if task.get("strip_spaces") else " ", v)
    return v


def expected_answers(lab, task, variables):
    if "answer_cmd" in task:
        c = task["answer_cmd"]
        code, out, _ = exec_in(lab, c["node"], sub(c["cmd"], variables))
        lines = [l for l in out.strip().splitlines() if l.strip()]
        return [lines[-1].strip()] if code == 0 and lines else []
    ans = task["answer"]
    return [sub(a, variables) for a in (ans if isinstance(ans, list) else [ans])]


def check_answer(lab, task, value):
    variables = lab_vars(lab)
    if ("answer_cmd" in task or "{{" in json.dumps(task["answer"] if "answer" in task else "")) \
            and not is_running(lab):
        return False, "Start the lab first: this answer is different on every run."
    good = {normalize(a, task) for a in expected_answers(lab, task, variables)}
    if normalize(value, task) in good:
        mark_done(lab, task["id"])
        return True, "Correct."
    return False, "Not quite."


def check_state(lab, task, record=True):
    """A state task passes when every check behaves as expected."""
    if not is_running(lab):
        return False, "The lab is not running."
    variables = lab_vars(lab)
    for c in task["checks"]:
        code, _, _ = exec_in(lab, c["node"], sub(c["cmd"], variables), timeout=30)
        want_ok = c.get("expect", "ok") == "ok"
        if (code == 0) != want_ok:
            return False, c.get("fail_msg", "Not there yet.")
    if record:
        mark_done(lab, task["id"])
    return True, "Passed."


# ---------------------------------------------------------------- CLI commands

def cmd_setup(_):
    if not docker_ok():
        raise SystemExit("Docker is not running. Start Docker Desktop first.")
    ensure_toolbox()
    print("Ready. Next: dojo list")


def cmd_list(_):
    up = running_projects()
    module = None
    for lab in load_labs():
        if lab["module"] != module:
            module = lab["module"]
            print(f"\n{module}")
        done = len(done_tasks(lab) & {t["id"] for t in lab["tasks"]})
        mark = "RUNNING" if lab["project"] in up else ""
        print(f"  {lab['num']}  {lab['title']:<44} {done}/{len(lab['tasks'])} tasks  {mark}")
    print()


def briefing(lab):
    print(f"\n{lab['title']}  (lab {lab['num']})")
    print("Hosts you can open a shell on:")
    for node, desc in lab["nodes"].items():
        print(f"  dojo shell {lab['num']} {node:<10} {desc}")
    print(f"\nTasks:    dojo tasks {lab['num']}")
    print(f"Check:    dojo check {lab['num']}")
    print(f"Lesson:   labs/{lab['id']}/lesson.md  (or run: dojo serve)\n")


def cmd_start(a):
    lab = find_lab(a.lab)
    others = running_projects() - {lab["project"]}
    others = sorted(p for p in others if p.startswith("dojo-"))
    if others:
        print(f"Note: other labs still running ({', '.join(others)}). Stop them with: dojo stop --all")
    try:
        start_lab(lab)
    except RuntimeError as e:
        raise SystemExit(str(e))
    briefing(lab)


def cmd_stop(a):
    if a.all or not a.lab:
        for lab in load_labs():
            if is_running(lab):
                print(f"Stopping {lab['id']}")
                stop_lab(lab)
        return
    lab = find_lab(a.lab)
    stop_lab(lab)
    print(f"Stopped {lab['id']}")


def cmd_shell(a):
    lab = find_lab(a.lab)
    node = a.node or lab.get("default_node") or next(iter(lab["nodes"]))
    if node not in lab["nodes"]:
        raise SystemExit(f"No host '{node}' in this lab. Hosts: {', '.join(lab['nodes'])}")
    if not is_running(lab):
        raise SystemExit(f"Lab is not running. Start it with: dojo start {lab['num']}")
    sys.exit(subprocess.call(["docker", "exec", "-it", container(lab, node), "bash"]))


def cmd_tasks(a):
    lab = find_lab(a.lab)
    done = done_tasks(lab)
    variables = lab_vars(lab)
    print(f"\n{lab['title']}\n")
    for t in lab["tasks"]:
        box = "[x]" if t["id"] in done else "[ ]"
        kind = "do" if t["type"] == "state" else "answer"
        print(f"{box} {t['id']} ({kind}) {t['title']}")
        print(f"      {sub(strip_md(t['text']), variables)}\n")
    print(f"Answer a question:  dojo answer {lab['num']} <task> <value>")
    print(f"Check 'do' tasks:   dojo check {lab['num']}")
    print(f"Stuck:              dojo hint {lab['num']} <task>\n")


def strip_md(text):
    return re.sub(r"[`*]", "", text)


def cmd_check(a):
    lab = find_lab(a.lab)
    done = done_tasks(lab)
    for t in lab["tasks"]:
        if t["type"] == "state":
            ok, msg = check_state(lab, t)
            print(f"{'[x]' if ok else '[ ]'} {t['id']} {t['title']}: {msg}")
        else:
            print(f"{'[x]' if t['id'] in done else '[ ]'} {t['id']} {t['title']}"
                  f"{'' if t['id'] in done else ': answer with dojo answer'}")


def get_task(lab, task_id):
    for t in lab["tasks"]:
        if t["id"] == task_id:
            return t
    raise SystemExit(f"No task '{task_id}'. Tasks: {', '.join(t['id'] for t in lab['tasks'])}")


def cmd_answer(a):
    lab = find_lab(a.lab)
    task = get_task(lab, a.task)
    if task["type"] != "answer":
        raise SystemExit("That task is checked by doing it, not by an answer. Run: dojo check")
    ok, msg = check_answer(lab, task, " ".join(a.value))
    print(msg)


def cmd_hint(a):
    lab = find_lab(a.lab)
    task = get_task(lab, a.task)
    hints = task.get("hints", [])
    n = min(a.n, len(hints))
    for i, h in enumerate(hints[:n], 1):
        print(f"Hint {i}/{len(hints)}: {sub(strip_md(h), lab_vars(lab))}")
    if n < len(hints):
        print(f"More: dojo hint {lab['num']} {task['id']} -n {n + 1}")


def cmd_status(_):
    up = [l for l in load_labs() if is_running(l)]
    if not up:
        print("No labs running.")
    for lab in up:
        print(f"{lab['id']} is running: {', '.join(lab['nodes'])}")


# ---------------------------------------------------------------- selftest

def selftest_lab(lab):
    """Start the lab, prove each task fails before and passes after its solution."""
    problems = []
    try:
        start_lab(lab, log=lambda m: None)
    except RuntimeError as e:
        return [f"start failed: {e}"]
    variables = lab_vars(lab)
    try:
        for t in lab["tasks"]:
            if t["type"] == "state" and not t.get("initially_ok"):
                if check_state(lab, t, record=False)[0]:
                    problems.append(f"{t['id']}: passes before the learner does anything")
        for t in lab["tasks"]:
            sol = t.get("solution", {})
            for step in sol.get("steps", []):
                code, out, err = exec_in(lab, step["node"], sub(step["cmd"], variables), timeout=120)
                if code != 0:
                    problems.append(f"{t['id']}: solution step failed on {step['node']}: "
                                    f"{step['cmd']!r} -> {(err or out).strip()[-300:]}")
            if t["type"] == "state":
                ok = False
                for _ in range(5):
                    ok, msg = check_state(lab, t, record=False)
                    if ok:
                        break
                    time.sleep(1)
                if not ok:
                    problems.append(f"{t['id']}: still failing after solution ({msg})")
            else:
                if "answer_cmd" in sol:
                    c = sol["answer_cmd"]
                    code, out, err = exec_in(lab, c["node"], sub(c["cmd"], variables), timeout=180)
                    lines = [l for l in out.strip().splitlines() if l.strip()]
                    got = lines[-1].strip() if lines else ""
                else:
                    got = sub(str(sol.get("answer", "")), variables)
                good = {normalize(x, t) for x in expected_answers(lab, t, variables)}
                if not good:
                    problems.append(f"{t['id']}: engine could not compute the expected answer")
                elif normalize(got, t) not in good:
                    problems.append(f"{t['id']}: solution produced {got!r}, expected one of {sorted(good)}")
    finally:
        stop_lab(lab)
    return problems


def cmd_selftest(a):
    labs = [find_lab(k) for k in a.labs] if a.labs else load_labs()
    failed = 0
    for lab in labs:
        problems = selftest_lab(lab)
        print(f"{'FAIL' if problems else 'PASS'}  {lab['id']}")
        for p in problems:
            print(f"      - {p}")
        failed += bool(problems)
        time.sleep(2)  # let the laptop breathe between labs
    sys.exit(1 if failed else 0)


# ---------------------------------------------------------------- markdown

def md_inline(s):
    s = html.escape(s, quote=False)
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    s = re.sub(r"`([^`]+)`", stash, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", s)


def md_to_html(text):
    lines = text.replace("\r\n", "\n").split("\n")
    out, para, i = [], [], 0

    def flush():
        if para:
            out.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(block), quote=False) + "</code></pre>")
        elif re.match(r"#{1,4} ", line):
            flush()
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{md_inline(line[level + 1:].strip())}</h{level}>")
        elif re.match(r"\s*([-*]|\d+\.) ", line):
            flush()
            tag = "ol" if re.match(r"\s*\d+\. ", line) else "ul"
            items = []
            while i < len(lines) and (re.match(r"\s*([-*]|\d+\.) ", lines[i])
                                      or (lines[i].startswith("  ") and lines[i].strip())):
                if re.match(r"\s*([-*]|\d+\.) ", lines[i]):
                    items.append(re.sub(r"^\s*([-*]|\d+\.) ", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{md_inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        elif line.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> "))
                i += 1
            out.append("<blockquote>" + md_inline(" ".join(quote)) + "</blockquote>")
            continue
        elif line.startswith("|") and i + 1 < len(lines) and re.match(r"\|[\s:|-]+\|?\s*$", lines[i + 1]):
            flush()
            cells = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
            head = cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{md_inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>"
                                 for r in rows) + "</tbody></table>")
            continue
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


# ---------------------------------------------------------------- web UI

def api_lab(lab, up):
    variables = lab_vars(lab) if lab["project"] in up else {}
    done = done_tasks(lab)
    lesson = lab["dir"] / "lesson.md"
    return {
        "id": lab["id"], "num": lab["num"], "title": lab["title"], "module": lab["module"],
        "minutes": lab.get("minutes"), "summary": lab.get("summary", ""),
        "running": lab["project"] in up,
        "nodes": [{"name": n, "desc": d, "cmd": f"docker exec -it {container(lab, n)} bash"}
                  for n, d in lab["nodes"].items()],
        "links": lab.get("links", []),
        "lesson": md_to_html(lesson.read_text(encoding="utf-8")) if lesson.is_file() else "",
        "tasks": [{"id": t["id"], "title": t["title"], "type": t["type"],
                   "text": md_to_html(sub(t["text"], variables)),
                   "done": t["id"] in done, "hints": len(t.get("hints", [])),
                   "has_solution": "solution" in t} for t in lab["tasks"]],
    }


def solution_html(lab, task):
    variables = lab_vars(lab)
    sol = task.get("solution", {})
    parts = []
    if sol.get("note"):
        parts.append(md_to_html(sub(sol["note"], variables)))
    steps = list(sol.get("steps", []))
    if "answer_cmd" in sol:
        steps.append(sol["answer_cmd"])
    for s in steps:
        parts.append(f"<p>On <strong>{html.escape(s['node'])}</strong>:</p><pre><code>"
                     + html.escape(sub(s["cmd"], variables), quote=False) + "</code></pre>")
    return "\n".join(parts) or "<p>No written solution for this one.</p>"


class Handler(BaseHTTPRequestHandler):
    server_version = "dojo"

    def log_message(self, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def host_ok(self):
        # Local page only: refuse other Host names (DNS rebinding) and plain cross-site POSTs.
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self.host_ok():
            return self.send_json({"error": "forbidden"}, 403)
        if self.path in ("/", "/index.html"):
            body = (ROOT / "ui" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return self.wfile.write(body)
        if self.path == "/api/state":
            code, out, _ = run(["docker", "ps", "--format", '{{.Label "com.docker.compose.project"}}'],
                               timeout=20)
            up = set(out.split()) if code == 0 else set()
            return self.send_json({"docker": code == 0, "labs": [api_lab(l, up) for l in load_labs()]})
        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self.host_ok() or self.headers.get("X-Dojo") != "1":
            return self.send_json({"error": "forbidden"}, 403)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self.send_json({"error": "bad json"}, 400)
        m = re.fullmatch(r"/api/lab/([\w-]+)/(\w+)", self.path)
        labs = {l["id"]: l for l in load_labs()}
        if not m or m.group(1) not in labs:
            return self.send_json({"error": "not found"}, 404)
        lab, action = labs[m.group(1)], m.group(2)
        try:
            if action == "start":
                start_lab(lab, log=lambda m: None)
                return self.send_json({"ok": True})
            if action == "stop":
                stop_lab(lab)
                return self.send_json({"ok": True})
            if action == "terminal":
                node = body.get("node")
                if node not in lab["nodes"] or not is_running(lab):
                    return self.send_json({"ok": False, "msg": "Start the lab first."})
                if os.name == "nt":
                    subprocess.Popen(["cmd", "/c", "start", f"{node} - lab {lab['num']}",
                                      "docker", "exec", "-it", container(lab, node), "bash"])
                    return self.send_json({"ok": True})
                return self.send_json({"ok": False, "msg": "Copy the command into a terminal."})
            tasks = {t["id"]: t for t in lab["tasks"]}
            task = tasks.get(body.get("task"))
            if not task:
                return self.send_json({"error": "no such task"}, 404)
            if action == "check":
                ok, msg = (check_state(lab, task) if task["type"] == "state"
                           else check_answer(lab, task, body.get("value", "")))
                return self.send_json({"ok": ok, "msg": msg})
            if action == "hint":
                hints = task.get("hints", [])
                n = max(0, min(int(body.get("n", 1)), len(hints)))
                return self.send_json({"hints": [md_to_html(sub(h, lab_vars(lab))) for h in hints[:n]],
                                       "total": len(hints)})
            if action == "solution":
                return self.send_json({"html": solution_html(lab, task)})
        except RuntimeError as e:
            return self.send_json({"ok": False, "msg": str(e)})
        self.send_json({"error": "not found"}, 404)


def cmd_serve(a):
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"netsec-dojo is at http://127.0.0.1:{a.port}  (Ctrl+C to quit)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------- main

def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="dojo", description="Networking and security labs on your own machine.")
    sp = ap.add_subparsers(dest="command", required=True)
    sp.add_parser("setup", help="build the lab tools image").set_defaults(fn=cmd_setup)
    sp.add_parser("list", help="show all labs and your progress").set_defaults(fn=cmd_list)
    sp.add_parser("status", help="show running labs").set_defaults(fn=cmd_status)
    p = sp.add_parser("start", help="start (or restart from scratch) a lab")
    p.add_argument("lab"); p.set_defaults(fn=cmd_start)
    p = sp.add_parser("stop", help="stop a lab, or all labs")
    p.add_argument("lab", nargs="?"); p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_stop)
    p = sp.add_parser("shell", help="open a shell on a lab host")
    p.add_argument("lab"); p.add_argument("node", nargs="?"); p.set_defaults(fn=cmd_shell)
    p = sp.add_parser("tasks", help="show a lab's tasks")
    p.add_argument("lab"); p.set_defaults(fn=cmd_tasks)
    p = sp.add_parser("check", help="check the hands-on tasks of a lab")
    p.add_argument("lab"); p.set_defaults(fn=cmd_check)
    p = sp.add_parser("answer", help="answer a question task")
    p.add_argument("lab"); p.add_argument("task"); p.add_argument("value", nargs="+"); p.set_defaults(fn=cmd_answer)
    p = sp.add_parser("hint", help="get a hint for a task")
    p.add_argument("lab"); p.add_argument("task"); p.add_argument("-n", type=int, default=1); p.set_defaults(fn=cmd_hint)
    p = sp.add_parser("serve", help="open the lesson and progress page")
    p.add_argument("--port", type=int, default=UI_PORT); p.set_defaults(fn=cmd_serve)
    p = sp.add_parser("selftest", help="verify labs work by running their solutions")
    p.add_argument("labs", nargs="*"); p.set_defaults(fn=cmd_selftest)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
