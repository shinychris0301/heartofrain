"""Root-approved metrics-only Editor fixture epoch. Does not run native tools."""
from __future__ import annotations
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('caption_epoch07_prep', HERE / 'prepare_payment_diagnostics127.py')
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)
PARENT = Path('E:/.verification-cache/HOTR127/Pay01')
PREVIOUS = '1af93a0a3549a89c59718da2ae3102d7b679b2cdb5a772b9adea8af295ae15cd'
PREVIOUS_PLAN = 'afc912c5fd8e2ff37f2b40e09c55c2b847d007fa8c52972d701f2378d3e35666'
BEFORE = 'ba55deb177260489032e3fe121500c1b402ccca6dbdc02d47993f122b0394733'
AFTER = 'f293130ce846a871d17c7f740e06cd877e8b2cef0c84e4c987a8f437b6ee986c'
RELATIVE = 'Assets/Review127Diagnostics/Editor/SigninLayout127Verification.cs'
BUILDER = 'a23b3a242f542a3187baa69f5e45cd11ed06f95b1a65f2ad219ea017fda2db11'
RUNNER = '56e7ee24e04a436230c6c85802f5d623606ef1130972064a81213692dfdd2c96'
WRAPPER = '836197b052cb7f72e527469bfd7045451d40635fac7a07b0abd63bd757cbacee'


def prepare():
    old = PARENT / 'Preparation127_Epoch06.json'
    old_plan = PARENT / 'RunPlan127_Epoch06.json'
    new = PARENT / 'Preparation127_Epoch07.json'
    new_plan = PARENT / 'RunPlan127_Epoch07.json'
    prep.need(prep.sha(old) == PREVIOUS and prep.sha(old_plan) == PREVIOUS_PLAN, 'ExactPreviousEpoch06Required127')
    prep.need(not new.exists() and not new_plan.exists(), 'FreshCaptionMetricEpoch07Required127')
    value = json.loads(old.read_text('utf-8'))
    plan = json.loads(old_plan.read_text('utf-8'))
    project = PARENT / 'Game'
    target = project / RELATIVE
    source = prep.ROOT / 'Verification/Tools/Review127/Signin/SigninLayout127Verification.cs'
    prep.need(Path(value['project']).resolve() == project.resolve(), 'ExactPrivateProjectRequired127')
    prep.need(prep.sha(source) == AFTER and prep.sha(target) == BEFORE, 'ExactReviewedMetricsFixtureRequired127')
    before_inputs = prep.inventory(project)
    prep.need(len(before_inputs) == 6310 and before_inputs == value['inputs'], 'UnexpectedProjectDriftBeforeMetrics127')
    prep.need(prep.sha(project / 'Assets/Review127Diagnostics/Editor/PaymentDiagnosticBuild127.cs') == BUILDER, 'FrozenNativeBuilderRequired127')
    prep.need(prep.sha(HERE / 'run_payment_diagnostics127_02.py') == RUNNER and prep.sha(HERE / 'run_isolated_native127_02.py') == WRAPPER, 'FrozenRunnersRequired127')
    history = PARENT / 'History/EditorFixtureba55deb1'
    history.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(target, history / 'SigninLayout127Verification.cs')
    shutil.copyfile(Path(str(target) + '.meta'), history / 'SigninLayout127Verification.cs.meta')
    prep.need(prep.sha(history / 'SigninLayout127Verification.cs') == BEFORE, 'ExactPreviousFixtureHistoryRequired127')
    meta = prep.sha(Path(str(target) + '.meta'))
    shutil.copyfile(source, target)
    expected = dict(before_inputs)
    expected[RELATIVE] = AFTER
    prep.need(prep.inventory(project) == expected and prep.sha(Path(str(target) + '.meta')) == meta, 'OnlyApprovedFixtureMayChange127')
    value['inputs'] = expected
    value['sha256'][value['paths'].index(RELATIVE)] = AFTER
    value.update(sourceEpoch=7, runtimeSourceEpoch=4, toolingEpoch=5, epochPreparedUtc=datetime.now(timezone.utc).isoformat(), previousPreparationSHA256=PREVIOUS, epochToolSHA256=prep.sha(__file__), nativeFixtureSHA256=AFTER, epochDelta={RELATIVE: {'before': BEFORE, 'after': AFTER}}, runtimeAssetChanges=[], epochScope='EDITOR METRICS ONLY: durable whitelisted numeric caption snapshot before unchanged raw-font bounds assertion. All other6309 source inputs, runtime/UI7, meta/art/vendor, builder and immutable runners remain unchanged.', diagnosticProbeOnly=True, expectedNativeOutcome='Existing BoundedReadableButtonCaption127 failure is expected until actual numeric metric evidence establishes its units. This diagnostic epoch is not an accepted native layout or APK build gate.')
    prep.write(new, value)
    plan.update(sourceEpoch=7, runtimeSourceEpoch=4, toolingEpoch=5, preparationSHA256=prep.sha(new), previousRunPlanSHA256=PREVIOUS_PLAN, epochScope=value['epochScope'], diagnosticProbeOnly=True, expectedNativeOutcome=value['expectedNativeOutcome'], executionPurpose='Root-only Layout05 DIAGNOSTIC probe; no signing, packaging or APK build authorized by this plan.')
    plan['environmentReferences']['HOTR_PAYMENTDIAG127_RECEIPT'] = str(new)
    command = list(plan['rootCommands'][0])
    command[command.index('--receipt') + 1] = str(new)
    command[command.index('--tag') + 1] = 'Layout05'
    plan['rootCommands'] = [command]
    plan['diagnosticOutput'] = 'Actual Layout05 CaptionMetric127.json must be read before any assertion normalization/tolerance change. No native PASS claim from an expected diagnostic failure.'
    prep.write(new_plan, plan)
    prep.need(prep.sha(old) == PREVIOUS and prep.sha(old_plan) == PREVIOUS_PLAN, 'PriorEpoch06MustRemainExact127')
    return {'status': 'PREPARED_DIAGNOSTIC_METRICS_ONLY_EPOCH07_127', 'preparationSHA256': prep.sha(new), 'runPlanSHA256': prep.sha(new_plan), 'editorFixtureSHA256': AFTER, 'projectInputs': 6310, 'changedProjectPaths': [RELATIVE], 'runtimeAssetChanges': [], 'metaUnchanged': True, 'builderAndRunnersUnchanged': True, 'actualNativeExecution': False}


if __name__ == '__main__':
    try:
        print(json.dumps(prepare()))
    except Exception as failure:
        code = str(failure)
        print(json.dumps({'status': 'BLOCKED_EDITOR_METRICS_EPOCH07', 'code': code if re.fullmatch('[A-Za-z0-9_]{1,120}', code) else type(failure).__name__}))
        raise SystemExit(1)
