"""Seal existing Review126 evidence; never run providers, builds or migrations."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "Verification/Evidence/Review126"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read(relative: str) -> dict:
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8-sig"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-receipt", help="Existing sanitized receipt relative to Review126 evidence")
    parser.add_argument("--worker-receipt", help="Existing sanitized LocalService observation relative to Review126 evidence")
    parser.add_argument("--deployment-receipt", help="Existing sanitized successful cutover receipt relative to Review126 evidence")
    args = parser.parse_args()
    backend = read("Backend/Full02/Service_Tests.json")
    assert backend["status"] == "PASS_BACKEND_SERVICE_TESTS"
    assert backend["tests"] == backend["executedTests"] == len(backend["passed"]) == 959
    assert not backend["failures"] and not backend["errors"] and not backend["skipped"]
    assert backend["actualPinnedWorkerIntegration"] is True
    pins = backend["sourceSHA256"]
    assert len(pins) == 179 and pins == backend["sourceSHA256After"]
    changed = [name for name, sha in pins.items() if digest(ROOT / name) != sha]
    assert not changed, changed
    published = read("Android/PublishedApk126.json")
    apk = ROOT / published["apk"]
    assert digest(apk) == published["sha256"]
    assert apk.stat().st_size == published["bytes"]
    build = read("Android/SignedBuild01/Native.json")
    static = read("Android/SignedBuild01/Static/Values02/Audit.json")
    assert build["apkSHA256"] == static["apkSHA256"] == published["sha256"]
    assert build["status"] == "PASS_COMBINED_MONETIZATION126_ANDROID_BUILD"
    assert static["status"] == "PASS_COMBINED_APK126"
    bundle = read("Deployment/Bundle02/Bundle126.json")
    bundle_changed = [name for name, sha in bundle["filesSHA256"].items() if digest(ROOT / name) != sha]
    assert not bundle_changed, bundle_changed
    host = read(args.host_receipt) if args.host_receipt else None
    worker = read(args.worker_receipt) if args.worker_receipt else None
    worker_result = worker["receipt"]["qualifier"] if worker else None
    if worker_result:
        assert worker_result["status"] == "PASS_LOCAL_SERVICE_WORKER_SMOKE126"
        assert worker_result["executionAccountIsLocalService"] is worker_result["qualifiedForLocalService"] is True
        assert worker["receipt"]["liveAuthorityFactsUnchanged"] is True
    deployment = read(args.deployment_receipt) if args.deployment_receipt else None
    deployed = deployment is not None
    if deployed:
        assert deployment["status"] == "completed_same_wallet_staging_sdk126"
        receipt = deployment["receipt"]
        assert receipt["exit"]["exitCode"] == 0 and not receipt["validationFailures"]
        assert receipt["partialOrInvalidLines"] == 0
        complete = receipt["complete"]
        assert complete["code"] == "SAME_WALLET_STAGING_SDK126_CONFIGURED"
        assert complete["schemaVersion"] == 125 and complete["verificationMode"] == "sdk_client_reported"
        assert complete["adsEnabled"] is complete["vkEnabled"] is complete["qualifiedLegacyReplayConfigured"] is True
        assert complete["productionEnabled"] is complete["databaseReplaced"] is False
    links = [
        ("Backend: 959 passed with real pinned worker", "Backend/Full02/Service_Tests.json"),
        ("Backend focused closure and external fixtures", "Backend/FinalFocused126.json"),
        ("Operations compatibility", "Operations/Compatibility03.json"),
        ("Native advertising: 853 assertions", "Advertising/Advertising126Summary.json"),
        ("SDK guard: 198 assertions", "Toolchain/UpmManifest126Summary.json"),
        ("Actual signed Android build", "Android/SignedBuild01/Native.json"),
        ("Actual APK: 31 static checks", "Android/SignedBuild01/Static/Values02/Audit.json"),
        ("Independent APK/source seal and warning classification", "Android/IndependentSignedApk126.json"),
        ("Published APK descriptor", "Android/PublishedApk126.json"),
        ("Pinned backend source bundle", "Deployment/Bundle02/Bundle126.json"),
        ("Read-only original VPS inventory", "Operations/VpsReadOnlyInventory126.json"),
        ("Actual VPS: 26 unchanged focused tests", "Operations/VpsSourceQualification126.json"),
        ("Constrained original50 worker/client source compatibility", "Deployment/Worker01/SourceSemantics126.json"),
        ("LocalService qualification plan", "Deployment/Worker01/QualificationPlan126.json"),
        ("Owner-confirmed VK inputs", "VkOwnerInputs126.json"),
        ("Root reviewed cutover decision", "Operations/RootCutoverDecision126.json"),
        ("Independent cutover review", "Operations/IndependentCutoverReview126.json"),
        ("Final owned-source and frozen APK scope", "Android/FinalSnapshotScope126.json"),
        ("Complete Main path inventory", "Android/FinalSnapshotInventory126.json"),
    ]
    if args.host_receipt:
        links.append(("Latest hosted acceptance receipt", args.host_receipt))
    if args.worker_receipt:
        links.append(("Actual scoped LocalService worker qualification", args.worker_receipt))
    if args.deployment_receipt:
        links.append(("Actual same-wallet staging cutover", args.deployment_receipt))
    for _, relative in links:
        target = (EVIDENCE / relative).resolve()
        assert target.is_relative_to(EVIDENCE.resolve()) and target.is_file(), relative
    summary = {
        "version": 1,
        "kind": "HeartOfTheRainReview126",
        "utc": datetime.now(timezone.utc).isoformat(),
        "status": "SANDBOX_DEPLOYED_WITH_OPEN_PROVIDER_DEVICE_PRODUCTION_GATES" if deployed else ("SIGNED_SANDBOX_BUILT_WITH_OPEN_HOST_DEVICE_PROVIDER_GATES" if host is None else "SIGNED_SANDBOX_BUILT_HOST_RECEIPT_ATTACHED_REVIEW_GATES"),
        "productionApproved": False,
        "backend": {"executed": 959, "passed": 959, "failures": 0, "errors": 0, "skipped": 0, "actualPinnedWorkerIntegration": True, "currentSourcePins": 179, "changedSourcePins": changed},
        "nativeAdvertisingAssertions": 853,
        "nativeSdkGuardAssertions": 198,
        "countsOverlapDoNotSum": True,
        "apk": published,
        "hostReceipt": args.host_receipt,
        "hostStatus": "LIVE_SCHEMA125_SDK_ADS_VK_LEGACY_REPLAY_ENABLED_SANDBOX" if deployed else (host.get("status") if host else "SOURCE_STAGED_INACTIVE_SCHEMA15_LIVE_LAST_VERIFIED"),
        "deploymentReceipt": args.deployment_receipt,
        "deploymentVerified": deployed,
        "hostedSchema": 125 if deployed else 15,
        "hostedVkApplicationId": "54867814" if deployed else None,
        "hostedVkCallback": "https://api.novamind-it.ru/v1/identity/vk/callback" if deployed else None,
        "hostedSdkApplicationId": "2063777840" if deployed else None,
        "hostedSandboxProducts": 12 if deployed else 0,
        "hostedAdPolicy": {"coins": 400, "dailyLimit": 3, "cooldownSeconds": 600} if deployed else None,
        "workerReceipt": args.worker_receipt,
        "workerLocalServiceQualified": bool(worker_result),
        "workerQualification": worker_result,
        "actualProviderPaymentVerified": False,
        "actualRewardedPlaybackVerified": False,
        "actualVkAuthenticationVerified": False,
        "deviceInstalledByThisReview": False,
        "workerScope": "Approved83 artifact; source compatibility constrained to original50/defaultfalse growth flag; one actual LocalService L1 check passed, not full-corpus/capacity/WindowsCore qualification." if worker_result else "Approved83 artifact; source compatibility constrained to original50/defaultfalse growth flag; LocalService receipt required before host replay activation.",
        "openFindings": [
            "Installed monitor Windows8.3 alias/ownership-path portability gap; canonical per-process retest does not implement broad alias support.",
            "Actual Console-configured RuStore tester purchase/cancel/bank-return/restart/duplicate and Yandex demo-unit playback acceptance pending.",
            "Actual VK login, explicit cross-package managed-account recovery and physical-device startup/rendering acceptance pending.",
            "Final operator/support/legal facts, off-device encrypted signing backup and independent owner password retention pending.",
            "Original50 sustained worker capacity, unsupported preview117 and Windows Server Core remain separate gates; one L1 LocalService check does not establish these.",
            "Inactive production122 module CLI private-permit identity risk is inferred and not repaired by staging126.",
        ],
        "retainedFailedEpochs": "Aborted full run, failed packaging/audit epochs, raw-path25/26 and lost-verdict wrapper remain separate historical evidence; none are presented as passed runs.",
        "fixedFindings": [
            "Atomic Windows rewarded journal replacement and durable resolution before presentation.",
            "Real module-CLI private-permit identity mismatch.",
            "Stock Gradle library-only layout and exact generated UPM fingerprint handling.",
            "Transport capture before validation; classified stderr is not the test verdict.",
            "Cutover embedded metadata, durable backup binding/recheck, worker/catalog verification before stop, startup readiness retry and logging-independent stop containment.",
        ],
        "remediationPlan": "Codex_Handoff/Documentation/126_SDK_PAYMENTS_AD_REWARDS_AND_VK_REVIEW.md",
        "sourceBundleSHA256": bundle["archiveSHA256"],
        "sourceBundleCurrentFiles": len(bundle["filesSHA256"]),
        "evidenceSHA256": {relative: digest(EVIDENCE / relative) for _, relative in links},
        "credentialsCommitted": False,
        "gitCommitCreatedByThisReview": False,
        "aggregateToolSHA256": digest(Path(__file__)),
    }
    (EVIDENCE / "Review126Summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    rows = "\n".join(f'<tr><td>{html.escape(label)}</td><td><a href="{html.escape(relative, quote=True)}">Receipt</a></td></tr>' for label, relative in links)
    findings = "\n".join(f"<li>{html.escape(item)}</li>" for item in summary["openFindings"])
    host_status = html.escape(summary["hostStatus"])
    page = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Heart of the Rain — Review126</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;background:#101c29;color:#ecf2f7;margin:0}}main{{max-width:1050px;margin:auto;padding:32px}}h1{{line-height:1.2}}a{{color:#91d7ff}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}}.card{{background:#1d3042;border:1px solid #36516a;padding:16px;border-radius:9px}}.card strong{{display:block;font-size:28px}}table{{border-collapse:collapse;width:100%;margin:20px 0}}td{{padding:10px;border-bottom:1px solid #36516a}}code{{overflow-wrap:anywhere}}.gate{{border-left:4px solid #f0c56e;padding:12px 18px;background:#273545}}</style>
<main><h1>Review126: SDK purchases, ad rewards and VK</h1>
<p>The combined release-certificate-signed sandbox Development APK is built. The existing staging authority is configured for SDK payments, capped rewarded ads, VK and constrained original campaign replay; original accounts and wallets are preserved. These receipts distinguish backend tests, native Editor checks, actual APK inspection and pending provider/device acceptance.</p>
<div class="cards"><div class="card"><strong>959 / 959</strong>Backend tests; real approved replay worker</div><div class="card"><strong>853</strong>Native advertising assertions</div><div class="card"><strong>31</strong>Actual APK checks</div><div class="card"><strong>0</strong>Observed real provider transactions in this review</div></div>
<p>Scoped assertion counts overlap and must not be summed. Main Unity2022 and artwork/GUIDs/settings remain; packaging uses the approved isolated Unity6000.3.27f1 SDK project.</p>
<p class="gate">Hosted checkpoint: <code>{host_status}</code>. Production approval remains false.</p>
<p><a href="../../../Unity/Builds/Review126/HeartOfTheRain_SDK126_Sandbox.apk">Signed sandbox APK</a> · <a href="Review126Summary.json">Aggregate receipt</a> · <a href="../../../Codex_Handoff/Documentation/126_SDK_PAYMENTS_AD_REWARDS_AND_VK_REVIEW.md">Changes, test scope and step-by-step remaining plan</a> · <a href="../../../Release/Signing/README.md">Signing recovery before first upload</a></p>
<p>APK SHA256: <code>{published['sha256']}</code>. Package <code>com.heartoftherain.game</code>, RuStore <code>2063777840</code>, VK <code>54867814</code>. Use only the Console-configured RuStore test account. Four unrelated newer Main paths are explicitly excluded from this frozen APK.</p>
<table><tbody>{rows}</tbody></table>
<h2>Remaining acceptance and findings</h2><ol>{findings}</ol>
<p>SDK payments and ad completion are authenticated client reports, without independent server-side provider proof. Keys/passwords, provider tokens and database rows are not published here. No device screenshots are represented by this evidence index.</p></main></html>"""
    (EVIDENCE / "Comparison.html").write_text(page + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": summary["status"], "currentBackendPins": len(pins), "currentBundleFiles": len(bundle["filesSHA256"]), "apkSHA256": published["sha256"], "hostReceipt": args.host_receipt}))


if __name__ == "__main__":
    main()
