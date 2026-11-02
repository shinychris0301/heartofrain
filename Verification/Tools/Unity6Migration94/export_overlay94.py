"""Export-only private migration overlay. Never extracts, applies or changes a project."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'Verification/Evidence/Unity6Migration94'
MAIN = ROOT / 'Unity'
CANDIDATE = ROOT / '.verification-cache/Unity6Migration94/Project'
PRIVATE = ROOT / '.verification-cache/Unity6Migration94/Handoff'
AUDIT = EVIDENCE / 'SourceAudit/Set02/Report.json'
BASELINE = EVIDENCE / 'MainSources_Before.json'
PREPARATION = EVIDENCE / 'Preparation.json'
VERSION = '6000.6.6f1'
COMMIT = '196f606d'
BASELINE_SHA = '773493400ad57ea52db9e9cf11ba0cd1774fd47071c179ad15d88a4480cebccb'
ACCEPTED93_SHA = 'e6b761f46bd57a6d7b0c3c69a0cf00a3411fad4c700ce31e44598199a9432cfd'
STATUS = 'PASS_ISOLATED_CANDIDATE_SOURCE_AUDIT94_WITH_CONFIGURATION_REVIEW_REQUIRED'
SCOPE = 'Export-only private source overlay for a fresh isolated copy of the exact196f606d/5407-input base. Not a full project, APK, successful Android build, production release or removal of host security restrictions. No SDK/tool binaries, caches, profiles, credentials or raw logs are exported. No extraction, application or project mutation.'


def need(value, reason):
    if not value:
        raise ValueError(reason)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(Path(path).read_bytes())


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def metadata(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT), 'Overlay94WorkspaceBindingRequired')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def audit_module():
    path = Path(__file__).with_name('audit_candidate94.py')
    spec = importlib.util.spec_from_file_location('overlay94_read_only_source_auditor', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def safe_relative(relative):
    need(isinstance(relative, str) and relative and '\\' not in relative and ':' not in relative
         and not relative.startswith('/') and not relative.endswith('/'), 'Overlay94UnsafeRelativePath')
    parts = PurePosixPath(relative).parts
    need('/'.join(parts) == relative and all(part not in ('', '.', '..') for part in parts), 'Overlay94UnsafeRelativePath')
    need(parts[0] in ('Assets', 'Packages', 'ProjectSettings') and len(parts) > 1, 'Overlay94OnlyProjectInputsAllowed')
    allowed = { 'Assets': {'.cs', '.meta'}, 'Packages': {'.json'}, 'ProjectSettings': {'.asset', '.json', '.txt'} }
    need(PurePosixPath(relative).suffix.lower() in allowed[parts[0]], 'Overlay94OnlyReviewedTextInputKindsAllowed')
    denied = {'.dll','.so','.a','.aar','.jar','.apk','.aab','.exe','.dex','.jks','.keystore','.p12','.pfx','.key','.pem','.db','.sqlite','.zip','.7z','.log'}
    stem = relative[:-5] if relative.endswith('.meta') else relative
    need(not any(part.lower() in ('library','temp','logs','obj','profiles','credentials','sdk','ndk','jdk') for part in parts)
         and PurePosixPath(stem).suffix.lower() not in denied, 'Overlay94ForbiddenBinaryCacheOrCredentialPath')
    return relative


def safe_text(relative, raw):
    safe_relative(relative)
    need(b'\0' not in raw, 'Overlay94BinaryPayloadRefused')
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('Overlay94NonUTF8PayloadRefused') from None
    need(not re.search(r'-----BEGIN (?:[A-Z ]* )?PRIVATE KEY-----', text), 'Overlay94PrivateKeyRefused')
    sensitive = r'(?:password|keystorepass|keyaliaspass|access.?token|refresh.?token|api.?secret|client.?secret|private.?key|api.?key|signing.?credential)'
    # Reject populated serialized secret fields and literal secret assignments. Values never enter errors.
    for match in re.finditer(r'(?im)^[ \t]*[A-Za-z0-9_]*'+sensitive+r'[A-Za-z0-9_]*[ \t]*:[ \t]*([^\r\n]*)', text):
        value = match.group(1).strip()
        need(value in ('', '""', "''", 'null', '~'), 'Overlay94PopulatedSerializedCredentialRefused')
    need(not re.search(r'(?i)\b'+sensitive+r'\b\s*=\s*[\"\'][^\"\'\r\n]+[\"\']', text), 'Overlay94LiteralCredentialRefused')
    return raw


def overlay_rows(before, after):
    need(isinstance(before, dict) and isinstance(after, dict), 'Overlay94FullManifestsRequired')
    need(not (set(before)-set(after)), 'Overlay94DeletionsCannotBeRepresentedByOverlay')
    for relative in set(before) | set(after):
        need(isinstance(relative, str) and relative.startswith(('Assets/','Packages/','ProjectSettings/'))
             and '\\' not in relative and '..' not in PurePosixPath(relative).parts, 'Overlay94ManifestPathRefused')
    changed = []
    for relative in sorted(after):
        if before.get(relative) == after[relative]: continue
        safe_relative(relative)
        for item in (before.get(relative), after[relative]):
            if item is not None:
                need(isinstance(item, dict) and re.fullmatch('[a-f0-9]{64}', item.get('sha256',''))
                     and type(item.get('bytes')) is int and item['bytes'] >= 0, 'Overlay94FullByteBindingsRequired')
        changed.append({'path':relative, 'kind':'added' if relative not in before else 'changed',
                        'before':before.get(relative), 'after':after[relative]})
    need(changed, 'Overlay94NonemptyReviewedOverlayRequired')
    return changed


def validate_report(report, baseline, candidate, preparation, changes):
    need(report.get('status') == STATUS and report.get('violations') == [] and report.get('mainInputCount') == 5407
         and report.get('mainInputsUnchanged') is True and report.get('candidateInputsStable') is True
         and report.get('allOriginalGuidsPreserved') is True and report.get('backendHeadSourceUnchanged') is True
         and report.get('inputsModifiedByAudit') is False and report.get('sdkOrUnityOrDeviceCommandsExecuted') is False,
         'Overlay94PassedExactSourceAuditRequired')
    need(preparation.get('status') == 'PASS_EXACT_MAIN_COPY94' and preparation.get('authorization') == 'USER_APPROVED_ISOLATED_UNITY6_MIGRATION'
         and preparation.get('baselineCommit') == COMMIT and preparation.get('mainInputCount') == 5407
         and preparation.get('project') == CANDIDATE.relative_to(ROOT).as_posix(), 'Overlay94AuthorizedExactMigrationBaseRequired')
    need(baseline.get('inputCount') == len(baseline.get('files',{})) == 5407
         and candidate.get('inputCount') == len(candidate.get('files',{})) == report.get('candidateInputCount'), 'Overlay94Complete5407BaseAndCandidateRequired')
    expected = {'added':sum(row['kind']=='added' for row in changes), 'changed':sum(row['kind']=='changed' for row in changes), 'deleted':0}
    need(report.get('changeCounts') == expected, 'Overlay94ReviewedChangeCountsRequired')


def readme(overlay_count):
    return f'''Heart of the Rain — isolated Unity 6 migration overlay94\n\nThis ZIP is NOT a complete project and NOT an APK. It does not contain the\nUnity Editor, Android modules/SDK/NDK/JDK, Bee tools, runtime binaries, Library,\nprofiles, signing keys, credentials or raw logs. It is an export, not a build.\n\nRequired base\n- Obtain the authorized complete repository at commit {COMMIT}.\n- Create a fresh isolated copy; keep the approved Unity2022/main project intact.\n- Before manual overlay, require ALL5,407 Unity Assets/Packages/ProjectSettings\n  inputs to match Manifests/BaseUnity5407.json exactly (keys start Unity/).\n  A commit label alone is insufficient: exact bytes and original GUIDs matter.\n- Use Unity {VERSION} with matching official Android modules/toolchain on\n  another approved build machine. No host-security bypass is included.\n\nContents and manual review\n- Overlay/ contains only {overlay_count} changed or new project-input files.\n- Manifests/CandidateUnity6.json lists the full intended post-overlay inputs,\n  with paths relative to the isolated Unity project.\n- Manifests/MigrationOverlay94.json binds every before/after file, the exact\n  source-audit receipt and both complete manifests.\n- Review these files, then manually copy Overlay/ into the fresh isolated\n  project if its exact base was verified. There is no apply/extraction script.\n- Require the entire resulting Assets/Packages/ProjectSettings inventory to\n  equal CandidateUnity6.json before allowing further imports/build changes.\n- Editor verification fixtures reference the original workspace, historical\n  controls and evidence. This overlay alone cannot reproduce those suites.\n  Obtain the authorized full workspace/control artifacts separately.\n\nOpen acceptance gates\nAndroid production is NOT approved. The originating machine cannot complete\nits Android build because Windows VerifiedAndReputableDesktop policy blocks\nthe unsigned Bee Android toolchain DLL (SHA prefix9d7158). Moving source does\nnot prove that another host can build it. Re-run actual compile, native suites,\nAndroid static checks and startup/device tests on the approved machine.\nKeep trusted backend replay pinned2022; this overlay does not migrate it.\nThe350-command model diagnostic retains a strict raw-turn JSON hash FAIL even\nthough sampled runtime values and all final checkpoints match.\nProvider/payment/ad/signing/hosting/legal/moderation/performance and wider\nregression gates remain separate. No production readiness is claimed.\n'''.encode('utf-8')


def archive_payloads(project, changes, baseline_raw, candidate_raw, context, reject_links):
    payloads = {'README.txt':readme(len(changes)), 'Manifests/BaseUnity5407.json':baseline_raw,
                'Manifests/CandidateUnity6.json':candidate_raw}
    for row in changes:
        relative = safe_relative(row['path']); source = project / relative; reject_links(source)
        raw = source.read_bytes(); need({'sha256':sha_bytes(raw),'bytes':len(raw)} == row['after'], 'Overlay94CandidateFileChangedWhileReading')
        payloads['Overlay/'+relative] = safe_text(relative,raw)
    declaration = {'schemaVersion':1,'scope':SCOPE,'baseCommit':COMMIT,'unity':VERSION,
                   'overlayFiles':changes, **context,
                   'fullBaseManifestSHA256':sha_bytes(baseline_raw),'fullCandidateManifestSHA256':sha_bytes(candidate_raw),
                   'readmeSHA256':sha_bytes(payloads['README.txt'])}
    payloads['Manifests/MigrationOverlay94.json'] = (json.dumps(declaration,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    return payloads


def verify_zip(path, expected):
    with zipfile.ZipFile(path,'r') as archive:
        names = archive.namelist()
        need(len(names) == len(set(name.casefold() for name in names)) == len(expected) and set(names) == set(expected), 'Overlay94ExactUniqueArchiveMembersRequired')
        need(archive.testzip() is None, 'Overlay94ArchiveCRCFailure')
        result = []
        for info in archive.infolist():
            need(not info.is_dir() and not info.filename.startswith('/') and '\\' not in info.filename
                 and '..' not in PurePosixPath(info.filename).parts, 'Overlay94UnsafeArchiveMember')
            raw = archive.read(info.filename)
            need(raw == expected[info.filename] and sha_bytes(raw) == sha_bytes(expected[info.filename])
                 and info.file_size == len(raw), 'Overlay94ArchiveMemberSHAOrBytesMismatch')
            result.append({'path':info.filename,'sha256':sha_bytes(raw),'bytes':len(raw),'crc32':format(info.CRC,'08x')})
    return result


def write_zip(path, payloads):
    need(not Path(path).exists(), 'Overlay94FreshArchiveRequired')
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name, raw in sorted(payloads.items()): archive.writestr(name,raw)
    return verify_zip(path,payloads)


def export(archive_path, output):
    audit = audit_module()
    for path in (MAIN,CANDIDATE,PRIVATE,AUDIT,BASELINE,PREPARATION,archive_path,output): audit.reject_links(path)
    archive_path, output = Path(archive_path).resolve(), Path(output).resolve()
    need(archive_path.parent == PRIVATE.resolve() and archive_path.suffix == '.zip' and re.fullmatch(r'[A-Za-z0-9_-]+\.zip',archive_path.name)
         and not archive_path.exists(), 'Overlay94FreshPrivateHandoffZIPRequired')
    need(output.is_relative_to((EVIDENCE/'BuildHandoff').resolve()) and output != (EVIDENCE/'BuildHandoff').resolve()
         and not output.exists(), 'Overlay94FreshPublicBuildHandoffChildRequired')
    report, baseline, preparation = read(AUDIT), read(BASELINE), read(PREPARATION)
    need(report.get('candidate') == CANDIDATE.relative_to(ROOT).as_posix()
         and report.get('mainBaselineSHA256') == preparation.get('mainManifestSHA256') == sha(BASELINE)
         and report.get('preparationSHA256') == sha(PREPARATION), 'Overlay94ExactBoundAuditPreparationRequired')
    need(sha(BASELINE) == BASELINE_SHA and preparation.get('accepted93SummarySHA256') == report.get('accepted93SummarySHA256') == ACCEPTED93_SHA
         and sha(ROOT/'Verification/Evidence/Review93/Summary.json') == ACCEPTED93_SHA, 'Overlay94ExactAcceptedHistoricalBaseRequired')
    need(report.get('runnerSHA256') == sha(Path(audit.__file__)), 'Overlay94SourceAuditorChangedSinceReceipt')
    required_artifacts = {'MainSources_before.json','MainSources_after.json','CandidateSources.json','CandidateSources_after.json',
                          'FileChanges.json','ProtectedGroups.json','GuidAudit.json','BackendInputs.json','TextDiffIndex.json'}
    need(required_artifacts.issubset(report.get('reportFileSHA256',{})), 'Overlay94CompleteBoundAuditArtifactsRequired')
    for name, expected in report.get('reportFileSHA256',{}).items():
        need(Path(name).name == name and sha(AUDIT.parent/name) == expected, 'Overlay94BoundAuditArtifactChanged')
    audited_before, audited_after = read(AUDIT.parent/'MainSources_before.json'), read(AUDIT.parent/'MainSources_after.json')
    candidate = read(AUDIT.parent/'CandidateSources.json')
    need(audited_before == audited_after and audited_before['files'] == baseline['files']
         and candidate == read(AUDIT.parent/'CandidateSources_after.json'), 'Overlay94StableAuditedManifestsRequired')
    main_before, candidate_before = audit.inventory(MAIN,'Unity/'), audit.inventory(CANDIDATE)
    need(main_before['files'] == baseline['files'] and main_before['inputCount'] == 5407
         and candidate_before == candidate, 'Overlay94CurrentInputsDifferFromReviewedAudit')
    before = audit.without_unity_prefix(baseline['files']); changes = overlay_rows(before,candidate['files'])
    validate_report(report,baseline,candidate,preparation,changes)
    original_changes = read(AUDIT.parent/'FileChanges.json')
    need([{key:row[key] for key in ('path','kind','before','after')} for row in original_changes] == changes,
         'Overlay94ExactReviewedOverlayRowsRequired')
    version = (CANDIDATE/'ProjectSettings/ProjectVersion.txt').read_text('utf-8-sig')
    need(re.search(r'^m_EditorVersion: '+re.escape(VERSION)+r'\s*$',version,re.MULTILINE), 'Overlay94ExactTargetEditorRequired')
    context = {'sourceAudit':metadata(AUDIT),'sourceAuditConfigurationApproval':False,
               'sourceAuditMainManifest':metadata(AUDIT.parent/'MainSources_before.json'),
               'sourceAuditCandidateManifest':metadata(AUDIT.parent/'CandidateSources.json'),
               'migrationPreparation':metadata(PREPARATION),'exporterSHA256':sha(Path(__file__))}
    payloads = archive_payloads(CANDIDATE,changes,BASELINE.read_bytes(),(AUDIT.parent/'CandidateSources.json').read_bytes(),context,audit.reject_links)
    # No output is created until every input/content gate has passed.
    output.mkdir(parents=True,exist_ok=False); PRIVATE.mkdir(parents=True,exist_ok=True)
    receipt = {'schemaVersion':1,'status':'RUNNING_PRIVATE_MIGRATION_OVERLAY_EXPORT94','startedUtc':utc(),
               'scope':SCOPE,'exporterSHA256':sha(Path(__file__)),'sourceAudit':metadata(AUDIT),
               'privateArchivePath':archive_path.relative_to(ROOT).as_posix(),'baseCommit':COMMIT,'unity':VERSION}
    audit.write_new(output/'Authorization.json',receipt)
    try:
        members = write_zip(archive_path,payloads)
        need(audit.inventory(MAIN,'Unity/') == main_before and audit.inventory(CANDIDATE) == candidate_before,
             'Overlay94ProjectChangedDuringExport')
        need(sha(AUDIT) == context['sourceAudit']['sha256'] and sha(BASELINE) == sha_bytes(payloads['Manifests/BaseUnity5407.json'])
             and sha(PREPARATION) == context['migrationPreparation']['sha256']
             and sha(ROOT/'Verification/Evidence/Review93/Summary.json') == ACCEPTED93_SHA, 'Overlay94BoundEvidenceChangedDuringExport')
        audit.write_new(output/'ArchiveMembers.json',{'scope':'Verified names, CRC and full SHA256 for every private ZIP member; no extraction performed.','members':members})
        receipt.update(status='PASS_PRIVATE_MIGRATION_OVERLAY_EXPORT94_WITH_OPEN_BUILD_GATES',archive=metadata(archive_path),
                       archiveMemberCount=len(members),overlayFileCount=len(changes),
                       changedExistingMetadata=sum(row['kind']=='changed' and row['path'].endswith('.meta') for row in changes),
                       mainInputCount=5407,candidateInputCount=candidate['inputCount'],fullBeforeAfterManifestsIncluded=True,
                       allMemberCRCAndSHA256Verified=True,mainInputsUnchanged=True,candidateInputsUnchanged=True,
                       onlySourceOverlayAndManifests=True,fullProject=False,apk=False,androidBuildSucceeded=False,
                       memberInventory=metadata(output/'ArchiveMembers.json'))
    except Exception as error:
        receipt.update(status='FAIL_PRIVATE_MIGRATION_OVERLAY_EXPORT94',errorType=type(error).__name__,error=str(error),
                       retainedPartialArchive=archive_path.exists())
        raise
    finally:
        receipt['finishedUtc']=utc();audit.write_new(output/'Report.json',receipt)
        print(json.dumps({'status':receipt['status'],'report':(output/'Report.json').relative_to(ROOT).as_posix(),
                          'archiveSHA256':receipt.get('archive',{}).get('sha256'),'overlayFileCount':receipt.get('overlayFileCount')}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--archive',type=Path);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if not args.execute:
        print('Preparation only: root --execute is required to export. No extraction/application is implemented.');return 0
    need(os.name=='nt','Overlay94WindowsWorkspaceRequired')
    path=args.archive or PRIVATE/('MigrationOverlay94_'+uuid.uuid4().hex+'.zip')
    export(path,args.out);return 0


if __name__=='__main__':raise SystemExit(main())
