"""Collect current evidence and a reviewable path inventory; never run Unity."""
import collections
import datetime as dt
import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Verification/Evidence'


def read(path): return json.loads((OUT/path).read_text(encoding='utf-8-sig'))


def regression_summary(report):
    if not report:return None
    result={key:report.get(key) for key in ('status','utc','platform','graphics','device','width','height','checks','labels','clips','actions','boards','scope','damageFamilies','failures')}
    result['captured_frames']=len(report.get('frames',[]))
    return result


def category(path):
    if path=='Unity/ProjectSettings/ProjectSettings.asset':return 'Unity Player Settings: portrait policy and generated defaults'
    if path.startswith('Unity/ProjectSettings/') or path=='Unity/Packages/packages-lock.json': return 'Generated Unity settings or package lock'
    if path.startswith('Unity/Assets/HeartOfTheRain/Verification'): return 'Editor and opt-in development-player verification tools'
    if path.startswith('Unity/'):
        suffix=Path(path).suffix
        return {'.cs':'Native compile lifecycle lookup or rendering repair','.meta':'Intentional importer repair','.asset':'Serialized asset binding repair','.mat':'Native material reference tag repair','.prefab':'Native asset reference tag repair','.unity':'Native asset reference tag repair'}.get(suffix,'Unity project')
    if path.startswith('Codex_Handoff/Documentation/'): return 'Current handoff status and review'
    if path.startswith('Verification/Evidence/'): return 'Verification evidence'
    if path.startswith('Verification/'): return 'Verification tooling or pending QA worksheet'
    return 'Repository preparation'


def run():
    review93 = OUT/'Review93/Summary.json'
    if review93.exists():
        from Review93.collect_review93 import verify, STATUS
        verified = verify()
        if verified['status'] == STATUS:
            public = dict(verified, source_sha256=verified['sourceSHA256'],
                          summary='Verification/Evidence/Review93/Summary.json',
                          review='Codex_Handoff/Documentation/93_APP_BACKEND_OPERATIONAL_REVIEW.md')
            (OUT/'Verification_Summary.json').write_text(json.dumps(public, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
            return verified
        raise RuntimeError('CurrentReview93IsIncomplete')
    progress92 = OUT/'Progress92/Summary.json'
    if progress92.exists():
        from Progress92.collect_progress92 import verify
        verified = verify()
        public = dict(verified, source_sha256=verified['sourceSHA256'],
                      summary='Verification/Evidence/Progress92/Summary.json',
                      review='Codex_Handoff/Documentation/92_PROGRESS_BAR_REVIEW.md')
        (OUT/'Verification_Summary.json').write_text(json.dumps(public, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        return verified
    backdrop90 = OUT/'PageBackdrop90/Summary.json'
    if backdrop90.exists():
        from PageBackdrop90.collect_backdrop90 import verify
        verified = verify()
        public = dict(verified, source_sha256=verified['sourceSHA256'],
                      summary='Verification/Evidence/PageBackdrop90/Summary.json',
                      review='Codex_Handoff/Documentation/90_PAGE_BACKDROP_AND_SAFE_AREA_REVIEW.md')
        (OUT/'Verification_Summary.json').write_text(json.dumps(public, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        return verified
    regional89 = OUT/'RegionalAccounts89/Summary.json'
    if regional89.exists():
        from RegionalAccounts89.collect_review89 import verify
        verified = verify()
        public = dict(verified, source_sha256=verified['sourceSHA256'],
                      summary='Verification/Evidence/RegionalAccounts89/Summary.json',
                      review='Codex_Handoff/Documentation/89_REGIONAL_RANKINGS_VK_LOCAL_ADS_REVIEW.md')
        (OUT/'Verification_Summary.json').write_text(json.dumps(public, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        return verified
    display88 = OUT/'Display88/Summary.json'
    if display88.exists():
        from Display88.collect_display88 import verify
        verified = verify()
        public = dict(verified, source_sha256=verified['sourceSHA256'],
                      summary='Verification/Evidence/Display88/Summary.json',
                      review='Codex_Handoff/Documentation/88_FULL_DISPLAY_AND_DEVICE_FOLLOWUP.md')
        (OUT/'Verification_Summary.json').write_text(json.dumps(public, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        return verified
    review86 = OUT/'Review86/Summary.json'
    if review86.exists():
        from Review86.collect_review86 import verify
        verified = verify(json.loads(review86.read_text('utf-8-sig')))
        public = dict(verified, source_sha256=verified['sourceSHA256'],
                      summary='Verification/Evidence/Review86/Summary.json',
                      review='Codex_Handoff/Documentation/86_COMPREHENSIVE_APP_BACKEND_REVIEW.md')
        installed = OUT/'Install86/Current.json'
        if installed.exists():
            pointer = json.loads(installed.read_text('utf-8-sig'))
            proof = (ROOT/pointer['report']).resolve()
            assert proof.is_relative_to((OUT/'Install86').resolve())
            assert hashlib.sha256(proof.read_bytes()).hexdigest() == pointer['reportSHA256']
            deployment = json.loads(proof.read_text('utf-8-sig'))
            assert pointer['sourceSHA256'] == deployment['sourceSHA256'] == verified['sourceSHA256']
            assert pointer['status'] == deployment['status'] == 'PASS_INSTALLED_AND_STARTED86_MAIN_FRESH'
            assert deployment['sourceCheckpoint'] == 86 and deployment['index'] == 0 and deployment['serial'] == 'emulator-5554'
            assert deployment['apkSHA256'] == deployment['installedAPK_SHA256'] == verified['apks'][0]['sha256']
            assert deployment['startupErrorCount'] == 0 and deployment['otherInstancesUnchanged']
            assert hashlib.sha256((proof.parent/deployment['screenshot']).read_bytes()).hexdigest() == deployment['screenshotSHA256']
            assert hashlib.sha256((proof.parent/'Runtime.log').read_bytes()).hexdigest() == deployment['runtimeLogSHA256']
            public.update(reviewTimeApkInstalled=verified['currentApkInstalled'], currentApkInstalled=True,
                          installationFollowup=pointer, installationScope=deployment['scope'])
        physical = OUT/'Physical87/Current.json'
        if physical.exists():
            pointer = json.loads(physical.read_text('utf-8-sig'))
            assert set(pointer) == {'report', 'reportSHA256', 'sourceSHA256', 'apkSHA256'}
            relative = Path(pointer['report'])
            assert not relative.is_absolute() and '..' not in relative.parts
            proof = (ROOT/relative).resolve()
            assert proof.name == 'Summary.json' and proof.parent.parent == (OUT/'Physical87').resolve()
            assert hashlib.sha256(proof.read_bytes()).hexdigest() == pointer['reportSHA256']
            observed = json.loads(proof.read_text('utf-8-sig'))
            source = observed['sourceBinding']
            assert observed['schemaVersion'] == 1 and observed['checkpoint'] == 87
            assert observed['status'] == 'COMPLETED_PHYSICAL_REVIEW87_WITH_OPEN_GATES'
            assert observed['releaseApproved'] is False and observed['wholeGameSmoothnessCertified'] is False
            assert source['checkpoint'] == verified['source_checkpoint'] == 86
            assert source['manifest']['path'] == verified['sourceManifest']
            assert pointer['sourceSHA256'] == source['manifest']['sha256'] == verified['sourceSHA256']
            assert source['apk']['path'] == verified['apks'][0]['path']
            assert pointer['apkSHA256'] == source['apk']['sha256'] == verified['apks'][0]['sha256']
            from Physical87.report import verify as verify_physical87
            verify_physical87(proof.parent)
            # This supplement never replaces the frozen review86 status,
            # failures or evidence; current physical acceptance remains scoped.
            public['physicalDeviceReview'] = {
                'pointer': pointer, 'sourceCheckpoint': 86, 'checkpoint': 87,
                'status': observed['status'], 'checklistCounts': observed['checklistCounts'],
                'summary': proof.relative_to(ROOT).as_posix(), 'scope': observed['scope']}
        (OUT/'Verification_Summary.json').write_text(json.dumps(public, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        return verified
    recovery85 = OUT/'ShopAds85/ReservationRecovery85/Summary.json'
    if recovery85.exists():
        from Ads85.collect_reservation_recovery85 import verify_published
        verified = verify_published()
        public = dict(verified, source_sha256=verified['sourceSHA256'],
                      summary='Verification/Evidence/ShopAds85/ReservationRecovery85/Summary.json',
                      review='Codex_Handoff/Documentation/85_RUBLE_SHOP_AND_REWARDED_ADS_REVIEW.md')
        (OUT/'Verification_Summary.json').write_text(json.dumps(public, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        return verified
    ads85 = OUT/'ShopAds85/Summary.json'
    if ads85.exists():
        current = json.loads(ads85.read_text('utf-8-sig'))
        if current.get('source_checkpoint') == 85 and current.get('status') == 'PASS_TARGETED_SHOP_RUB_REWARDED_ADS85_WITH_RELEASE_GATES':
            from Ads85.collect_ads85 import build
            verified = build()
            # Keep the accepted SDK-free snapshot immutable. The later actual
            # full-game SDK compile has a separate, independently rechecked scope.
            from Ads85.collect_game_sdk85 import build as sdk_build
            sdk = sdk_build()
            sdk_path = OUT/'ShopAds85/SDK/FullGameBuild/Report.json'
            published_sdk = json.loads(sdk_path.read_text('utf-8-sig'))
            assert {k:v for k,v in sdk.items() if k != 'utc'} == {k:v for k,v in published_sdk.items() if k != 'utc'}, 'Full-game SDK supplement drifted'
            public = dict(verified, source_sha256=verified['sourceSHA256'],
                          summary='Verification/Evidence/ShopAds85/Summary.json',
                          review='Codex_Handoff/Documentation/85_RUBLE_SHOP_AND_REWARDED_ADS_REVIEW.md')
            public['isolatedFullGameSdkSupplement'] = dict(
                report=sdk_path.relative_to(ROOT).as_posix(),
                reportSHA256=hashlib.sha256(sdk_path.read_bytes()).hexdigest(),
                **{k:sdk[k] for k in ('status','scope','checkCount','apk','apkLaunched','sdkAdRequested','remainingGates')})
            (OUT/'Verification_Summary.json').write_text(json.dumps(public, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
            return verified
    connected84 = OUT/'ServerGameplay83/Summary.json'
    if connected84.exists():
        current = json.loads(connected84.read_text('utf-8-sig'))
        if current.get('sourceCheckpoint') == 84 and current.get('status') == 'PASS_CONNECTED_BACKEND84_TARGETED_NATIVE_AND_INTERNAL_COMPILE_WITH_EXTERNAL_GATES':
            from collect_connected_backend84 import Proof, collect, render_html
            verified = collect(Proof())
            connected84.write_text(json.dumps(verified, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
            (connected84.parent/'Comparison.html').write_text(render_html(verified), encoding='utf-8')
            public = dict(verified, source_checkpoint=84,
                          source_sha256=verified['sourceManifestSHA256'],
                          summary='Verification/Evidence/ServerGameplay83/Summary.json',
                          review='Codex_Handoff/Documentation/84_CONNECTED_BACKEND_APP_REVIEW.md')
            (OUT/'Verification_Summary.json').write_text(json.dumps(public, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
            return verified
    rustore81 = OUT/'RuStore81/Summary.json'
    if rustore81.exists():
        current = json.loads(rustore81.read_text('utf-8-sig'))
        if current.get('source_checkpoint') == 81 and current.get('status') == 'PASS_RUSTORE81_PORTABLE_FOUNDATION_WITH_RELEASE_GATES':
            from collect_rustore81_results import main as collect_rustore81
            return collect_rustore81(publish=True)
    russian80 = OUT/'LaunchRuStoreR3/Summary.json'
    if russian80.exists():
        current = json.loads(russian80.read_text('utf-8-sig'))
        if current.get('source_checkpoint') == 80 and current.get('status') == 'PASS_RUSSIAN_BRANDING_WITH_UNITY_SPLASH_LICENSE_GATE':
            from collect_russian_launch80_results import main as collect_russian_launch80
            return collect_russian_launch80(publish=True)
    if (OUT/'Gameplay79/Summary.json').exists():
        from collect_gameplay79_results import main as collect_gameplay79
        return collect_gameplay79(publish=True)
    if (OUT/'Gameplay78/Summary.json').exists():
        from collect_gameplay78_results import main as collect_gameplay78
        return collect_gameplay78(publish=True)
    if (OUT/'Gameplay77/Summary.json').exists():
        from collect_gameplay77_results import main as collect_gameplay77
        return collect_gameplay77(publish=True)
    if (OUT/'Gameplay76/Summary.json').exists():
        from collect_gameplay76_results import main as collect_gameplay76
        return collect_gameplay76()
    if (OUT/'Gameplay75/Summary.json').exists():
        from collect_gameplay75_results import main as collect_gameplay75
        return collect_gameplay75()
    if (OUT/'Gameplay74/Summary.json').exists():
        from collect_gameplay74_results import main as collect_gameplay74
        return collect_gameplay74()
    if (OUT/'LocalCascade73/Summary.json').exists():
        from collect_local_cascade73_results import main as collect_local_cascade73
        return collect_local_cascade73()
    if (OUT/'Gameplay72/Summary.json').exists():
        from collect_gameplay72_results import main as collect_gameplay72
        return collect_gameplay72()
    if (OUT/'ShopBounds/Summary.json').exists():
        from collect_shop_bounds_results import main as collect_shop_bounds
        return collect_shop_bounds()
    if (OUT/'NoMovesR3/Summary.json').exists():
        from collect_no_moves_r3_results import main as collect_no_moves_r3
        return collect_no_moves_r3()
    if (OUT/'RepeatMoves/Summary.json').exists():
        from collect_repeat_moves_results import main as collect_repeat_moves
        return collect_repeat_moves()
    if (OUT/'NoMovesR2/Summary.json').exists():
        from collect_no_moves_r2_results import main as collect_no_moves
        return collect_no_moves()
    if (OUT/'CascadeResponsiveness/Summary.json').exists():
        from collect_cascade_responsiveness import main as collect_cascade
        return collect_cascade()
    if (OUT/'IndependentReview66/Loading_Art_Lifetime.json').exists():
        from collect_independent_review66_results import main as collect_independent_review66
        return collect_independent_review66()
    if (OUT/'GameplayLoadingR1/Native_Review.json').exists():
        from collect_gameplay_loading_r1_results import main as collect_gameplay_loading_r1
        return collect_gameplay_loading_r1()
    if (OUT/'HomeLivesR1/Native_Review.json').exists():
        from collect_home_lives_r1_results import main as collect_home_lives_r1
        return collect_home_lives_r1()
    if (OUT/'RainCupR1/Native_Review.json').exists():
        from collect_rain_cup_r1_results import main as collect_rain_cup_r1
        return collect_rain_cup_r1()
    if (OUT/'WellworksR1/Native_Review.json').exists():
        from collect_wellworks_r1_results import main as collect_wellworks_r1
        return collect_wellworks_r1()
    if (OUT/'UIClarityR1/After/Report.json').exists():
        from collect_ui_clarity_r1_results import main as collect_ui_clarity_r1
        return collect_ui_clarity_r1()
    if (OUT/'DailyGiftR1/Native_Review.json').exists():
        from collect_daily_gift_r1_results import main as collect_daily_gift_r1
        return collect_daily_gift_r1()
    if (OUT/'AccountR6/Native_Review.json').exists():
        from collect_account_r6_results import main as collect_account_r6
        return collect_account_r6()
    if (OUT/'ObstacleDensity/Android/Main_Installation.json').exists():
        from collect_obstacle_density_results import main as collect_obstacle_density
        return collect_obstacle_density()
    if (OUT/'CrateBurst/Android/Main_Installation.json').exists():
        from collect_crate_burst_results import main as collect_crate_burst
        return collect_crate_burst()
    if (OUT/'LoadingBar/Android/Main_Installation.json').exists():
        from collect_loading_bar_results import main as collect_loading_bar
        return collect_loading_bar()
    if (OUT/'ProfileClarity/After/Native_Review.json').exists():
        from collect_profile_clarity_results import main as collect_profile_clarity
        return collect_profile_clarity()
    if (OUT/'LaunchIntegration/Native_Review.json').exists():
        from collect_launch_integration_results import main as collect_launch_integration
        return collect_launch_integration()
    if (OUT/'ProfileDesignAndroid/Main_Installation.json').exists():
        from collect_profile_design_android_results import main as collect_profile_design_android
        return collect_profile_design_android()
    if (OUT/'ProfileDesignKit/Native_Review.json').exists():
        from collect_profile_design_kit_results import main as collect_profile_design_kit
        return collect_profile_design_kit()
    if (OUT/'HomeHeaderAndroid/Main_Installation.json').exists():
        from collect_home_header_android_results import main as collect_home_header_android
        return collect_home_header_android()
    if (OUT/'HomeHeaderAvatar/After/Native_Review.json').exists():
        from collect_home_header_avatar_results import main as collect_home_header_avatar
        return collect_home_header_avatar()
    if (OUT/'HomeLevelButton/Native_Review.json').exists():
        from collect_home_level_button_results import main as collect_home_level_button
        return collect_home_level_button()
    if (OUT/'ProfileM71/Source_SHA256.json').exists():
        from collect_profile_m71_results import main as collect_profile_m71
        return collect_profile_m71()
    if (OUT/'ChapterBackground/Source_SHA256.json').exists():
        from collect_chapter_background_results import main as collect_chapter_background
        return collect_chapter_background()
    if (OUT/'BackendGiftUI/Source_SHA256.json').exists():
        from collect_backend_gift_ui_results import main as collect_backend_gift_ui
        return collect_backend_gift_ui()
    if (OUT/'Backend/Source_SHA256.json').exists():
        from collect_backend_results import main as collect_backend
        return collect_backend()
    if (OUT/'ProfileEvents/Source_SHA256.json').exists():
        from collect_profile_event_results import main as collect_profile_events
        return collect_profile_events()
    if (OUT/'RainCup/Player_Source_SHA256.json').exists():
        from collect_rain_cup_results import run as collect_rain_cup
        return collect_rain_cup()
    if (OUT/'Wellworks/Player_Source_SHA256.json').exists():
        from collect_wellworks_results import run as collect_wellworks
        return collect_wellworks()
    if (OUT/'DailyGift/Player_Source_SHA256.json').exists():
        from collect_daily_gift_results import run as collect_daily
        return collect_daily()
    if (OUT/'PowerWarmup/Player_Source_SHA256.json').exists():
        from collect_power_warmup_results import run as collect_warmup
        return collect_warmup()
    if (OUT/'GameplayAudit/Mixed_Swap_Checks.json').exists():
        from collect_gameplay_audit_results import run as collect_gameplay
        return collect_gameplay()
    if (OUT/'M70R2/Native_Checks.json').exists():
        from collect_m70r2_results import run as collect_r2
        return collect_r2()
    if (OUT/'IndividualFall/Native_Checks.json').exists():
        from collect_individual_fall_results import run as collect_individual
        return collect_individual()
    if (OUT/'ObstacleFall/Native_Checks.json').exists():
        from collect_obstacle_fall_results import run as collect_fall
        return collect_fall()
    checks=read('Native/Native_Checks.json')
    smoke=read('Native/Play_Smoke.json')
    build=read('Native/Android_Build.json')
    artifact=read('Native/APK_Artifact.json')
    current='SwapCreation' if (OUT/'SwapCreation/Native_Checks.json').exists() else 'M70' if (OUT/'M70/Native_Checks.json').exists() else 'Portrait' if (OUT/'Portrait/Native_Checks.json').exists() else 'ObstacleGravity' if (OUT/'ObstacleGravity/Native_Checks.json').exists() else 'Timing' if (OUT/'Timing/Native_Checks.json').exists() else 'Fluidity'
    player_root=current+'/LDPlayer' if (OUT/current/'LDPlayer/Installation.json').exists() else 'Regression/LDPlayer'
    emulator=read(player_root+'/Installation.json') if (OUT/player_root/'Installation.json').exists() else read('LDPlayer/Installation.json') if (OUT/'LDPlayer/Installation.json').exists() else None
    editor_regression=read('Regression/Editor/Regression.json') if (OUT/'Regression/Editor/Regression.json').exists() else None
    editor_checkpoint=regression_summary(editor_regression)
    if editor_checkpoint:
        editor_checkpoint['checkpoint_scope']='Historical pre-M68 rendered Editor run. Current M68/schedule checks and final Android APK results are separate fields.'
    android_regression=read(player_root+'/Regression.json') if (OUT/player_root/'Regression.json').exists() else None
    fluidity=read('Fluidity/Native_Checks.json') if (OUT/'Fluidity/Native_Checks.json').exists() else None
    m68_smoke=read('Fluidity/M68_Play_Smoke.json') if (OUT/'Fluidity/M68_Play_Smoke.json').exists() else None
    performance=read(current+'/Performance_Comparison.json') if (OUT/current/'Performance_Comparison.json').exists() else None
    touch=read(current+'/Touch/Touch_Smoke.json') if (OUT/current/'Touch/Touch_Smoke.json').exists() else None
    timing=read('Timing/Native_Checks.json') if (OUT/'Timing/Native_Checks.json').exists() else None
    gravity=read('ObstacleGravity/Native_Checks.json') if (OUT/'ObstacleGravity/Native_Checks.json').exists() else None
    m70=read('M70/Native_Checks.json') if current=='M70' else None
    portrait=read('Portrait/Native_Checks.json') if current=='Portrait' else None
    swap=read('SwapCreation/Native_Checks.json') if current=='SwapCreation' else None
    if swap:touch=read('SwapCreation/Touch/Report.json')
    timing_smoke=read('Timing/Play_Smoke.json') if timing else None
    integrity=read('Integrity_Current.json')
    metadata=read('Native/Metadata_Preservation_Regression.json') if (OUT/'Native/Metadata_Preservation_Regression.json').exists() else read('Native/Metadata_Preservation.json')
    content=read('Content_Review.json')
    apk=Path(artifact['path'])
    actual_sha=hashlib.sha256(apk.read_bytes()).hexdigest()
    assert actual_sha==artifact['sha256'], 'APK evidence is stale'
    assert checks['status']=='PASS_NATIVE_EDITOR_CHECKS' and checks['failed']==0
    assert smoke['status']=='PASS_NATIVE_PLAY_SMOKE' and not smoke['errors']
    assert build['status']=='PASS_ANDROID_DEVELOPMENT_BUILD' and build['errors']==0
    assert integrity['status'].startswith('PASS_') and not integrity['unexpected_changed_baseline_files']
    assert content['workbook']['independently_checked']==938 and not content['workbook']['mismatches']
    assert not any(row['issues'] for row in content['localization'])
    if android_regression:
        assert android_regression['status']=='PASS_NATIVE_REGRESSION' and not android_regression['failures'], 'Android regression did not pass'
        assert emulator['sha256']==actual_sha, 'Emulator installation hash is stale'
    if fluidity:
        assert fluidity['status']=='PASS_NATIVE_FLUIDITY_CHECKS' and not fluidity['failures']
        assert m68_smoke['status']=='PASS_NATIVE_M68_PLAY_SMOKE' and not m68_smoke['error']
        if performance:assert performance['apk_sha256']==actual_sha, 'Performance evidence is stale'
        elif not (gravity or portrait):raise AssertionError('Performance evidence missing')
        if not (portrait or swap):assert touch and touch['status']=='PASS_ACTUAL_ANDROID_INPUT_CAPTURE_REVIEW' and touch['apk_sha256']==actual_sha, 'Final input capture review is incomplete or stale'
        source=read(current+'/Player_Source_SHA256.json')
        assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected for path,expected in source['files'].items()), 'Player source changed after build'
    if timing:
        assert timing['status']=='PASS_NATIVE_TIMING_CHECKS' and not timing['failures']
        assert timing_smoke['status']=='PASS_NATIVE_TIMING_PLAY_SMOKE' and not timing_smoke['error']
        assert read('Timing/Render/Report.json')['status']=='PASS_NATIVE_PORTAL_RENDER'
    if gravity:
        assert gravity['status']=='PASS_NATIVE_OBSTACLE_GRAVITY' and not gravity['failures']
        assert read('ObstacleGravity/Campaign_Replay_Refresh.json')['status']=='PASS_CAMPAIGN_LOGIC'
    if gravity and not (portrait or m70 or swap):
        visual=read('ObstacleGravity/Stack_Render_Review.json')
        assert visual['status']=='PASS_NATIVE_STACK_RENDER_REVIEW' and visual['apk_sha256']==actual_sha
        for name in ('MainInstance_Final_Installation','QA_Final_Installation'):
            installed=read('ObstacleGravity/'+name+'.json')
            assert installed['status']=='PASS_FINAL_APK_INSTALLED_AND_RUNNING' and installed['apk_sha256']==actual_sha
    if portrait:
        assert portrait['status']=='PASS_NATIVE_PORTRAIT_CHECKS' and not portrait['failures']
        assert read('Portrait/APK_Orientation.json')['apk_sha256']==actual_sha
        matrix=read('Portrait/DeviceMatrix/Report.json')
        assert matrix['status']=='PASS_NATIVE_PORTRAIT_DEVICE_MATRIX' and matrix['restored'] and matrix['apk_sha256']==actual_sha
        assert read('Portrait/Frame_Manifest.json')['all_frames_portrait']
        for name in ('MainInstance_Final_Installation','QA_Final_Installation'):
            installed=read('Portrait/'+name+'.json')
            assert installed['status']=='PASS_FINAL_APK_INSTALLED_AND_RUNNING' and installed['apk_sha256']==actual_sha
    if m70:
        assert m70['status']=='PASS_NATIVE_M70_CHECKS' and not m70['failures'] and m70['frames']==586
        device=read('M70/LDPlayer/M70_Device.json')
        assert device['status']=='PASS_NATIVE_M70_DEVICE' and not device['failures']
        assert dt.datetime.fromisoformat(device['utc'].replace('Z','+00:00'))>=dt.datetime.fromisoformat(emulator['utc']), 'M70 device report predates this installation'
        assert len(device['textures'])==7 and all(t['width']==t['height']==2048 and t['loadedCopies']==1 for t in device['textures'])
        assert read('M70/Offline_Assets.json')['status']=='PASS_OFFLINE_M70_ASSET_CHECKS'
        assert read('M70/Frame_Manifest.json')['all_frames_portrait']
        assert read('M70/APK_Orientation.json')['apk_sha256']==actual_sha
        packaging=read('M70/APK_Packaging.json')
        assert packaging['status']=='PASS_CLEAN_GRADLE_APK_PACKAGING' and packaging['afterSHA256']==actual_sha and packaging['sameSignerCertificate'] and not packaging['changedNonSignatureEntries']
        visual=read('M70/Visual_Review.json')
        assert visual['status']=='PASS_NATIVE_M70_VISUAL_REVIEW' and visual['apk_sha256']==actual_sha
        assert read('M70/APK_Payloads.json')['status']=='PASS_M70_APK_TEXTURE_PAYLOADS' and read('M70/APK_Payloads.json')['apk_sha256']==actual_sha
        contract=json.loads((ROOT/'Unity/Assets/HeartOfTheRain/M69/Data/M70_PowerupContract.json').read_text())
        for entry in contract['entries']:
            for name in ('texture','resourceTexture'):
                assert hashlib.sha256((ROOT/'Unity'/entry[name]).read_bytes()).hexdigest()==entry['textureSHA256']
            assert hashlib.sha256((ROOT/'Unity'/entry['manifest']).read_bytes()).hexdigest()==entry['manifestSHA256']
        for name in ('MainInstance_Final_Installation','QA_Final_Installation'):
            installed=read('M70/'+name+'.json')
            assert installed['status']=='PASS_FINAL_APK_INSTALLED_AND_RUNNING' and installed['apk_sha256']==actual_sha
    if swap:
        assert swap['status']=='PASS_NATIVE_SWAP_CREATION' and not swap['failures']
        assert touch['status']=='PASS_ACTUAL_SWAP_CREATION_VISUAL_REVIEW' and touch['apk_sha256']==actual_sha
        assert len(touch['cases'])==4 and all(c['status']=='PASS_ACTUAL_SWAP_CREATION_INPUT' and not c['failures'] for c in touch['cases'])
        visual=read('SwapCreation/Visual_Review.json')
        assert visual['status']=='PASS_NATIVE_SWAP_CREATION_VISUAL_REVIEW' and visual['apk_sha256']==actual_sha
        packaging=read('SwapCreation/APK_Packaging.json')
        assert packaging['status']=='PASS_CLEAN_GRADLE_APK_PACKAGING' and packaging['afterSHA256']==actual_sha and packaging['sameSignerCertificate'] and not packaging['changedNonSignatureEntries']
        assert read('SwapCreation/Frame_Manifest.json')['all_frames_portrait']
        assert read('SwapCreation/APK_Orientation.json')['apk_sha256']==actual_sha
        assert read('SwapCreation/APK_Payloads.json')['apk_sha256']==actual_sha
        assert read('SwapCreation/Campaign_Replay_Refresh.json')['status']=='PASS_CAMPAIGN_LOGIC'
        for name in ('MainInstance_Final_Installation','QA_Final_Installation'):
            installed=read('SwapCreation/'+name+'.json')
            assert installed['status']=='PASS_FINAL_APK_INSTALLED_AND_RUNNING' and installed['apk_sha256']==actual_sha
    # Reserve both generated paths before querying Git, including them in the
    # final inventory without self-referential content hashes.
    summary_path=OUT/'Verification_Summary.json'
    csv_path=OUT/'Changed_Files.csv'
    summary_path.touch(exist_ok=True); csv_path.touch(exist_ok=True)
    tracked=subprocess.run(['git','diff','--name-only','--no-renames','-z'],cwd=ROOT,check=True,stdout=subprocess.PIPE).stdout.decode().split('\0')
    untracked=subprocess.run(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT,check=True,stdout=subprocess.PIPE).stdout.decode().split('\0')
    rows=[{'path':path,'status':'MODIFIED' if path in tracked else 'ADDED','category':category(path)} for path in sorted((set(tracked)|set(untracked))-{''})]
    importer_only={'Unity/'+p for p in integrity.get('archived_importer_serialization_only_files',[])}
    for row in rows:
        if row['path'] in importer_only:row['category']='Archived Unity importer serialization only'
    with csv_path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['status','path','category']);writer.writeheader();writer.writerows(rows)
    summary={
        'status':'PASS_VERIFICATION_WITH_OPEN_RELEASE_GATES',
        'date':build['utc'][:10],'runtime_baseline':'M67R4 plus documented verification repairs, owner-supplied M68 celebration, approved timing refinements, obstacle gravity repair and portrait launch/resume policy, plus owner-supplied M70 power-up assets and approved swap/rocket creation repairs',
        'unity':'2022.3.62f3 (96770f904ca7)','first_device_platform':'Android',
        'native_editor_checks':{'passed':checks['passed'],'failed':checks['failed'],'scope':checks['scope']},
        'native_play_smoke':{'status':smoke['status'],'checks':smoke['checks'],'scope':smoke['scope']},
        'expanded_editor_regression':editor_checkpoint,
        'android_regression':regression_summary(android_regression),
        'fluidity_native_checks':fluidity,
        'm68_play_smoke':m68_smoke,
        'approved_timing_checks':timing,
        'obstacle_gravity_checks':gravity,
        'portrait_native_checks':portrait,
        'm70_native_checks':m70,
        'm70_apk_packaging':read('M70/APK_Packaging.json') if m70 else None,
        'm70_device_checks':read('M70/LDPlayer/M70_Device.json') if m70 else None,
        'portrait_device_matrix':read('Portrait/DeviceMatrix/Report.json') if portrait else None,
        'current_evidence_branch':current,
        'swap_creation_native_checks':swap,
        'swap_creation_visual_review':read('SwapCreation/Visual_Review.json') if swap else None,
        'performance_scope':'Current swap/creation gestures and rendered poses are verified; no new frame-budget or physical-device performance claim.' if swap else 'Fresh pre-M70 versus M70 emulator measurement; physical-device profiling and heavy-combo spikes remain open.' if m70 and performance else 'No new frame-budget claim for portrait/gravity repairs. Prior timing performance, including heavy-combo spikes, remains a historical checkpoint.' if gravity or portrait else 'Current branch comparative measurement.',
        'timing_play_smoke':timing_smoke,
        'comparative_performance':performance,
        'android_input_capture_review':touch,
        'gameplay_comparison_review':{'evidence':'Verification/Evidence/GameplayComparison/Review.json','scope':'20 October direct installed-app comparison; open presentation findings, not a new runtime repair or performance pass.'} if (OUT/'GameplayComparison/Review.json').exists() else None,
        'android':{'status':build['status'],'errors':build['errors'],'warnings':build['warnings'],'apk_bytes':artifact['bytes'],'apk_sha256':actual_sha,'apk':str(apk),'physical_device_execution':'NOT_RUN','emulator_installation':emulator,
                   'original_instance_installation':read(current+'/MainInstance_Final_Installation.json') if (OUT/current/'MainInstance_Final_Installation.json').exists() else None,
                   'qa_final_installation':read(current+'/QA_Final_Installation.json') if (OUT/current/'QA_Final_Installation.json').exists() else None,
                   'preferences_preservation':read(current+'/Preferences_Preservation.json') if (OUT/current/'Preferences_Preservation.json').exists() else None},
        'integrity':{'baseline_files':integrity['baseline_files'],'unchanged':integrity['unchanged'],'documented_changes':len(integrity['documented_changed_baseline_files']),'unexpected_changes':len(integrity['unexpected_changed_baseline_files']),'historically_restored_metadata':metadata['restored'],'current_archived_importer_round_trips':len(importer_only),'intentional_importer_repairs':metadata['intentional_repairs_retained']},
        'workbook_formula_cells_checked':938,'changed_paths_by_category':dict(collections.Counter(r['category'] for r in rows)),
        'open_gates':['Physical Android lifecycle/low-memory/thermal/performance and store certification','Native-speaker and owner visual review across device sizes','Durable profile and inventory across restarts','Durable idempotent attempt settlement','Human playtesting and balance of all 50 levels','Commerce/social/event/analytics/support services and shipping configuration'],
        'review':'Codex_Handoff/Documentation/21_SWAP_AND_ROCKET_CREATION_REVIEW.md' if swap else 'Codex_Handoff/Documentation/20_M70_POWERUP_REVIEW.md' if m70 else 'Codex_Handoff/Documentation/19_PORTRAIT_ORIENTATION_REVIEW.md' if portrait else 'Codex_Handoff/Documentation/18_OBSTACLE_GRAVITY_REVIEW.md' if gravity else 'Codex_Handoff/Documentation/17_FLUIDITY_AND_M68_REVIEW.md' if fluidity else 'Codex_Handoff/Documentation/16_PLAYBACK_AND_UI_REVIEW.md','initial_review':'Codex_Handoff/Documentation/15_VERIFICATION_REVIEW.md','runbook':'Verification/README.md'
    }
    summary_path.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('native_play_smoke','changed_paths_by_category')},indent=2))


if __name__=='__main__': run()
