"""Render the reviewed116 evidence and handoff from an explicit final summary.

No app/backend/private state is changed. Existing handoff text is preserved;
only a main handoff still equal to its sealed copy receives the new entry.
"""
import hashlib
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review116'
REPO = OUT / 'Repository'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    summary_path = OUT / 'Review116Summary.json'
    summary = json.loads(summary_path.read_text('utf-8'))
    if summary['status'] != 'REVIEWED_TESTED_SNAPSHOT_WITH_OPEN_ACCEPTANCE_GATES':
        raise ValueError('ExplicitFinalReviewedSummaryRequired')
    plan = (OUT / 'RemediationPlan116.txt').read_text('utf-8-sig')
    if 'DRAFT' in plan:
        raise ValueError('FinalRemediationPlanRequired')
    rows = summary['executionEvidence']
    native = json.loads((ROOT / summary['nativeSummary']).read_text('utf-8-sig'))
    source_delta = json.loads((ROOT / summary['sourceDelta']).read_text('utf-8-sig'))
    if (native['status'] != 'CLASSIFIED_FINAL_NATIVE_SNAPSHOT116' or native['broadScopeCount'] != 53
            or len(native['broadScopes']) != 53 or len(native['actualHttp']) != 10):
        raise ValueError('ExpectedExplicitNativeScopeMatrix')
    text = [
        'HEART OF THE RAIN - COMPREHENSIVE APP AND BACKEND REVIEW116',
        '29 October 2026', '', summary['outcome'], '',
        'TESTED SOURCE AND COMMIT SCOPE', '',
        summary['sourceScope'], '',
        'EXECUTION EVIDENCE', '',
    ]
    for row in rows:
        text.extend([row['area'] + ': ' + row['result'],
                     '  Scope: ' + row['scope'],
                     '  Evidence: ' + row['path'], ''])
    text += ['NATIVE SCOPE MATRIX', '',
             'Original broad runs and later targeted runs retain separate source epochs.',
             'Checks are scoped assertions, not independent production acceptance tests.', '']
    for row in native['broadScopes']:
        latest = row['latestAttempt']
        text.append('- ' + row['name'] + ': ' + row['classification'] +
                    '; original=' + row['original']['status'] +
                    '; original checks=' + str(row['original']['checks']) +
                    '; latest=' + latest['tag'] + '/' + latest['status'] + '/' + str(latest['checks']) +
                    '; latest epoch=' + latest['sourceManifest']['path'] +
                    '; selected run=' + str(row.get('latestAccepted')))
        for accepted in row['acceptedTargetedReruns']:
            text.append('  Accepted targeted rerun: ' + json.dumps(accepted, ensure_ascii=True, sort_keys=True))
    text += ['', 'ACTUAL UNITY / TCP / SQLITE MATRIX', '']
    for row in native['actualHttp']:
        text.append('- ' + row['entry'] + ': ' + row['latestStatus'] +
                    '; checks=' + str(row['latestChecks']) + '; run=' + row['latestTag'])
    text.append('')
    text += ['CONFIRMED CHANGES', '']
    for item in summary['changes']:
        text += ['- ' + item, '']
    text += ['EXACT APP SOURCE REPAIRS IN THIS REVIEW', '']
    for item in source_delta['changes']:
        text.append('- ' + item['path'] + ': ' + item['classification'])
    text += ['', 'All original asset GUIDs and artwork are preserved. Full selected file inventories',
             'and backend/release/tooling provenance are in Repository/NonUnityCommitSource116.json',
             'and the explicitly selected final app manifest; newer main bytes are excluded.', '']
    text += ['RETAINED FAILURES AND MATERIAL LIMITATIONS', '']
    for item in summary['limitations']:
        text += ['- ' + item, '']
    text += ['ORDERED REMEDIATION', '', plan,
             'Machine-readable source/result bindings: Verification/Evidence/Review116/Review116Summary.json',
             'Visual evidence and direct report links: Verification/Evidence/Review116/Comparison.html', '']
    report_path = ROOT / 'Codex_Handoff/Documentation/116_COMPREHENSIVE_APP_BACKEND_REVIEW.txt'
    report_bytes = '\n'.join(text).encode('utf-8')
    if report_path.exists() and report_path.read_bytes() != report_bytes:
        raise ValueError('ExistingReviewReportPreservedForExplicitReview')
    if not report_path.exists():
        with report_path.open('xb') as stream:
            stream.write(report_bytes)
    esc = html.escape
    evidence_rows = ''.join('<tr><td>' + esc(row['area']) + '</td><td>' + esc(row['result']) +
        '</td><td>' + esc(row['scope']) + '</td><td><a href="../../../' + esc(row['path'], quote=True) +
        '">Report</a></td></tr>' for row in rows)
    matrix = ''
    for row in native['broadScopes']:
        latest = row['latestAttempt']
        accepted_text = '<pre>' + esc(json.dumps(row['acceptedTargetedReruns'], indent=2)) + '</pre>'
        matrix += '<tr><td>' + esc(row['name']) + '</td><td>' + esc(row['classification']) + \
            '</td><td>' + esc(row['original']['status']) + '<br>Checks: ' + str(row['original']['checks']) + '<br><a href="../../../' + \
            esc(row['original']['invocation']['path'], quote=True) + '">Original</a></td><td>' + \
            esc(latest['status']) + '<br>Checks: ' + str(latest['checks']) + '<br><a href="../../../' + \
            esc(latest['invocation']['path'], quote=True) + '">' + esc(latest['tag']) + '</a><br>Epoch: ' + \
            esc(latest['sourceManifest']['path']) + '</td><td>' + esc(str(row.get('latestAccepted'))) + \
            accepted_text + '</td></tr>'
    http_matrix = ''.join('<tr><td>' + esc(row['entry']) + '</td><td>' + esc(row['latestStatus']) +
        '</td><td>' + str(row['latestChecks']) + '</td><td><a href="../../../' +
        esc(row['latestInvocation']['path'], quote=True) + '">' + esc(row['latestTag']) +
        '</a></td></tr>' for row in native['actualHttp'])
    images = ''.join('<figure><a href="' + esc(item['path'].removeprefix('Verification/Evidence/Review116/'), quote=True) +
        '"><img loading="lazy" src="' + esc(item['path'].removeprefix('Verification/Evidence/Review116/'), quote=True) +
        '" alt="' + esc(item['caption'], quote=True) + '"></a><figcaption>' + esc(item['caption']) +
        '</figcaption></figure>' for item in summary['images'])
    bullet = lambda items: '<ul>' + ''.join('<li>' + esc(item) + '</li>' for item in items) + '</ul>'
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + \
        '<title>Heart of the Rain — Review116</title><style>' + \
        'body{font:16px/1.55 system-ui,sans-serif;max-width:1280px;margin:auto;padding:28px;background:#f5f7f8;color:#182d3d}' + \
        'table{border-collapse:collapse;width:100%;background:white}td,th{padding:12px;border:1px solid #c8d4dc;text-align:left;vertical-align:top}' + \
        '.gallery{display:flex;flex-wrap:wrap;gap:18px}figure{margin:0;width:min(300px,100%)}img{width:100%;height:auto}pre{white-space:pre-wrap;font:inherit}' + \
        'a{color:#065e89}li{margin-bottom:10px}</style><h1>Comprehensive app and backend review116</h1>' + \
        '<p>29 October 2026 · Tested snapshot; open acceptance gates retained.</p><p>' + esc(summary['outcome']) + \
        '</p><h2>Selected source</h2><p>' + esc(summary['sourceScope']) + '</p><h2>Specific execution evidence</h2>' + \
        '<table><thead><tr><th>Area</th><th>Observed result</th><th>Practical scope</th><th>Evidence</th></tr></thead><tbody>' + evidence_rows + \
        '</tbody></table><h2>Native scope matrix</h2><p>53 broad scopes plus 10 actual HTTP scopes. Original runs, latest attempts and selected reruns retain their individual source epochs.</p>' + \
        '<table><thead><tr><th>Scope</th><th>Classified result</th><th>Original</th><th>Latest attempt</th><th>Accepted reruns</th></tr></thead><tbody>' + \
        matrix + '</tbody></table><h2>Actual Unity / TCP / SQLite matrix</h2><table><thead><tr><th>Entry</th><th>Status</th><th>Checks</th><th>Invocation</th></tr></thead><tbody>' + \
        http_matrix + '</tbody></table><h2>Confirmed changes</h2>' + bullet(summary['changes']) + \
        '<details><summary>Exact app source repairs</summary>' + bullet([x['path'] + ': ' + x['classification'] for x in source_delta['changes']]) + '</details>' + \
        '<h2>Retained failures and limits</h2>' + bullet(summary['limitations']) + \
        '<h2>Actual native images</h2><div class="gallery">' + images + '</div><h2>Step-by-step remediation</h2><pre>' + esc(plan) + \
        '</pre><p><a href="Review116Summary.json">Machine-readable summary</a> · <a href="RemediationPlan116.txt">Remediation plan</a></p></html>\n'
    (OUT / 'Comparison.html').write_text(page, encoding='utf-8')
    (REPO / 'SelectedImages116.json').write_text(json.dumps(dict(paths=[i['path'] for i in summary['images']]), indent=2) + '\n', encoding='utf-8')
    overrides = {}
    header = summary['handoffEntry'].strip() + '\n\n'
    merge = []
    for name in ('00_START_HERE.md', '01_STATUS_AND_DECISIONS.md'):
        relative = 'Codex_Handoff/Documentation/' + name
        sealed = ROOT / '.verification-cache/Review116/CommitSource' / relative
        before = sealed.read_bytes()
        separator = re.search(rb'\r?\n\r?\n', before)
        if separator is None:
            raise ValueError('EstablishedHandoffHeadingRequired')
        insertion = separator.end()
        line_end = '\r\n' if b'\r\n' in before else '\n'
        entry = header.replace('\n', line_end).encode('utf-8')
        after = before[:insertion] + entry + before[insertion:]
        final = REPO / 'FinalDocumentation' / name
        final.parent.mkdir(parents=True, exist_ok=True)
        final.write_bytes(after)
        overrides[relative] = dict(source=final.relative_to(ROOT).as_posix(), sha256=sha(final))
        main_path = ROOT / relative
        current = main_path.read_bytes()
        if current == before and main_path.read_bytes() == current:
            main_path.write_bytes(after)
            result = 'UpdatedMainStillEqualToSealedBase'
        elif current == after:
            result = 'MainAlreadyContainsExactFinalReview'
        else:
            result = 'NewerMainDocumentationPreservedUnchanged'
        merge.append(dict(path=relative, result=result, beforeSHA256=hashlib.sha256(before).hexdigest(),
                          finalSHA256=sha(final), mainSHA256=sha(main_path)))
    # The new report is explicitly included; it did not exist at the initial cut.
    overrides[report_path.relative_to(ROOT).as_posix()] = dict(
        source=report_path.relative_to(ROOT).as_posix(), sha256=sha(report_path))
    (REPO / 'CommitOverrides116.json').write_text(json.dumps(dict(files=overrides, mainHandoffMerge=merge), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='WROTE_FINAL_REVIEW116_REPORTS', report=report_path.relative_to(ROOT).as_posix(),
                          selectedImages=len(summary['images']), handoff=merge)))


if __name__ == '__main__':
    main()
