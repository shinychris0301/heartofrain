"""Render the measured engineering evidence index; never executes tests or payments."""
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/RuStore81'


def main():
    inputs = ['Backend/Service_Tests.json', 'Native/RuStore81.json', 'Native/HTTP.json',
              'Backend/HTTP_Restart.json', 'SDK_Android/Assembly/APK_Inspection.json',
              'APK_Artifact.json', 'APK_Profile.json', 'Android/Installation.json',
              'Device_Visual_Notes.json', 'Implementation_Review.json', 'Source_Delta.json', 'Source_SHA256.json']
    read = lambda name: json.loads((OUT / name).read_text('utf-8-sig'))
    values = {name: read(name) for name in inputs}
    backend, guard, http = [values[n] for n in inputs[:3]]
    artifact, installed = values['APK_Artifact.json'], values['Android/Installation.json']
    assert backend['tests'] == 90 and guard['checks'] == 328 and http['checks'] == 38
    assert installed['data_unchanged'] and installed['portrait'] and installed['runtime_errors'] == 0
    digest = artifact['sha256']
    body = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RuStore backend and release foundation — checkpoint81</title><style>
*{box-sizing:border-box}body{margin:0;background:#091b2d;color:#e9f0f5;font:16px/1.55 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:30px 22px}h1{font-size:2rem;color:#f5cf76}h2{color:#f0ce85;margin-top:2rem}a{color:#8edbff}code{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #355267;vertical-align:top}th{color:#f5cf76}p{max-width:950px}.notice{border-left:5px solid #e6b544;background:#17354c;padding:16px}.gallery{display:flex;gap:20px;flex-wrap:wrap}figure{margin:0;flex:1;min-width:240px;max-width:440px}img{width:100%;height:auto;border:1px solid #456175}figcaption{font-size:.9rem;color:#bdd1df}small{color:#bdd1df}.scroll{overflow:auto}
</style><main><h1>RuStore backend and release foundation</h1><p>Checkpoint81 · pinned Unity2022.3.62f3 · <strong>Сердце дождя</strong></p>
<p class="notice"><strong>Portable staging foundation verified; production release blocked.</strong> Actual backend, Unity HTTP and SDK compilation evidence are separate from live payment acceptance. The ordinary game keeps its local profile and contains no native RuStore SDK.</p>
<p><a href="../../../Codex_Handoff/Documentation/81_RUSTORE_BACKEND_AND_RELEASE_FOUNDATION_REVIEW.md">Engineering review</a> · <a href="../../../Release/RuStore/README.md">Registration proposals and remaining requirements</a> · <a href="Summary.json">Source-bound result</a> · <a href="Backend/OpenAPI.json">Current API contract</a></p>
<h2>Implemented behavior</h2><p>Player-bound server orders, strict invoice verification, atomic once-only wallet credits, sticky refund review, delivery/restart recovery, shared coin/inventory/life ledger and typed attempts. Repeated continues cost900 coins for five moves; full refill at zero lives costs900 coins. Local balances are never silently imported.</p>
<p>The explicit Unity adapters keep credentials in memory, save correlation before checkout, fence late responses, reverify completed journals and use the SDK's returned <code>amountLabel</code>. Mutations stay in model/services. No automatic purchase, local grant or Continue tap is introduced.</p>
<h2>Measured checks</h2><div class="scroll"><table><tr><th>Evidence</th><th>Actual result</th><th>Scope</th></tr>
<tr><td><a href="Backend/Service_Tests.json">Backend90 tests</a></td><td>PASS ·30 unchanged inputs</td><td>Python/ASGI/SQLite, ephemeral RSA and synthetic provider responses; no real payment.</td></tr>
<tr><td><a href="Native/RuStore81.json">Native guard/recovery</a></td><td>PASS ·328 checks</td><td>102 config mutations,13 coordinator cases,6 actual disk cases,4 client cases, approved coin rules.</td></tr>
<tr><td><a href="Native/HTTP.json">Unity HTTP</a> / <a href="Backend/HTTP_Restart.json">process restart</a></td><td>PASS ·38 checks,20 requests,5 duplicate commands</td><td>2250coins /4lives /revision6 and six ledger entries survive a distinct server-process restart. Store confirmation is synthetic.</td></tr>
<tr><td>Selected native compatibility</td><td>PASS ·14,520 total including guard/HTTP</td><td>General/profile/connected/portrait checks. Additional preflight correctly blocks release.</td></tr>
<tr><td><a href="SDK_Android/Assembly/APK_Inspection.json">Separate SDK APK</a></td><td>PASS ·88 static checks</td><td>Pay11.1.0 + Core10.5.0, API26/34, ARM64, real Java17/Gradle7.5.1 assembly. APK never launched.</td></tr>
<tr><td><a href="Android_Build.json">Development</a> / <a href="Android_Release_Build.json">release compile</a></td><td>PASS ·internal builds</td><td>Verification package; no production signing/SDK activation.</td></tr>
<tr><td><a href="APK_Artifact.json">APK integrity</a> / <a href="APK_Profile.json">SDK isolation</a></td><td>PASS</td><td>Clean packaging, same development signer, CRC/alignment/ELF and native Pay provider/classes absent.</td></tr>
<tr><td><a href="Android/Installation.json">QA2 installation</a> / <a href="Device_Visual_Notes.json">actual visual review</a></td><td>PASS ·save unchanged ·portrait ·0 matched runtime errors</td><td>Only5558/index2. Main remains64; original QA1 remains78 with its active attempt preserved.</td></tr>
</table></div>
<h2>Actual ordinary APK frames</h2><p>Two original900×1600 screenshots reviewed. Russian Prologue and the first language menu retain artwork, readable text and contained controls. No language selected or tutorial advanced. This is not a whole-game, tablet, timing or reference-app review.</p><div class="gallery">
<figure><a href="Android/FirstStart_Russian.png"><img src="Android/FirstStart_Russian.png" alt="Actual portrait Russian Prologue"></a><figcaption>Russian Prologue after normal startup.</figcaption></figure>
<figure><a href="Android/FirstStart_Language_Menu.png"><img src="Android/FirstStart_Language_Menu.png" alt="Actual language menu with Russian first"></a><figcaption>Russian first and selected; no preference changed.</figcaption></figure></div>
<h2>Artifact and preserved source</h2><p>Internal development APK: <a href="../../../Unity/Builds/Verification/HeartOfTheRain_Development.apk">HeartOfTheRain_Development.apk</a> ·303,092,264 bytes.</p><p>SHA256: <code>APK_HASH</code></p><p><a href="Source_Delta.json">17 Unity additions; zero changed or removed source80 inputs</a>. All approved Resources, artwork, existing services and gameplay timing remain unchanged. The journal/transport fixes and initial SDK fixture failures are preserved in <a href="Attempts/001_packageinfo_ambiguity/Reason.json">compile attempt1</a>, <a href="Attempts/002_inline_json_nulls/Reason.json">native attempt2</a> and <a href="SDK_Android/Attempts/Manifest.json">SDK attempts</a>; failures are not counted as passes.</p>
<h2>Required before live release</h2><p>Reserve/check proposed package <code>com.heartoftherain.game</code> and return scheme <code>heartoftherain-pay</code>; create the real Console app/products; deploy an owned HTTPS backend. The Console ID and public backend URL do not exist yet. Six disabled proposed SKUs preserve the current Shop rewards; no hard-coded prices are enabled.</p>
<p>Connect managed guest identity/linking and secure recovery, approved profile migration and normal-game server-wallet routing, a real gameplay verifier, authenticated encrypted notifications/recovery workers, refund policy, environment isolation/operations, production signing and Russian legal/deletion/retention policies. Then test actual Android sandbox/bank-return/cancellation/termination/duplicate/upgrade flows. Real social features require moderation.</p>
<p>Stock SDK package metadata declares Unity6000.0; measured compilation on2022 is not vendor support certification. Java17 assembly uses normal Unity Gradle export with embedded Java11, without changing the Editor JDK. The license-required Unity splash remains. Existing gameplay smoothness and physical-device/translation/long-session gates remain open.</p>
<p><a href="Native/Release_Preflight.json">Actual blocked release preflight</a> · <a href="Implementation_Review.json">Source review</a> · <a href="Package_Audit.json">Complete uploaded-package review</a></p><small>Evidence scopes are explicit. No real RuStore payment, public deployment or store publication is claimed.</small></main></html>'''
    target = OUT / 'Comparison.html'
    target.write_text(body.replace('APK_HASH', html.escape(digest)), encoding='utf-8')
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = {'status': 'GENERATED_FROM_ACTUAL_RUSTORE81_PROOF_NOT_NEW_TEST', 'utc': datetime.now(timezone.utc).isoformat(),
              'toolSHA256': sha(Path(__file__)), 'inputSHA256': {name: sha(OUT / name) for name in inputs},
              'htmlSHA256': sha(target), 'scope': 'Evidence presentation only. Visual inspection recorded separately; generation never authorizes payments or publication.'}
    (OUT / 'Review_Index.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(report['status'])


if __name__ == '__main__':
    main()
