"""Produce feature/campaign coverage without converting fixtures into human QA."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/SwapCreation' if (ROOT/'Verification/Evidence/SwapCreation/LDPlayer/Regression.json').exists() else ROOT/'Verification/Evidence/M70' if (ROOT/'Verification/Evidence/M70/LDPlayer/Regression.json').exists() else ROOT/'Verification/Evidence/Portrait' if (ROOT/'Verification/Evidence/Portrait/LDPlayer/Regression.json').exists() else ROOT/'Verification/Evidence/ObstacleGravity' if (ROOT/'Verification/Evidence/ObstacleGravity/LDPlayer/Regression.json').exists() else ROOT/'Verification/Evidence/Timing' if (ROOT/'Verification/Evidence/Timing/LDPlayer/Regression.json').exists() else ROOT/'Verification/Evidence/Fluidity' if (ROOT/'Verification/Evidence/Fluidity/LDPlayer/Regression.json').exists() else ROOT/'Verification/Evidence/Regression'


def write(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)


def run():
    report=json.loads((OUT/'LDPlayer/Regression.json').read_text(encoding='utf-8'))
    assert report['status']=='PASS_NATIVE_REGRESSION' and not report['failures']
    checks=set(report['passed'])
    rows=[]
    for level in range(1,51):
        assert f'L{level} accepts natural move' in checks
        for tool in range(4):
            assert f'L{level} tool {tool} spends one stock' in checks
            assert f'L{level} tool {tool} preserves moves' in checks
        recorded=f'Connected L{level} grants one first-clear reward' in checks
        rows.append({'level':level,'native_board_and_natural_action':'PASS','native_four_tools_and_move_costs':'PASS',
                     'recorded_connected_win':'PASS' if recorded else 'NOT_RUN',
                     'full_human_playthrough':'PENDING','balance_certification':'PENDING',
                     'evidence':'LDPlayer/Regression.json','scope':'Programmatic native actions; no human cohort or natural-balance claim.'})
    write('Campaign_Automated_Regression.csv',rows)
    features=[
        ('Onboarding','Story/opening, language overlay, three guided lessons, ready screen','PASS_NATIVE','Five locales; transient onboarding store. ADB touch evidence is separate.'),
        ('Tutorial layout','Result and no-cost note fit at three portrait sizes','PASS_NATIVE_LAYOUT','45 stage/locale/size combinations in the native Editor case; Android capture at900x1600.'),
        ('Home','Header, chapter, progression, event drawer and navigation presentation','PASS_NATIVE_PRESENTATION','Five locales. Gift/cup/wellworks/profile/lives destination services are not implemented.'),
        ('Pre-level','Nine goal lookups, four distinct starting items, reservation/duplicate commit','PASS_NATIVE_MODEL_AND_PRESENTATION','All four item gesture/grant evidence, when collected, is separate from the no-selection connected suite.'),
        ('Campaign','All50 openings, natural moves, gravity/refill and state invariants','PASS_NATIVE','Full human wins/balance are pending for all50.'),
        ('Obstacles','Eight damageable families and jar delivery rules','PASS_NATIVE','All eight families damaged in live playback; jar delivery is exercised by recorded clears and clip sampling.'),
        ('Powers','Six standalone variants and14 pair types in56 arrangements','PASS_NATIVE','Staged fixtures; not exhaustive edge/hole/long-session stress.'),
        ('Tools','Hammer/Axe/Ram/Atlas playback, stock cost and move preservation','PASS_NATIVE','Four tools on each of50 boards.'),
        ('Effects','Clips/body sprites, fragments, sparks and target glow','PASS_NATIVE_SAMPLES','354 sampled visible-pixel-count comparisons; five terminal hit samples are empty in both shaders. Native captures supplement counts.'),
        ('Moss','Canonical/legacy interval, cap, zero budget and invalid input','PASS_NATIVE_MODEL','Authored default fingerprints preserved.'),
        ('Failure/retry','One-move loss fixture, life charge, repeated frames and retry','PASS_NATIVE_CONNECTED','Fixture guarantees a loss; no authored level changed. No crash-durable attempt receipt.'),
        ('Tool inventory','Reload/retry retain spending; Settings reads shared stock','PASS_SESSION_ONLY','App-restart persistence remains unimplemented.'),
        ('Completion','Five connected recorded wins, first-clear rewards and duplicate close','PASS_NATIVE_CONNECTED','Recorded seeds/actions; not player balance certification.'),
        ('Celebrations','M68 mesh victory and Chapter1 restoration/Dariya/city hook','PASS_NATIVE_CONNECTED','Native composition comparison, pause/skip/reduced-motion checks and connected Android captures. No new art approval.'),
        ('Completion return','Celebration closes to interactive Home with settled reward counters','PASS_NATIVE_CONNECTED','Five recorded wins; no automatic next-level preview. Durable settlement remains open.'),
        ('Navigation motion','Shared dock geometry, press/release scale and fixed hit rectangles','PASS_NATIVE_PRESENTATION','Five locales and native Android captures; reduced motion uses tint feedback.'),
        ('Concurrent playback','Contact-triggered powers, per-column refill and cabinet reservations','PASS_NATIVE_SCHEDULE_AND_PLAYBACK','Preserves model rules and causal obstacle damage. Does not activate unrelated powers.'),
        ('Fluidity','Unaccelerated before/after input, frame intervals and collection counters','MEASURED_WITH_REMAINING_SPIKES','One run per APK on ARM-translated LDPlayer. Consult current Performance_Comparison.json; physical profiling pending.'),
        ('Reaction timing','Direct and hit ignition, distance-aware gravity, spawn portals and validated tail input','PASS_NATIVE_MODEL_AND_LIFECYCLE','Timing/Native_Checks.json and Play_Smoke.json; actual Android gesture/video evidence is separate.'),
        ('Journey','Archive and Chapter1 reader presentation','PASS_NATIVE_PRESENTATION','100-chapter catalogs structurally reviewed; only Chapter1 has playable levels.'),
        ('Leaderboard','Three tabs, friends search and removal cancellation','PASS_PREVIEW_UI','No authenticated ranking/friend delivery service.'),
        ('Teams','Chat/info/mail tabs, composer cancellation and mail readers','PASS_PREVIEW_UI','Local snapshot only; no messages sent to other users.'),
        ('Shop','Carousel and all12 offer detail views','PASS_PREVIEW_UI','No purchases, billing, receipts or fulfillment implemented.'),
        ('Settings','Main/inventory/language/help/follow and gameplay settings','PASS_NATIVE_PRESENTATION','Test settings use a transient store. Audio perception, haptics and IME/accessibility require further device review.'),
        ('Localization','Five UI locales,231 catalog entries and100 chapters per translated story file','PASS_STRUCTURAL_AND_NATIVE_SAMPLES','Some gameplay/error strings still need a complete localization audit; native-speaker review pending.'),
        ('Persistence','Durable campaign/wallet/lives/all eight stock fields/attempt ledger','NOT_IMPLEMENTED','ENG-02/03/05 remain release gates. Existing settings/tutorial PlayerPrefs are a narrower feature.'),
        ('Services','Production commerce/social/events/analytics/support/legal/account operations','NOT_IMPLEMENTED','Preview pages cannot certify these services.'),
        ('Physical devices','Suspend/process death, low memory, thermal/frame budgets and store compliance','PENDING','LDPlayer uses ARM translation. Screenshot readbacks perturb timing.'),
        ('Historical review scenes','Earlier planners, galleries and M66 review views','COMPILE_AND_BINDING_REVIEW','They coexist with the live M46/M48 board and M67 flow; no claim that every historical scene received a device playthrough.'),
        ('Unspecified rule','Golden+Golden','INTENTIONALLY_UNDEFINED','No new mechanic invented.'),
    ]
    if OUT.name in ('ObstacleGravity','Portrait','M70','SwapCreation'):
        assert 'Android cleared cell below stacked stones is occupied' in checks
        features.append(('Obstacle gravity','Reachable gaps under stacked fixed stones, diagonal path and settled occupancy','PASS_NATIVE_MODEL_AND_ANDROID_RENDER','Native fixtures and all50 board regression; no physical-device or identical competitor-mechanic claim.'))
        features=[('Fluidity','Prior timing APK frame measurements','HISTORICAL_PERFORMANCE_CHECKPOINT','No fresh frame-budget measurement for this APK. Heavy-combo spikes and physical profiling remain open.') if a=='Fluidity' else (a,f,s,scope) for a,f,s,scope in features]
    if OUT.name=='Portrait':
        features.append(('Portrait orientation','Cold launch, all captured app pages, rotation preferences and resume at four emulator sizes','PASS_NATIVE_DEVICE_AND_MANIFEST','Portrait native policy and device matrix; real Android16/17 tablets and physical sensors remain pending.'))
    if OUT.name=='M70':
        features.append(('Portrait orientation','Preserved app policy; current compiled manifest and all listed suite frames','PASS_CURRENT_APK_MANIFEST_AND_FRAMES','Earlier24-profile/rotation/resume checkpoint remains historical; physical Android16/17/iOS validation pending.'))
        features.append(('M70 power-up bodies','Seven updated sheets;586 frame rectangles/replay parity,48-frame Bomb/Rocket idle and live pause/activation across three board shapes','PASS_NATIVE_EDITOR_AND_ANDROID','ASTC4x4 and single-copy residency checked in LDPlayer. Physical-device texture fallback/thermal profiling and owner art review remain open.'))
        features=[('Fluidity','Fresh pre-M70 versus M70 emulator probe','RECORDED_EMULATOR_MEASUREMENT','One run per variant; heavy-combo spikes and physical profiling remain open.') if a=='Fluidity' else (a,f,s,scope) for a,f,s,scope in features]
    if OUT.name=='SwapCreation':
        features.append(('Swap and rocket creation','Accepted swap poses, matching endpoint, swipe-axis rocket and one-move charge in all four directions','PASS_NATIVE_AND_ACTUAL_ANDROID_INPUT','Transient fixtures plus actual Android swipes/video. Rocket can fall normally after being created. Physical performance remains pending.'))
        features.append(('Portrait orientation','Current compiled manifest and listed Android suite frames','PASS_CURRENT_APK_MANIFEST_AND_FRAMES','Earlier rotation/profile matrix remains historical.'))
    write('Feature_Coverage.csv',[{'area':a,'feature':f,'status':s,'scope_or_limitation':scope} for a,f,s,scope in features])
    print(json.dumps({'native_checks':report['checks'],'native_actions':report['actions'],'campaign_rows':50,'feature_rows':len(features)},indent=2))


if __name__=='__main__':run()
