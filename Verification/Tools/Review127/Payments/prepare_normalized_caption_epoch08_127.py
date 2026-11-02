"""Root-approved Editor-only caption metric correction; no native execution."""
from __future__ import annotations
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('caption_epoch08_helpers', HERE / 'prepare_caption_metrics_epoch07_127.py')
previous_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous_tool)
prep = previous_tool.prep
PARENT = previous_tool.PARENT
PREVIOUS = 'ecc521344b6ec6e154a13dc9d4ad02d15b530334344f97eb352b48662fa1de4d'
PREVIOUS_PLAN = 'cb4055c7e159f8d39d910d7d7381da22842d1f75029aae344703070b71e490f2'
BEFORE = 'f293130ce846a871d17c7f740e06cd877e8b2cef0c84e4c987a8f437b6ee986c'
AFTER = '1eeff3c3a2600520356801825ee042babedccea8ddccb93a1a75d1d0a326e579'
RELATIVE = previous_tool.RELATIVE


def prepare():
    old = PARENT / 'Preparation127_Epoch07.json'
    old_plan = PARENT / 'RunPlan127_Epoch07.json'
    new = PARENT / 'Preparation127_Epoch08.json'
    new_plan = PARENT / 'RunPlan127_Epoch08.json'
    prep.need(prep.sha(old) == PREVIOUS and prep.sha(old_plan) == PREVIOUS_PLAN, 'ExactPreviousEpoch07Required127')
    prep.need(not new.exists() and not new_plan.exists(), 'FreshNormalizedCaptionEpoch08Required127')
    value = json.loads(old.read_text('utf-8'))
    plan = json.loads(old_plan.read_text('utf-8'))
    project = PARENT / 'Game'
    target = project / RELATIVE
    source = prep.ROOT / 'Verification/Tools/Review127/Signin/SigninLayout127Verification.cs'
    prep.need(Path(value['project']).resolve() == project.resolve(), 'ExactPrivateProjectRequired127')
    prep.need(prep.sha(source) == AFTER and prep.sha(target) == BEFORE, 'ExactReviewedNormalizedFixtureRequired127')
    before_inputs = prep.inventory(project)
    prep.need(len(before_inputs) == 6310 and before_inputs == value['inputs'], 'UnexpectedProjectDriftBeforeNormalizedCaption127')
    prep.need(prep.sha(project / 'Assets/Review127Diagnostics/Editor/PaymentDiagnosticBuild127.cs') == previous_tool.BUILDER, 'FrozenNativeBuilderRequired127')
    prep.need(prep.sha(HERE / 'run_payment_diagnostics127_02.py') == previous_tool.RUNNER and prep.sha(HERE / 'run_isolated_native127_02.py') == previous_tool.WRAPPER, 'FrozenRunnersRequired127')
    history = PARENT / 'History/EditorFixturef293130c'
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
    value.update(sourceEpoch=8, runtimeSourceEpoch=4, toolingEpoch=5, epochPreparedUtc=datetime.now(timezone.utc).isoformat(), previousPreparationSHA256=PREVIOUS, epochToolSHA256=prep.sha(__file__), nativeFixtureSHA256=AFTER, epochDelta={RELATIVE: {'before': BEFORE, 'after': AFTER}}, runtimeAssetChanges=[], epochScope='EDITOR TEST UNITS ONLY: actual Layout05 raw34/ppu1.832=18.558 confirms native pixel units. Normalize by pixelsPerUnit, require finite positive matching scale and dynamic font, allow only configured bound floor/ceil integer-pixel quantization (<1 raw pixel), retain first tiny metric once. All other6309 inputs and strict visibility/geometry/raycast/startup checks remain unchanged.', diagnosticProbeOnly=False, expectedNativeOutcome='Root-only full Layout06 sweep must actually pass180cases/540layouts and strict source/startup checks before any native acceptance or build credential use. No pass is claimed by preparation.')
    prep.write(new, value)
    plan.update(sourceEpoch=8, runtimeSourceEpoch=4, toolingEpoch=5, preparationSHA256=prep.sha(new), previousRunPlanSHA256=PREVIOUS_PLAN, epochScope=value['epochScope'], diagnosticProbeOnly=False, expectedNativeOutcome=value['expectedNativeOutcome'], executionPurpose='Root-only full Layout06 native rendering sweep, then packaging/build only after all original acceptance guards and explicit startup flag check.')
    plan.pop('diagnosticOutput', None)
    plan['environmentReferences']['HOTR_PAYMENTDIAG127_RECEIPT'] = str(new)
    prior_commands = json.loads((PARENT / 'RunPlan127_Epoch06.json').read_text('utf-8'))['rootCommands']
    plan['rootCommands'] = prior_commands
    for command in plan['rootCommands']:
        for index, part in enumerate(command):
            if part == str(PARENT / 'Preparation127_Epoch06.json'):
                command[index] = str(new)
            elif part == 'Layout04':
                command[index] = 'Layout06'
            elif part == '<Layout04/Native.json>':
                command[index] = '<Layout06/Native.json>'
    prep.write(new_plan, plan)
    prep.need(prep.sha(old) == PREVIOUS and prep.sha(old_plan) == PREVIOUS_PLAN, 'PriorEpoch07MustRemainExact127')
    return {'status': 'PREPARED_EDITOR_NORMALIZED_CAPTION_EPOCH08_127', 'preparationSHA256': prep.sha(new), 'runPlanSHA256': prep.sha(new_plan), 'editorFixtureSHA256': AFTER, 'projectInputs': 6310, 'changedProjectPaths': [RELATIVE], 'runtimeAssetChanges': [], 'metaUnchanged': True, 'builderAndRunnersUnchanged': True, 'actualNativeExecution': False}


if __name__ == '__main__':
    try:
        print(json.dumps(prepare()))
    except Exception as failure:
        code = str(failure)
        print(json.dumps({'status': 'BLOCKED_EDITOR_NORMALIZED_CAPTION_EPOCH08', 'code': code if re.fullmatch('[A-Za-z0-9_]{1,120}', code) else type(failure).__name__}))
        raise SystemExit(1)
