"""Validate the native-only Settings/account checkpoint without claiming provider integration."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Verification/Evidence/AccountR6'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
    source=read(OUT/'Source_SHA256.json');assert all(sha(ROOT/p)==h for p,h in source['files'].items()),'Native-verified inputs changed'
    native=read(OUT/'Native_Review.json');general=read(OUT/'General_Checks.json');package=read(OUT/'Package_Review.json');visual=read(OUT/'Visual_Review.json');audit=read(OUT/'Asset_Audit.json')
    assert native['status']=='PASS_NATIVE_ACCOUNT_R6' and not native['error'] and native['checks']==939 and native['layouts']==34 and len(native['frames'])==65
    assert general['status']=='PASS_NATIVE_EDITOR_CHECKS' and general['failed']==0 and general['passed']==533
    for name in ['Native_Process.json','General_Process.json']:
        p=read(OUT/name);assert p['exitCode']==0 and not p['timedOut']
    assert package['zip_crc']=='PASS' and package['unitypackage_patch_asset_matches']==13
    assert audit['original_metadata_unchanged'] and len(audit['changed_existing_inputs'])==3 and audit['new_original_images']==4
    assert all(sha(OUT/p)==h for p,h in visual['frames'].items()) and len(visual['frames'])==16
    assert set(native['frames'])==set(source['capture_sha256']) and all(sha(OUT/p)==h for p,h in source['capture_sha256'].items())
    for p in audit['changed_existing_inputs']:assert p in source['files']
    summary={'utc':datetime.now(timezone.utc).isoformat(),'status':'PASS_NATIVE_ACCOUNT_R6_SOURCE_ONLY','scope':'Native Settings > Save Progress route, modal input/scroll/focus/preferences, actual local identity and service-driven account/sync presentation. Linked/callback states use an explicit Editor fixture. No Google/Apple authentication, cloud upload/restore, Android build or device validation in this checkpoint.','native_account_checks':native['checks'],'native_cases':34,'locale_size_combinations':30,'account_status_cases':4,'captured_frames':65,'inspected_frames':16,'general_editor_checks':533,'changed_existing_inputs':audit['changed_existing_inputs'],'imported_new_images':4,'source_inputs':len(source['files']),'source_sha256':sha(OUT/'Source_SHA256.json'),'apk_built':False,'apk_installed':False,'provider_service_connected':False,'collector_sha256':sha(Path(__file__))}
    write(OUT/'Verification_Summary.json',summary)
    deployment=read(ROOT/'Verification/Evidence/Checkpoint53/Android/Main_Installation.json')
    write(ROOT/'Verification/Evidence/Native_Source_Checkpoint.json',{'utc':summary['utc'],'status':summary['status'],'scope':summary['scope'],'source_checkpoint':55,'review':'Codex_Handoff/Documentation/55_ACCOUNT_R6_REVIEW.md','summary':'Verification/Evidence/AccountR6/Verification_Summary.json','source_sha256':summary['source_sha256'],'installed_checkpoint':54,'deployment_scope':'Last recorded deployment, not rechecked this turn. Account R6 is native-source-only.','android_apk_sha256':deployment['apk_sha256'],'android_apk_matches_current_source':False})
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
