"""Host-only guard and exclusive-write lifecycle controls; no native execution."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import resolved_native97d as M


class ResolverFixture:
    def __init__(self, root):
        self.root = root
        self.evidence = root/'Evidence'
        self.private = root/'Private'
        self.preparation = self.evidence/'ResolverMap97/Set01/Preparation.json'
        self.now = datetime(2026, 10, 27, 14, 25, tzinfo=timezone.utc)
        self.preparation.parent.mkdir(parents=True)
        self.hosts = self.private/'Retry97/BuildHostsSet01.txt'
        self.hosts.parent.mkdir(parents=True)
        self.hosts.write_text('127.0.0.1 localhost\n::1 localhost\n' + ''.join('142.250.102.'+str(i)+' dl.google.com\n' for i in (190, 136, 91, 93)))
        self.routes = self.private/'Retry97/Routes.json'
        M.write(self.routes, {'host':'dl.google.com', 'uri':'/dl/android/maven2/com/android/tools/build/gradle/9.1.1/gradle-9.1.1.pom',
             'utc':(self.now-timedelta(minutes=1)).isoformat(), 'results':[
             dict(address='142.250.102.'+str(i), success=True, statusLine='HTTP/1.1 200 OK', tls='TLSv1.3') for i in (190,136,91,93)]})
        self.dns = self.private/'Retry97/Dns.json'; M.write(self.dns, {'host':'dl.google.com'})
        self.proof = dict(schemaVersion=1, status='PREPARED_PRIVATE_EXPIRING_JAVA_RESOLVER_TEST97', utc=self.now.isoformat(),
             expiresUtc=(self.now+timedelta(hours=1)).isoformat(), hostsFile=M.bound(self.hosts), googleRouteAuthority=M.bound(self.routes),
             earlierDnsObservation=M.bound(self.dns), overriddenNetworkHostnames=['dl.google.com'], ordinaryRepositoryDomainCount=8,
             localHostnamesIncluded=True, localHostValuesPrivate=True, requiredJavaOptions=M.options_for(self.hosts))
        self.make_policy()
        self.make_snapshot()
        self.save()

    def make_policy(self):
        self.short = self.root/'ShortGradle'
        (self.short/'init.d').mkdir(parents=True)
        props=self.short/'gradle.properties';props.write_bytes(b'org.gradle.daemon=false\r\n')
        init=self.short/'init.d/hotr_offline97.gradle'
        with patch.object(M,'PRIVATE',self.private):
            allowed=M.allowed_gradle_directories();init.write_bytes(M.expected_init_script())
        copied=self.evidence/'ShortGradleCache97/Set01/Report.json';copied.parent.mkdir(parents=True)
        manifest=copied.parent/'SourceFiles.json'
        M.write(manifest,{'files':{'files-2.1/group/item/a.jar':{'sha256':'a'*64,'bytes':3}}})
        M.write(copied,dict(status='PASS_VERIFIED_SHORT_GRADLE_DEPENDENCY_CACHE97',source=str(self.private/'Gradle97/caches/modules-2'),
            destinationHome=str(self.short),fileCount=1,bytes=3,manifest=M.bound(manifest),allCopiedBytesMatchSource=True,
            excludedLockAndGcFiles=['gc.properties','modules-2.lock'],versionSpecificTransformsCopied=False,nativeOrEditorProcessesLaunched=False))
        self.proof['privateGradlePolicy']=dict(home=str(self.short),copiedCache=M.bound(copied),gradleProperties=M.bound(props),initScript=M.bound(init),
            triggerEnvironment={'HOTR_GRADLE97_OFFLINE':'1'},allowedGeneratedGradleDirectories=allowed)

    def make_snapshot(self):
        self.previous=self.evidence/'ResolverMap97/Set02/Preparation.json'
        self.previous.parent.mkdir(parents=True,exist_ok=True)
        self.old_hosts=self.private/'Retry97/PreviousHosts.txt'
        self.old_hosts.write_bytes(self.hosts.read_bytes())
        captured=(self.now-timedelta(minutes=35)).isoformat()
        M.write(self.previous,dict(utc=captured,hostsFile=M.bound(self.old_hosts)))
        self.proof['ordinaryHostsSnapshot']=dict(preparation=M.bound(self.previous),hostsFile=M.bound(self.old_hosts),
            capturedUtc=captured,freshOsRefreshFailed=True,failureCategory='socket.gaierror11001')

    def save(self):
        self.preparation.write_text(json.dumps(self.proof))

    def patches(self):
        return patch.multiple(M, ROOT=self.root, EVIDENCE=self.evidence, PRIVATE=self.private,
                              RESOLVER=self.preparation, RESOLVER_SHA=M.sha(self.preparation), GRADLE_HOME=self.short,
                              CACHE_COPY_SOURCE=self.private/'Gradle97/caches/modules-2', ORDINARY_SNAPSHOT_SHA=M.sha(self.previous))


class ResolvedHostTests(unittest.TestCase):
    def test_exact_options_and_valid_unexpired_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder))
            with f.patches():
                result=M.validate_resolver(900,f.now)
            self.assertEqual(result['requiredJavaOptions'],M.options_for(f.hosts))

    def test_expiry_requires_whole_timeout_plus_sixty_seconds(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder))
            with f.patches():
                M.validate_resolver(900,f.now+timedelta(seconds=2640))
                with self.assertRaisesRegex(ValueError,'InsufficientResolverLifetime'):
                    M.validate_resolver(900,f.now+timedelta(seconds=2640.01))

    def test_future_or_overlong_mapping_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder))
            for created,expiry in ((f.now+timedelta(seconds=1),f.now+timedelta(hours=1)),(f.now,f.now+timedelta(hours=2))):
                f.proof.update(utc=created.isoformat(),expiresUtc=expiry.isoformat());f.save()
                with f.patches(),self.assertRaisesRegex(ValueError,'NoFutureOrOverlongMapping'):
                    M.validate_resolver(600,f.now)

    def test_changed_preparation_cannot_extend_expiry(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder))
            with f.patches():
                f.proof['expiresUtc']=(f.now+timedelta(hours=2)).isoformat();f.save()
                with self.assertRaisesRegex(ValueError,'ExactReviewedResolverPreparation'):
                    M.validate_resolver(600,f.now)

    def test_hosts_routes_and_dns_bytes_all_bound(self):
        for which in ('hosts','routes','dns'):
            with self.subTest(which=which),tempfile.TemporaryDirectory() as folder:
                f=ResolverFixture(Path(folder))
                with f.patches():
                    with getattr(f,which).open('a') as stream:stream.write('tamper')
                    with self.assertRaisesRegex(ValueError,'ArtifactHashOrBytesChanged'):
                        M.validate_resolver(600,f.now)

    def test_no_extra_tls_or_trust_property_allowed(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder));f.proof['requiredJavaOptions'].append('-Dhttps.protocols=TLSv1.2');f.save()
            with f.patches(),self.assertRaisesRegex(ValueError,'ExactJavaOptions'):
                M.validate_resolver(600,f.now)

    def test_override_scope_cannot_expand(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder));f.proof['overriddenNetworkHostnames'].append('other.example');f.save()
            with f.patches(),self.assertRaisesRegex(ValueError,'NarrowReviewedResolverScope'):
                M.validate_resolver(600,f.now)

    def test_bad_tls_route_is_rejected_even_when_rebound(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder));r=M.read(f.routes);r['results'][0]['success']=False
            f.routes.write_text(json.dumps(r));f.proof['googleRouteAuthority']=M.bound(f.routes);f.save()
            with f.patches(),self.assertRaisesRegex(ValueError,'FourSuccessfulRecordedTLSRoutes'):
                M.validate_resolver(600,f.now)

    def test_different_google_mapping_or_missing_loopback_rejected(self):
        for raw in ('127.0.0.1 localhost\n::1 localhost\n142.250.102.55 dl.google.com\n',
                    ''.join('142.250.102.'+str(i)+' dl.google.com\n' for i in (190,136,91,93))):
            with tempfile.TemporaryDirectory() as folder:
                f=ResolverFixture(Path(folder));f.hosts.write_text(raw);f.proof['hostsFile']=M.bound(f.hosts);f.save()
                with f.patches(),self.assertRaisesRegex(ValueError,'HostsMustMatchVerifiedRoutesAndLoopback'):
                    M.validate_resolver(600,f.now)

    def test_outside_artifact_rejected_without_read(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder));f.proof['hostsFile']['path']=str(f.root/'outside.txt');f.save()
            with f.patches(),self.assertRaisesRegex(ValueError,'ContainedPathRequired'):
                M.validate_resolver(600,f.now)

    def test_duplicate_hosts_and_malformed_tokens_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'hosts'
            for raw in ('127.0.0.1 localhost\n127.0.0.1 localhost\n','127.0.0.1 ../name\n'):
                path.write_text(raw)
                with self.assertRaises(ValueError):M.parse_hosts(path)

    def test_timezone_required(self):
        with self.assertRaisesRegex(ValueError,'TimezoneRequired'):M.instant('2026-10-27T12:00:00')

    def test_action_operation_and_timeout_restrictions(self):
        M.validate_arguments('smoke',None,600)
        M.validate_arguments('game','BuildDevelopment',900)
        for args in [('smoke','Configure',600),('game',None,900),('game','Release',900),('smoke',None,1800)]:
            with self.subTest(args=args),self.assertRaises(ValueError):M.validate_arguments(*args)

    def test_private_policy_file_tamper_cannot_be_hidden_by_rebinding(self):
        for key in ('gradleProperties','initScript'):
            with self.subTest(key=key),tempfile.TemporaryDirectory() as folder:
                f=ResolverFixture(Path(folder));policy=f.proof['privateGradlePolicy'];path=Path(policy[key]['path'])
                with path.open('ab') as stream:stream.write(b'// unexpected mutation\r\n')
                policy[key]=M.bound(path);f.save()
                with f.patches(),self.assertRaisesRegex(ValueError,'ExactPrivateDaemonProperties|ExactGatedOfflineInitContent'):
                    M.validate_resolver(600,f.now)

    def test_extra_root_or_nested_gradle_init_sources_are_rejected(self):
        for relative in ('init.gradle','init.gradle.kts','init.d/extra.gradle','init.d/nested/extra.gradle.kts'):
            with self.subTest(relative=relative),tempfile.TemporaryDirectory() as folder:
                f=ResolverFixture(Path(folder));extra=f.short/relative;extra.parent.mkdir(parents=True,exist_ok=True);extra.write_text('// synthetic')
                with f.patches(),self.assertRaisesRegex(ValueError,'NoAdditionalPrivateGradleInitSources'):
                    M.validate_resolver(600,f.now)

    def test_policy_cannot_expand_trigger_or_six_approved_contexts(self):
        for key,value in (('triggerEnvironment',{'HOTR_GRADLE97_OFFLINE':'anything'}),('allowedGeneratedGradleDirectories',['E:/other'])):
            with self.subTest(key=key),tempfile.TemporaryDirectory() as folder:
                f=ResolverFixture(Path(folder));f.proof['privateGradlePolicy'][key]=value;f.save()
                with f.patches(),self.assertRaisesRegex(ValueError,'ExactOfflineTriggerAndSixProjectContexts'):
                    M.validate_resolver(600,f.now)

    def test_policy_cannot_point_to_another_short_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder));f.proof['privateGradlePolicy']['home']=str(f.root/'Other');f.save()
            with f.patches(),self.assertRaisesRegex(ValueError,'ExactShortGradleHome'):
                M.validate_resolver(600,f.now)

    def test_exact_six_contexts_include_both_actual_warmups_but_not_neighbors(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder));allowed=f.proof['privateGradlePolicy']['allowedGeneratedGradleDirectories']
            self.assertEqual(len(allowed),6)
            self.assertEqual(sum(name.endswith('/Temp/StagingArea/gradleWarmupArea') for name in allowed),2)
            with f.patches():M.validate_resolver(600,f.now)
            allowed[2]=allowed[2]+'/unexpected-child';f.save()
            with f.patches(),self.assertRaisesRegex(ValueError,'ExactOfflineTriggerAndSixProjectContexts'):
                M.validate_resolver(600,f.now)

    def test_historical_ordinary_snapshot_cannot_hide_new_hostname_or_address(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder))
            with f.hosts.open('a') as stream:stream.write('9.9.9.9 repo.maven.apache.org\n')
            f.proof['hostsFile']=M.bound(f.hosts);f.save()
            with f.patches(),self.assertRaisesRegex(ValueError,'OnlyFreshGoogleRoutesMayDiffer'):
                M.validate_resolver(600,f.now)

    def test_failed_ordinary_refresh_must_remain_explicit_and_bound(self):
        for change in ('claimFresh','sourceTamper'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                f=ResolverFixture(Path(folder))
                if change=='claimFresh':
                    f.proof['ordinaryHostsSnapshot']['freshOsRefreshFailed']=False;f.save()
                    with f.patches(),self.assertRaisesRegex(ValueError,'ExplicitHistoricalOrdinaryDNSObservation'):
                        M.validate_resolver(600,f.now)
                else:
                    with f.patches():
                        f.previous.write_text('{}')
                        with self.assertRaisesRegex(ValueError,'ArtifactHashOrBytesChanged'):
                            M.validate_resolver(600,f.now)

    def test_copy_receipt_must_preserve_modules_only_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder));p=f.proof['privateGradlePolicy'];path=Path(p['copiedCache']['path']);value=M.read(path)
            value['versionSpecificTransformsCopied']=True;path.write_text(json.dumps(value));p['copiedCache']=M.bound(path);f.save()
            with f.patches(),self.assertRaisesRegex(ValueError,'VerifiedShortDependencyCacheProvenance'):
                M.validate_resolver(600,f.now)

    def test_copy_manifest_bytes_and_counts_cannot_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            f=ResolverFixture(Path(folder));p=f.proof['privateGradlePolicy'];path=Path(p['copiedCache']['path']);value=M.read(path)
            value['fileCount']=2;path.write_text(json.dumps(value));p['copiedCache']=M.bound(path);f.save()
            with f.patches(),self.assertRaisesRegex(ValueError,'ExactCacheCopyManifest'):
                M.validate_resolver(600,f.now)

    def test_process_environment_restored_after_normal_and_exception(self):
        for fails in (False,True):
            with patch.dict(os.environ,{'HOTR_TEST_EXISTING':'original'},clear=True):
                before=dict(os.environ)
                try:
                    with M.process_environment({'HOTR_TEST_EXISTING':'temporary','HOTR_TEST_NEW':'value'}):
                        self.assertEqual(os.environ['HOTR_TEST_NEW'],'value')
                        if fails:raise RuntimeError('synthetic')
                except RuntimeError:pass
                self.assertEqual(dict(os.environ),before)

    def test_stock_unity_cleanup_retains_sdk_script_options_without_java_wide_notice(self):
        with patch.dict(os.environ,{},clear=True):
            before=dict(os.environ)
            options=' '.join(M.options_for(Path('E:/private/hosts.txt')))
            with M.process_environment({'SDKMANAGER_OPTS':options,'GRADLE_USER_HOME':'E:/shortcache','HOTR_GRADLE97_OFFLINE':'1'}):
                # Simulate only the exact environment cleanup/replacement observed in stock DLL IL.
                child=dict(os.environ)
                for key in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','CLASSPATH'):child.pop(key,None)
                child['JAVA_TOOL_OPTIONS']='-Dfile.encoding=UTF-8'
                self.assertEqual(child['SDKMANAGER_OPTS'],options)
                self.assertNotIn('JDK_JAVA_OPTIONS',child)
                self.assertEqual(child['HOTR_GRADLE97_OFFLINE'],'1')
                self.assertEqual(child['JAVA_TOOL_OPTIONS'],'-Dfile.encoding=UTF-8')
                self.assertEqual(child['GRADLE_USER_HOME'],'E:/shortcache')
                self.assertNotIn('JAVA_TOOL_OPTIONS',os.environ)
            self.assertEqual(dict(os.environ),before)

    def test_actual_current_frozen_helpers_are_byte_exact(self):
        result=M.helper_bindings()
        self.assertEqual(result['smoke95.py']['sha256'],M.FROZEN['smoke95.py'])
        self.assertEqual(result['game95.py']['sha256'],M.FROZEN['game95.py'])

    def test_zero_or_multiple_fresh_native_receipts_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaisesRegex(ValueError,'ExactlyOneFreshNativeInvocation'):
                M.new_invocation(root,{},'smoke',None,0)
            for name in ('a'*32,'b'*32):
                path=root/name/'Invocation.json';path.parent.mkdir();M.write(path,{})
            with self.assertRaisesRegex(ValueError,'ExactlyOneFreshNativeInvocation'):
                M.new_invocation(root,{},'smoke',None,0)

    def test_historical_native_receipt_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/('a'*32)/'Invocation.json';path.parent.mkdir();M.write(path,{'status':'FAIL'})
            before=M.existing_invocations(root);path.write_text('{}')
            with self.assertRaisesRegex(ValueError,'HistoricalInvocationChanged'):
                M.new_invocation(root,before,'smoke',None,0)

    def test_failed_native_result_is_retained_as_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/('a'*32)/'Invocation.json';path.parent.mkdir()
            M.write(path,dict(status='FAIL_ACTUAL_LTS95_TOOLCHAIN_SMOKE',exitCode=1))
            result=M.new_invocation(root,{},'smoke',None,1)
            self.assertFalse(result['passed']);self.assertEqual(result['actualNativeExitCode'],1)
            self.assertEqual(result['actualStatus'],'FAIL_ACTUAL_LTS95_TOOLCHAIN_SMOKE')

    def test_wrapper_lifecycle_calls_unmodified_runner_and_writes_final_once(self):
        for passes in (False,True):
            with self.subTest(passes=passes),tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{},clear=True):
                f=ResolverFixture(Path(folder));prepared=f.evidence/'SmokePreparation/Test/Preparation.json'
                prepared.parent.mkdir(parents=True);M.write(prepared,{'hostSyntheticOnly':True})
                (f.private/'Gradle97').mkdir()
                out=f.evidence/'ResolvedNative97'/('c'*32)
                helpers={'wrapper':{'hostSyntheticOnly':True}}
                seen=[]
                def fake_native(path,timeout):
                    seen.append((path,timeout,dict(os.environ)))
                    native=f.evidence/'SmokeRuns'/('a'*32)/'Invocation.json';native.parent.mkdir(parents=True)
                    M.write(native,dict(status='PASS_ACTUAL_LTS95_TOOLCHAIN_SMOKE_WITH_NO_GAME_ACCEPTANCE' if passes else 'FAIL_ACTUAL_LTS95_TOOLCHAIN_SMOKE',
                        exitCode=0 if passes else 1,actualEngineVersionFromLog=M.smoke95.VERSION,mainInputsUnchanged=True,
                        candidate66InputsUnchanged=True,externalToolPrefFingerprintsUnchanged=True,embeddedToolMarkersUnchanged=True,unityPidsAfter=[],
                        preparation=M.bound(path),runnerSHA256=M.FROZEN['smoke95.py']))
                    return 0 if passes else 1
                with f.patches(),patch.object(M,'utc',return_value=f.now),patch.object(M,'helper_bindings',return_value=helpers),\
                     patch.object(M.smoke95,'run',side_effect=fake_native):
                    self.assertEqual(M.run('smoke',prepared,None,600,out),0 if passes else 1)
                report=M.read(out/'Report.json')
                self.assertEqual(len(seen),1);self.assertTrue(report['processEnvironmentRestored'])
                self.assertEqual(seen[0][2]['GRADLE_USER_HOME'],str(f.short))
                self.assertEqual(seen[0][2]['HOTR_GRADLE97_OFFLINE'],'1')
                self.assertNotIn('JDK_JAVA_OPTIONS',seen[0][2]);self.assertNotIn('JAVA_TOOL_OPTIONS',seen[0][2])
                self.assertEqual(seen[0][2]['SDKMANAGER_OPTS'],' '.join(f.proof['requiredJavaOptions']))
                self.assertTrue(report['resolverFilesUnchanged']);self.assertTrue(report['helpersUnchanged'])
                self.assertEqual(report['actualNative']['passed'],passes)
                self.assertFalse(os.environ.get('SDKMANAGER_OPTS'));self.assertFalse(os.environ.get('HOTR_GRADLE97_OFFLINE'));self.assertFalse(os.environ.get('GRADLE_USER_HOME'))
                with self.assertRaises(FileExistsError):M.write(out/'Report.json',{})

    def test_outer_pass_with_wrong_engine_or_failed_preservation_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/('a'*32)/'Invocation.json';path.parent.mkdir()
            clean=dict(status='PASS_ACTUAL_LTS95_TOOLCHAIN_SMOKE_WITH_NO_GAME_ACCEPTANCE',exitCode=0,
                actualEngineVersionFromLog=M.smoke95.VERSION,mainInputsUnchanged=True,candidate66InputsUnchanged=True,
                externalToolPrefFingerprintsUnchanged=True,embeddedToolMarkersUnchanged=True,unityPidsAfter=[])
            for key,value in [('actualEngineVersionFromLog','2022.3.62f3'),('mainInputsUnchanged',False),
                              ('externalToolPrefFingerprintsUnchanged',False),('timedOut',True),('unityPidsAfter',[123])]:
                path.write_text(json.dumps(dict(clean,**{key:value})))
                with self.subTest(key=key):self.assertFalse(M.new_invocation(root,{},'smoke',None,0)['passed'])


if __name__=='__main__':unittest.main()
