"""Publish and verify host-only physical87 evidence without operating a device.

Generation reads completed observations; it never promotes a partial checklist,
scripted fixture, absent raw capture or unconfigured provider into acceptance.
Run only after the operator has finished the evidence and retention policy.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import math
from pathlib import Path
import subprocess
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EVIDENCE = ROOT / "Verification/Evidence/Physical87"
GENERATED = {"Summary.json", "Comparison.html", "ArtifactInventory.json"}
MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".mp4"}
STATES = {"NOT_RUN", "PASS", "FAIL", "PARTIAL", "BLOCKED_EXTERNAL",
          "BLOCKED_SAFETY", "BLOCKED_ENVIRONMENT"}
MAX_FILES = 20000
MAX_JSON = 40 * 1024 * 1024


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    path = Path(path)
    if path.stat().st_size > MAX_JSON:
        raise ValueError("JSON evidence exceeds the bounded report input")
    return json.loads(path.read_text(encoding="utf-8-sig"),
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=True,
                                    allow_nan=False) + "\n", encoding="utf-8")


def relative_path(base, value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Expected a relative POSIX evidence path")
    path = Path(value)
    target = (base / path).resolve()
    if path.is_absolute() or ".." in path.parts or not target.is_relative_to(base.resolve()):
        raise ValueError("Evidence path escapes its authorized directory")
    return target


def root_binding(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Binding escapes the project")
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path),
            "bytes": path.stat().st_size}


def public_keys(value):
    """Reject accidental credential-bearing fields; never copy private selectors."""
    forbidden = {"serial", "password", "token", "accesstoken", "refreshtoken",
                 "recoverycode", "apikey", "privatekey", "secret", "authorizationtoken"}
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).replace("_", "").replace("-", "").lower() in forbidden and child:
                raise ValueError("Private field is not permitted in public report input")
            public_keys(child)
    elif isinstance(value, list):
        for child in value:
            public_keys(child)


def optional(run, name):
    matches = [p for p in run.rglob(name) if p.is_file()]
    direct = run / name
    if direct in matches:
        return direct, read(direct)
    if len(matches) > 1:
        raise ValueError("Ambiguous optional report: " + name)
    return (matches[0], read(matches[0])) if matches else (None, None)


def validate_checklist(checklist):
    rows = checklist.get("rows", [])
    if len(rows) != 39 or len({r.get("id") for r in rows}) != 39:
        raise ValueError("The physical checklist must retain all39 unique rows")
    if not {"DEV-%02d" % i for i in range(1, 21)} <= {r["id"] for r in rows}:
        raise ValueError("The original20 device-matrix rows are required")
    if any(r.get("status") not in STATES for r in rows):
        raise ValueError("Unrecognized checklist status")
    return rows


def files_for_inventory(run):
    paths = []
    for path in sorted(run.rglob("*")):
        if path.is_symlink():
            raise ValueError("Evidence symlinks are not supported")
        if path.is_file() and path.relative_to(run).as_posix() not in GENERATED:
            paths.append(path)
    if len(paths) > MAX_FILES:
        raise ValueError("Evidence inventory exceeds bounded file count")
    return paths


def inventory(run):
    paths = files_for_inventory(run)
    # One bounded host-only invocation. --no-index also classifies tracked files
    # by the declared retention rules instead of assuming every raw file is kept.
    names = [p.relative_to(ROOT).as_posix() for p in paths]
    payload = b"\0".join(s.encode("utf-8") for s in names) + b"\0"
    result = subprocess.run(["git", "check-ignore", "--no-index", "-z", "--stdin"],
                            cwd=ROOT, input=payload, capture_output=True, timeout=30)
    if result.returncode not in (0, 1):
        raise ValueError("Git retention classification failed")
    ignored = set(result.stdout.decode("utf-8").split("\0"))
    declared = None
    policy_path = run / "RetainedCaptures.json"
    if policy_path.exists():
        policy = read(policy_path)
        declared = set()
        for row in policy.get("paths", policy.get("retained", [])):
            value = row.get("path") if isinstance(row, dict) else row
            if isinstance(value, str) and value.startswith(run.relative_to(ROOT).as_posix() + "/"):
                path = relative_path(ROOT, value)
                if not path.is_relative_to(run):
                    raise ValueError("Retained capture is outside this run")
            else:
                path = relative_path(run, value)
            if path.suffix.lower() not in MEDIA or not path.is_file():
                raise ValueError("Declared retained capture is missing or has an unsupported type")
            if path.relative_to(ROOT).as_posix() in ignored:
                raise ValueError("Declared retained capture is ignored by Git")
            declared.add(path.relative_to(run).as_posix())
        if "paths" not in policy and "retained" not in policy:
            raise ValueError("RetainedCaptures must declare paths or retained")
        public_keys(policy)
    entries = []
    for path, name in zip(paths, names):
        local = path.relative_to(run).as_posix()
        retained = name not in ignored
        if declared is not None and path.suffix.lower() in MEDIA:
            retained = local in declared
        entries.append({"path": local, "bytes": path.stat().st_size,
                        "sha256": sha(path),
                        "retention": "git_retained" if retained else "local_raw"})
    return {"schemaVersion": 1, "checkpoint": 87, "utc": utc(),
            "scope": "Hash inventory of files present at publication, not a claim that local raw files are committed.",
            "excludes": sorted(GENERATED),
            "retentionPolicy": {"method": "RetainedCaptures.json plus Git rules" if declared is not None else "Git rules",
                                "explicitCaptures": root_binding(policy_path) if declared is not None else None,
                                "gitignore": root_binding(ROOT / ".gitignore"),
                                "rawAvailability": "local_raw may be absent in a fresh clone. Retained evidence must remain available; raw availability is checked separately."},
            "counts": dict(Counter(e["retention"] for e in entries)), "files": entries}


def source_binding(target):
    review = read(ROOT / "Verification/Evidence/Review86/Summary.json")
    manifest = relative_path(ROOT, review["sourceManifest"])
    if sha(manifest) != target["sourceSHA256"]:
        raise ValueError("Source manifest differs from the physical target")
    frozen = read(manifest)
    apk = relative_path(ROOT, target["apk"])
    if apk.is_file() and sha(apk) != target["apkSHA256"]:
        raise ValueError("Available APK differs from the physical target")
    return {"checkpoint": target["sourceCheckpoint"],
            "manifest": root_binding(manifest), "inputCount": frozen["inputCount"],
            "currentSourceRehashedByGenerator": False,
            "apk": {"path": target["apk"], "sha256": target["apkSHA256"],
                    "availableAtPublication": apk.is_file(),
                    "bytes": apk.stat().st_size if apk.is_file() else None},
            "note": "The exact frozen input manifest binds the tested APK. --verify independently rehashes the current Unity tree when available."}


def numeric_values(value, prefix="", out=None, limit=240):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise ValueError("Nonfinite performance measurement")
        out.append({"field": prefix, "value": value})
    elif isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() not in {"raw", "rawsamples", "samples", "frames", "rows"}:
                numeric_values(child, prefix + ("." if prefix else "") + str(key), out, limit)
    elif isinstance(value, list) and len(value) <= 24:
        for index, child in enumerate(value):
            numeric_values(child, prefix + "[%d]" % index, out, limit)
    return out


def render(run, data, artifact_inventory):
    entries = {e["path"]: e for e in artifact_inventory["files"]}

    def link(value, title=None):
        if isinstance(value, dict):
            value = value.get("path", "")
        title = title or value
        if not isinstance(value, str):
            return escape(str(title))
        prefix = run.relative_to(ROOT).as_posix() + "/"
        name = value[len(prefix):] if value.startswith(prefix) else value
        entry = entries.get(name)
        if entry and entry["retention"] == "git_retained":
            return '<a href="' + quote(name, safe="/") + '">' + escape(str(title)) + '</a>'
        return escape(str(title)) + (" (local raw; hash retained)" if entry else " (not linked by this inventory)")

    def items(values):
        return "<ul>" + "".join("<li>" + escape(str(v)) + "</li>" for v in values) + "</ul>" if values else ""

    def observations(value):
        if isinstance(value, str):
            return "<p>" + escape(value) + "</p>"
        if isinstance(value, list):
            return items(value)
        return "<pre>" + escape(json.dumps(value, indent=2, ensure_ascii=False)) + "</pre>"

    checklist = data["checklist"]
    rows = []
    for row in checklist["rows"]:
        detail = '<details><summary>' + escape(row["scenario"]) + '</summary><p><b>Acceptance:</b> ' + escape(row["acceptance"]) + '</p>'
        detail += observations(row.get("observations", []))
        if row.get("subresults"):
            detail += '<ul>' + ''.join('<li><b>' + escape(str(s.get("status", ""))) + '</b> ' + escape(str(s.get("name", ""))) + ': ' + escape(str(s.get("observation", ""))) + ' <small>(' + escape(str(s.get("scope", ""))) + ')</small></li>' for s in row["subresults"]) + '</ul>'
        detail += items(row.get("remaining", []))
        if row.get("evidence"):
            detail += '<p>' + ' · '.join(link(e) for e in row["evidence"]) + '</p>'
        detail += '</details>'
        rows.append('<tr><td>' + escape(row["id"]) + '</td><td class="' + escape(row["status"]) + '">' + escape(row["status"]) + '</td><td>' + detail + '</td></tr>')
    target = data["target"]
    summary = data["summary"]
    cards = ''.join('<div class="card"><strong>' + str(count) + '</strong><span>' + escape(status) + '</span></div>' for status, count in sorted(summary["checklistCounts"].items()))
    regression = data["regression"]
    no_moves = data["noMoves"]
    failures = checklist.get("known_failures", [])
    failure_html = ''.join('<article><b>' + escape(str(f.get("id", "Finding"))) + ' — ' + escape(str(f.get("status", ""))) + '</b>' + observations(f.get("observation", f.get("observations", ""))) + '<p>Cause: ' + escape(str(f.get("cause", "not established"))) + '</p></article>' for f in failures)
    performance = data["performance"]
    numeric = numeric_values(performance.get("analysis", {}), limit=40)
    perf_html = '<p>No completed PerformanceAnalysis.json was available at publication.</p>'
    if performance.get("path"):
        perf_html = '<p>' + link(performance["path"], "Performance analysis and limitations") + '</p><table><tr><th>Recorded analysis field</th><th>Value</th></tr>' + ''.join('<tr><td>' + escape(n["field"]) + '</td><td>' + str(n["value"]) + '</td></tr>' for n in numeric) + '</table><p>Field names retain their analysis units and scope. Slow samples and intentional controls remain in the full reports.</p>'
    raw_reports = [name for name, entry in entries.items() if entry["retention"] == "git_retained" and name.startswith("Probes/") and name.endswith(("/Report.json", "/Manifest.json"))]
    perf_html += '<p>' + ' · '.join(link(name) for name in raw_reports) + '</p>'
    ordinary = data["ordinary"]
    ordinary_html = '<p>No separate OrdinarySummary.json was supplied; inspect the checklist observations and individual action records.</p>'
    if ordinary.get("path"):
        ordinary_html = '<p>' + link(ordinary["path"], "Ordinary-phone summary") + '</p>' + observations(ordinary.get("report", {}))
    galleries = []
    for category, label in (("Ordinary/", "Ordinary phone captures"), ("NoMoves/", "Actual Android input in isolated Continue/Shop fixtures"), ("Regression/", "Transient regression captures and review plates")):
        images = []
        for name, entry in entries.items():
            if name.startswith(category) and entry["retention"] == "git_retained" and Path(name).suffix.lower() in MEDIA - {".mp4"}:
                url = quote(name, safe="/")
                images.append('<figure><a href="' + url + '"><img loading="lazy" src="' + url + '" alt="' + escape(name) + '"></a><figcaption>' + escape(name) + '</figcaption></figure>')
        if images:
            galleries.append('<h3>' + label + '</h3><p>A filename or displayed capture is not a pass assertion. Offscreen regression captures have the caveats recorded below.</p><div class="gallery">' + ''.join(images) + '</div>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Heart of the Rain — physical review87</title><style>body{font:16px/1.5 system-ui,sans-serif;background:#102c43;color:#f4f1e9;margin:0 auto;padding:28px;max-width:1400px}a{color:#91dbff;overflow-wrap:anywhere}h1,h2,h3{color:#ffd984}p,li{max-width:100ch}table{border-collapse:collapse;width:100%;margin:18px 0}th,td{border:1px solid #517087;text-align:left;vertical-align:top;padding:10px}th{background:#1d425b}td:first-child{white-space:nowrap}details summary{cursor:pointer}small{color:#bfd1de}.cards{display:flex;flex-wrap:wrap;gap:12px}.card,article{background:#1d425b;padding:14px;border-radius:10px;margin:12px 0}.card strong{display:block;font-size:28px}.card span{font-size:13px}.FAIL{color:#ff9c9c;font-weight:bold}.PASS{color:#a5e6b6}.PARTIAL,.NOT_RUN,[class^=BLOCKED]{color:#ffdc8f}.gallery{display:flex;flex-wrap:wrap;gap:16px}figure{margin:0;width:210px}figure img{width:100%;height:380px;object-fit:contain;background:#081b29}figcaption{font-size:12px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}.notice{border-left:4px solid #ffd984;padding:12px;background:#1d425b}</style><h1>Physical-phone review87</h1><p class="notice">' + escape(summary["status"]) + '. This evidence records scoped tests on one phone. It is not an all-tests pass, human50-level campaign, whole-game smoothness certificate or RuStore release approval.</p><p>' + escape(target["manufacturer"] + ' ' + target["model"] + ' · Android ' + target["props"]["ro.build.version.release"] + ' / API ' + target["props"]["ro.build.version.sdk"] + ' · ' + target["physicalDisplay"]) + '</p><p>Source checkpoint ' + str(target["sourceCheckpoint"]) + '; APK SHA256 <code>' + escape(target["apkSHA256"]) + '</code>.</p><div class="cards">' + cards + '</div><h2>Observed findings and remaining limits</h2>' + failure_html + observations(checklist.get("capture_caveats", [])) + '<p>Externally configured account/social transport, actual payment/ad providers, release signing/legal/moderation and broader device coverage retain their exact checklist status. No successful service test is inferred from a rendered page.</p><h2>Distinct execution scopes</h2><p><b>Transient native regression:</b> ' + escape(str(regression.get("status", "unknown"))) + '; ' + str(regression.get("checks", 0)) + ' checks, ' + str(regression.get("boards", 0)) + ' boards, ' + str(regression.get("actions", 0)) + ' programmatic actions and ' + str(regression.get("clips", 0)) + ' clips. ' + escape(str(regression.get("scope", ""))) + ' ' + link("Regression/Invocation.json", "Invocation") + ' · ' + link("Regression/Native/Regression.json", "Native report") + '</p><p><b>Continue/Shop:</b> ' + escape(str(no_moves.get("status", "unknown"))) + '; ' + str(len(no_moves.get("cases", []))) + ' isolated cases. Actual input counts and state assertions are in ' + link("NoMoves/Summary.json", "the fixture summary") + '.</p><h2>Ordinary phone actions</h2>' + ordinary_html + '<h2>Performance observations</h2>' + perf_html + '<h2>All39 checklist rows</h2><table><tr><th>ID</th><th>Current result</th><th>Acceptance, observations and evidence</th></tr>' + ''.join(rows) + '</table><h2>Retained captures</h2>' + ''.join(galleries) + '<h2>Evidence retention</h2><p>Selected captures and structured reports are retained. Other raw captures may remain only in the original workspace. Their path, size and hash are preserved in the inventory; absence in a fresh clone is not claimed as successful raw verification.</p><p><a href="Summary.json">Summary</a> · <a href="ArtifactInventory.json">Artifact inventory</a> · ' + link("Checklist.json", "Full checklist") + ' · ' + link("RetainedCaptures.json", "Capture retention policy") + '</p></html>\n'


def generate(run):
    target = read(run / "Target.json")
    installation = read(run / "Installation.json")
    regression = read(run / "Regression/Invocation.json")
    native = read(run / "Regression/Native/Regression.json")
    no_moves = read(run / "NoMoves/Summary.json")
    checklist = read(run / "Checklist.json")
    rows = validate_checklist(checklist)
    for value in (target, installation, regression, native, no_moves, checklist):
        public_keys(value)
    if target.get("authorization") != "OWNER_CONNECTED_PHYSICAL_PHONE87":
        raise ValueError("Expected a physical-phone authorization record")
    if installation.get("installedAPK_SHA256") != target["apkSHA256"]:
        raise ValueError("Installed APK identity differs from the target")
    for key in ("checks", "boards", "actions", "clips"):
        if regression.get(key) != native.get(key):
            raise ValueError("Regression wrapper/native count differs")
    analysis_path, analysis = optional(run, "PerformanceAnalysis.json")
    ordinary_path, ordinary = optional(run, "OrdinarySummary.json")
    public_keys(analysis)
    public_keys(ordinary)
    artifacts = inventory(run)
    counts = dict(Counter(r["status"] for r in rows))
    draft = checklist.get("draft", True)
    summary = {"schemaVersion": 1, "checkpoint": 87, "utc": utc(),
               "status": "DRAFT_PHYSICAL_REVIEW87_WITH_OPEN_GATES" if draft else "COMPLETED_PHYSICAL_REVIEW87_WITH_OPEN_GATES",
               "releaseApproved": False, "allChecklistRowsPassed": all(r["status"] == "PASS" for r in rows),
               "wholeGameSmoothnessCertified": False, "humanCampaignCompletedByFixtures": False,
               "checklistCounts": counts, "checklistRowCount": len(rows),
               "scope": "Actual selected physical ARM64 phone, unchanged checkpoint86 APK. Ordinary actions and transient scripted fixtures are separate. Open failures, incomplete variants and external gates are retained.",
               "device": {key: target[key] for key in ("deviceAlias", "model", "manufacturer", "serialSHA256", "physicalDisplay", "densityDpi", "props")},
               "sourceBinding": source_binding(target),
               "regression": {key: regression.get(key) for key in ("status", "nativeStatus", "checks", "boards", "actions", "clips", "ordinaryDataUnchanged", "ordinaryDataUnchangedAfterRelaunch", "scope")},
               "noMoves": {"status": no_moves.get("status"), "cases": len(no_moves.get("cases", [])),
                           "inputCounts": dict(Counter(action.get("kind", "unknown") for case in no_moves.get("cases", []) for action in case.get("inputs", []))),
                           "caseStatuses": dict(Counter(case.get("status", "unknown") for case in no_moves.get("cases", [])))},
               "knownFailures": checklist.get("known_failures", []),
               "captureCaveats": checklist.get("capture_caveats", []),
               "performance": {"analysis": root_binding(analysis_path) if analysis_path else None,
                               "status": analysis.get("status") if isinstance(analysis, dict) else "NOT_SUPPLIED",
                               "numericSummary": numeric_values(analysis) if analysis is not None else []},
               "ordinary": {"summary": root_binding(ordinary_path) if ordinary_path else None,
                            "status": ordinary.get("status") if isinstance(ordinary, dict) else "NOT_SUPPLIED"},
               "tools": [root_binding(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in {".py", ".json", ".txt"}],
               "retention": {"counts": artifacts["counts"], "rawAvailability": artifacts["retentionPolicy"]["rawAvailability"]}}
    data = {"target": target, "regression": regression, "noMoves": no_moves,
            "checklist": checklist, "summary": summary,
            "performance": {"path": analysis_path.relative_to(run).as_posix() if analysis_path else None, "analysis": analysis},
            "ordinary": {"path": ordinary_path.relative_to(run).as_posix() if ordinary_path else None, "report": ordinary}}
    html = render(run, data, artifacts)
    (run / "Comparison.html").write_text(html, encoding="utf-8")
    write(run / "ArtifactInventory.json", artifacts)
    summary["outputs"] = [root_binding(run / name) for name in ("ArtifactInventory.json", "Comparison.html")]
    write(run / "Summary.json", summary)
    print(json.dumps({"status": summary["status"], "checklistCounts": counts,
                      "artifacts": len(artifacts["files"]), "output": (run / "Summary.json").relative_to(ROOT).as_posix()}))


def verify_binding(binding):
    path = relative_path(ROOT, binding["path"])
    if not path.is_file() or sha(path) != binding["sha256"] or ("bytes" in binding and path.stat().st_size != binding["bytes"]):
        raise ValueError("Bound file is missing or changed: " + binding["path"])
    return path


def verify(run, require_raw=False):
    summary = read(run / "Summary.json")
    for binding in summary["outputs"] + summary["tools"]:
        verify_binding(binding)
    artifacts = read(run / "ArtifactInventory.json")
    verify_binding(artifacts["retentionPolicy"]["gitignore"])
    if artifacts["retentionPolicy"].get("explicitCaptures"):
        verify_binding(artifacts["retentionPolicy"]["explicitCaptures"])
    if dict(Counter(e["retention"] for e in artifacts["files"])) != artifacts["counts"]:
        raise ValueError("Artifact retention counts differ")
    counts = Counter()
    seen = set()
    for entry in artifacts["files"]:
        if entry["path"] in seen or entry["path"] in GENERATED:
            raise ValueError("Duplicate or recursive inventory entry")
        seen.add(entry["path"])
        path = relative_path(run, entry["path"])
        if entry["retention"] not in {"git_retained", "local_raw"}:
            raise ValueError("Unknown retention classification")
        if not path.is_file():
            if entry["retention"] == "git_retained" or require_raw:
                raise ValueError("Required evidence file is missing: " + entry["path"])
            counts["localRawMissingNotVerified"] += 1
            continue
        if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
            raise ValueError("Evidence file changed: " + entry["path"])
        counts["retainedVerified" if entry["retention"] == "git_retained" else "localRawPresentVerified"] += 1
    checklist = read(run / "Checklist.json")
    rows = validate_checklist(checklist)
    if dict(Counter(r["status"] for r in rows)) != summary["checklistCounts"]:
        raise ValueError("Published checklist counts differ")
    source = summary["sourceBinding"]
    manifest = verify_binding(source["manifest"])
    frozen = read(manifest)
    if len(frozen["files"]) != source["inputCount"]:
        raise ValueError("Source input count differs")
    existing = set()
    for category in ("Assets", "Packages", "ProjectSettings"):
        directory = ROOT / "Unity" / category
        if directory.exists():
            existing.update(p.relative_to(ROOT).as_posix() for p in directory.rglob("*") if p.is_file())
    source_status = "UNAVAILABLE_NOT_VERIFIED"
    if existing:
        if existing != set(frozen["files"]):
            raise ValueError("Current Unity source inventory differs")
        for name, binding in frozen["files"].items():
            verify_binding({"path": name, **binding})
        source_status = "ALL_CURRENT_UNITY_INPUTS_VERIFIED"
    apk = relative_path(ROOT, source["apk"]["path"])
    apk_status = "UNAVAILABLE_NOT_VERIFIED"
    if apk.is_file():
        verify_binding({key: value for key, value in source["apk"].items() if key in {"path", "sha256", "bytes"} and value is not None})
        apk_status = "AVAILABLE_APK_VERIFIED"
    print(json.dumps({"status": "PASS_PHYSICAL_REPORT_BINDINGS_ONLY87", "evidence": dict(counts),
                      "source": source_status, "apk": apk_status,
                      "scope": "Host hash/inventory verification only. Missing local raw files are not verified. This does not rerun device tests or approve release."}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--verify", action="store_true", help="Read-only verification; never rewrites the reports")
    parser.add_argument("--require-raw", action="store_true", help="With --verify, require every local raw file as well")
    args = parser.parse_args()
    run = args.out.resolve()
    if not run.is_relative_to(EVIDENCE.resolve()) or run == EVIDENCE.resolve() or not run.is_dir():
        parser.error("Select an existing individual Physical87 run directory")
    if args.require_raw and not args.verify:
        parser.error("--require-raw applies only to --verify")
    verify(run, args.require_raw) if args.verify else generate(run)


if __name__ == "__main__":
    main()
