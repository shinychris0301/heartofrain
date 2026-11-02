"""Bind105 recorded tests, actual TCP drill, source epochs and open gates.

Only read-only source/log/owned-database inventories run here. No new test,
service, worker, PowerShell, Unity, APK, provider or device process is started.
"""
import ast
from collections import Counter
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
from run_ads85_native import freeze,sha,utc,write
E=ROOT/'Verification/Evidence/Review105'


def load(path):return json.loads(path.read_text('utf-8-sig'))
def bind(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)
def change(a,b):return dict(added=sorted(b.keys()-a.keys()),removed=sorted(a.keys()-b.keys()),changed=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k]))


def inventory(path):
    if not path.resolve().is_relative_to((ROOT/'.verification-cache/Review105/TCP/Flow02').resolve()):
        raise ValueError('Owned105RecordedDatabaseRequired')
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,isolation_level=None)
    try:
        db.execute('PRAGMA query_only=ON')
        counts={table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('players','wallets','wallet_ledger','social_teams','social_team_members','social_messages','rewards','gameplay_attempts','commerce_orders','commerce_credits')}
        good=(db.execute('PRAGMA quick_check').fetchall()==[('ok',)] and not db.execute('PRAGMA foreign_key_check').fetchall()
              and db.execute('SELECT version FROM schema_info').fetchall()==[(10,)])
        if not good or counts!={'players':2,'wallets':2,'wallet_ledger':2,'social_teams':1,'social_team_members':2,'social_messages':1,'rewards':0,'gameplay_attempts':0,'commerce_orders':0,'commerce_credits':0}:
            raise ValueError('Recorded105FinancialAndSocialInventoryMismatch')
        return dict(database=path.relative_to(ROOT).as_posix(),readOnly=True,integrityAndForeignKeysValid=True,schemaVersion=10,counts=counts,
            scope='Post-run read-only aggregate inventory of this owned disposable database; no auth rows or message bodies are exported. This does not add scenarios to the recorded116 TCP checks.')
    finally:db.close()


def methods(path):
    tree=ast.parse(path.read_text('utf-8-sig'))
    return {node.name:ast.dump(node,include_attributes=False) for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')}


def main():
    final_path=E/'TCP/Flow02/Report.json';flow=load(final_path)
    focused_path=E/'Focused/Focused01/Invocation.json';focused=load(focused_path)
    service_path=E/'Focused/Focused01/ServiceTests.json';service=load(service_path)
    follow_path=E/'Focused/OpsFollowup01/Invocation.json';follow=load(follow_path)
    follow_service_path=E/'Focused/OpsFollowup01/ServiceTests.json';follow_service=load(follow_service_path)
    ps_path=E/'PowerShell/Example01/Report.json';ps=load(ps_path)
    failed_path=E/'TCP/Flow01/Report.json';failed=load(failed_path)
    recheck_path=E/'TCP/Flow01/CleanupRecheck01.json';recheck=load(recheck_path)
    if flow['status']!='PASS_STAGING105_TCP' or flow['checks']!=116 or len(flow['requests'])!=29 or not all(p['listenerClosed'] and p['actualServerTerminationObserved'] for p in flow['processes']):
        raise ValueError('Accepted105ActualTcpProofRequired')
    if focused['status']!='PASS_FOCUSED105_INVOCATION' or service['executedTests']!=52 or follow['status']!='PASS_FOCUSED105_INVOCATION' or follow_service['executedTests']!=12:
        raise ValueError('Accepted52And12RecordedTestsRequired')
    baseline_main=ROOT/'Verification/Evidence/Review104/Native/PackagingIsolated01/MainSources_after.json'
    final_main=E/'TCP/Flow02/MainSources_after.json'
    main_before,main_after=load(baseline_main),load(final_main)
    baseline_backend=ROOT/'Verification/Tools/Review105/BaselineBackend105.json'
    previous=load(baseline_backend)['sourceSHA256'];current=flow['sourceSHA256After']
    if main_before!=main_after or freeze()!=main_after or any(sha(ROOT/k)!=v for k,v in current.items()):
        raise ValueError('Sealed105CurrentSourceBoundaryRequired')
    delta=change(previous,current)
    expected_added=['Backend/hotr_backend/staging105.py','Backend/hotr_backend/staging_ops105.py','Backend/tests/test_staging105.py','Backend/tests/test_staging_ops105.py']
    if delta!=dict(added=expected_added,removed=[],changed=[]):raise ValueError('ExactlyFourAddedNoOldBackendChanges105')
    epoch=change(service['sourceSHA256After'],current)
    if epoch!=dict(added=[],removed=[],changed=['Backend/tests/test_staging_ops105.py']) or follow_service['sourceSHA256After']!=current:
        raise ValueError('OnlyOpsFixtureHygieneChangedAfterFocused52Required')
    old_test=E/'RetainedSources/test_staging_ops105_before_cleanup.py'
    old_guide=E/'RetainedSources/STAGING_SERVER_OPERATIONS105_before_policy_note.txt'
    guide=ROOT/'Release/RuStore/STAGING_SERVER_OPERATIONS105.txt'
    if sha(old_test)!=service['sourceSHA256After']['Backend/tests/test_staging_ops105.py'] or methods(old_test)!=methods(ROOT/'Backend/tests/test_staging_ops105.py'):
        raise ValueError('RetainedSame12MethodBodiesRequired105')
    if sha(guide)!='7260425fa5fb0b2c79b5605b40aa1b813bc5e992cdeb54aa9c45718c5b25d291':
        raise ValueError('FinalGuideRefreezeRequired105')
    source_delta=dict(schemaVersion=1,status='VERIFIED_STAGING105_SOURCE_DELTA',utc=utc(),
        baselineMain=bind(baseline_main),finalMain=bind(final_main),unityInputCount=main_after['inputCount'],all5482UnityInputsUnchanged=True,
        baselineBackend=bind(baseline_backend),finalBackendProof=bind(final_path),previousBackendFiles=len(previous),finalBackendFiles=len(current),backend=delta,
        all101ExistingBackendInputsPreserved=True,fullBackendSuiteRerun=False,actualReplayWorkerRun=False,
        focused52EarlierSourceEpoch=bind(service_path),earlierToFinalEpoch=epoch,opsOnlyFinalProof=bind(follow_service_path),
        testMethodBodiesUnchanged=True,other40TestsRerunAfterHygieneFix=False,
        supplementalSupport=[bind(ROOT/'Backend/Start-Staging105.ps1'),bind(ROOT/'Release/RuStore/staging-server.example.json'),bind(guide)],
        oldGuide=bind(old_guide),oldOpsFixture=bind(old_test),
        scope='104 Unity and the unchanged101-file backend baseline versus105. Four Python additions plus staging support only; existing runtime/config/requirements and all artwork/GUIDs/settings/gameplay/economy are unchanged.52 distinct tests and12 repeated ops cases retain their actual epochs; no64-distinct claim.')
    write(E/'SourceDelta105.json',source_delta)

    harness_old=ROOT/'.verification-cache/Review105/ToolSources/ac55aa1825e6b89b16ab941d7196cf2bfdf65c883caf56a3e918362c1c63736c.py'
    focus_runner_old=ROOT/'.verification-cache/Review105/ToolSources/2ef0fa90f5be7ba6542f257620b817a095438fcc10165c3fbee89ddce35b5ce7.py'
    retained=dict(schemaVersion=1,status='RETAINED_FAILURES_AND_EPOCHS105',utc=utc(),
        firstTcp=dict(report=bind(failed_path),recordedStatus=failed['status'],checks=failed['checks'],requests=len(failed['requests']),
            outcome='Immediate listener check raced asynchronous kill-on-close Job termination; no restart/restore pass is inferred from Flow01.',
            laterCleanupObservation=bind(recheck_path),laterPortClosed=recheck['portClosedAtRecheck'],
            correction='Retain exact already-owned server SYNCHRONIZE handle, wait for process termination and bounded known-port closure before asserting.',
            originalHarness=bind(harness_old),successor=bind(final_path),originalReportUnmodified=True),
        windowsScript=dict(report=bind(ps_path),recordedStatus=ps['status'],gate='PC execution policy rejects script files before Python bootstrap.',
            pythonBootstrapVerified=False,executionPolicyOverridden=False,scriptRetried=False,
            sourceBugDemonstrated=False,supportedPythonCliUsed=True,oldGuide=bind(old_guide),finalGuide=bind(guide)),
        testEpoch=dict(focused52=bind(service_path),finalOps12=bind(follow_service_path),oldOpsFixture=bind(old_test),
            change='Register environment/temp cleanup immediately during setUp; identical12 test method bodies.',
            originalFocusedRunner=bind(focus_runner_old),no64DistinctTestsClaim=True))
    write(E/'FailuresAndEpochs105.json',retained)

    diagnostics=[]
    for tag,parent in [('Focused01',E/'Focused/Focused01'),('OpsFollowup01',E/'Focused/OpsFollowup01')]:
        inv=load(parent/'Invocation.json');log=ROOT/inv['privateConsole']['path'];text=log.read_text('utf-8-sig',errors='replace')
        counts=Counter(re.findall(r'\b[A-Za-z_][A-Za-z_0-9]*Warning\b',text))
        diagnostics.append(dict(tag=tag,privateConsole=bind(log),warningTypeOccurrences=dict(counts)))
    for row in flow['processes']:
        log=ROOT/row['privateServerLog']['path'];text=log.read_text('utf-8-sig',errors='replace')
        diagnostics.append(dict(tag=row['label'],privateConsole=bind(log),nonEmpty=bool(text.strip()),
            uppercaseWarningOrErrorLines=len(re.findall(r'(?m)^(?:WARNING|ERROR)\b',text))))
    diag=dict(schemaVersion=1,status='SCOPED_DIAGNOSTICS_AND_OPEN_GATES105',utc=utc(),logs=diagnostics,
        powerShellPolicyGate=dict(report=bind(ps_path),blocked=True,bootstrapReached=False,policyChanged=False),
        priorTcpCleanupFailureRetained=True,finalOwnedProcessClosuresObserved=3,finalListenerClosuresObserved=3,
        csharpCompilePerformed=False,csharpWarningCountsMeasured=False,unityOrEngineOrSdkOperation=False,
        noGlobalWarningsResolvedClaim=True,priorIl2cppAndPhysicalPerformanceFindingsNotRerun=True,
        scope='Recorded Python/test/server log inventories and explicit environment gates. Existing dependency warnings remain distinct; no Unity compile/zero-C#-warning or whole-app performance claim.')
    write(E/'Diagnostics105.json',diag)

    data=ROOT/'.verification-cache/Review105/TCP/Flow02/Data'
    database_inventory=[inventory(data/'authority.sqlite3'),inventory(data/'backups/LiveWAL.sqlite3'),inventory(data/'restores/Restored01/authority.sqlite3')]
    previous_summary=load(ROOT/'Verification/Evidence/Review104/Summary.json')
    summary=dict(schemaVersion=1,status='REVIEWED_STAGING_SUPPORT_WITH_OPEN_DEPLOYMENT_GATES',utc=utc(),
        targetedCodeAndLocalOperationalVerificationPassed=True,fullyVetted=False,taskComplete=False,productionApproved=False,
        sourceDelta=bind(E/'SourceDelta105.json'),failuresAndEpochs=bind(E/'FailuresAndEpochs105.json'),diagnostics=bind(E/'Diagnostics105.json'),
        tests=dict(focused52=bind(focused_path),focusedService=bind(service_path),distinctPassedTests=52,
            passedByModule=service['passedByModule'],finalOps12=bind(follow_path),finalOpsService=bind(follow_service_path),
            repeatedOpsTests=12,distinctTestsAreNot64=True,fullBackend527Rerun=False,actualReplayWorker=False),
        actualTcp=dict(report=bind(final_path),checks=116,requests=29,actualUvicornStarts=3,maxConcurrentOwnedServices=1,
            realDisposableManagedGuestEnrollments=2,teamCount=1,memberCount=2,messageCount=1,coinsEach=1250,
            exactCreateJoinChatRetriesAfterRestartAndRestore=True,committedResponseBodyDeliberatelyNotConsumed=True,
            physicalNetworkLossInjected=False,liveWalBackupThroughOwnedWrapper=True,newDatabaseRestoreThroughOwnedWrapper=True,
            automaticActivationPerformed=False,manualDescriptorAndStart=True,observedServerTerminations=3,observedClosedPorts=3,
            crashStyleTermination=True,gracefulShutdownClaim=False,servicesLeftRunning=False,
            independentRecordedDatabaseInventories=database_inventory,
            totalDisposableTcpEnrollmentsAcrossRetainedAttempts=flow['passed'].count('real_guest_enrollment_expected_status')+failed['passed'].count('real_guest_enrollment_expected_status')),
        configuration=dict(untouchedEmptyExamplePreflightBlocked=focused['untouchedExampleBlocked'],untouchedEmptyExampleExportBlocked=True,
            actualAppConfigurationExport=flow['details']['explicitAppConfigurationExport'],unchanged104PreparerAcceptedWithoutCandidate=True,
            publicOriginAssignedOrOwned=False,syntheticOriginResolvedOrContacted=False,hostingConfigured=False,
            gameplayEnabled=False,gameplayExecutionVerified=False,vkConfigured=False,realProvidersUsed=False,
            realHttpsOrTlsVerified=False,guide=bind(guide),powerShellWrapperUsableOnThisPcVerified=False),
        unityAndAndroid=dict(unityInputCount=5482,allUnityInputsPreserved=True,unityEditorInvoked=False,engineOrSdkChanged=False,
            apkBuiltOrInstalled=False,adbOrDeviceInspected=False,ordinaryProfilesReadOrChanged=False,
            historical101Artifact=previous_summary['android']['previous101Artifact'],freshDeviceStateVerified=False),
        remainingGates=[
            'Owner-selected hosting, owned DNS/HTTPS/TLS, storage/ACL/firewall/backup operations and external two-device acceptance remain unconfigured.',
            'The exact synthetic HTTPS string is unowned metadata; this drill contacted only127.0.0.1 and does not establish hosted reachability.',
            'The current Windows PowerShell script policy blocks the optional file wrapper. No policy override was attempted; supported Python CLI is verified.',
            'Gameplay replay is disabled in this social-only drill. Enabling the approved worker requires separate execution acceptance.',
            'Real VK consent/callbacks, payment/advertising credentials, SDK/device integration and production activation remain open.',
            'The earlier Android101 artifact and broader startup/performance/device release findings were not retested.'],
        reviewPath='Codex_Handoff/Documentation/105_STAGING_SERVER_OPERATIONS_REVIEW.txt',galleryPath='Verification/Evidence/Review105/Comparison.html',
        scope='Actual new staging launch/ops Python CLI,52 distinct focused tests with12 final-fixture repetitions, and the final two-account116-check local TCP/WAL/restart/restore rehearsal. No live hosting/provider, Unity, APK, physical device or production acceptance.')
    write(E/'Summary.json',summary)
    print(json.dumps(dict(status=summary['status'],distinctTests=52,repeatedOps=12,tcpChecks=116,tcpRequests=29,ownedClosures=3,unchangedUnity=5482,unchangedOldBackend=101,newPython=4)))


if __name__=='__main__':main()
