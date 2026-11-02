"""Publish separate LTS log derivatives only after root confirms writers ended.

Imports the pinned94 pure redactor without changing it or its global scope.
Original logs and old receipts remain untouched. No native/SDK/device operation.
"""
import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import uuid

ROOT=Path(__file__).resolve().parents[3]
REDACTOR_PATH=ROOT/'Verification/Tools/Unity6Migration94/sanitize_logs94.py'
REDACTOR_SHA='364b9e460da7129f166e4a4a9034773d22204142605ab1adb099f868c54e592b'
MAX_LOG_BYTES=128*1024*1024
MAX_SET_BYTES=512*1024*1024
NAMES={'unity.log','console.log'}


def need(condition,code):
    if not condition:raise RuntimeError(code)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def reject_links(path):
    path=Path(os.path.abspath(path))
    for item in (path,*path.parents):
        if item.exists() or item.is_symlink():
            info=item.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,
                 'Privacy97LinkedPathRefused')


@dataclass(frozen=True)
class LogScope:
    """Explicit new scope; temporary host fixtures supply their own real paths."""
    anchor:Path
    evidence:Path
    public:Path
    private:Path

    def validated(self):
        for path in (self.anchor,self.evidence,self.public,self.private):reject_links(path)
        anchor=self.anchor.resolve()
        need(self.evidence.resolve()==anchor/'Verification/Evidence/Unity6LTS95'
             and self.public.resolve()==self.evidence.resolve()/'Privacy97'
             and self.private.resolve()==anchor/'.verification-cache/Unity6LTS95/PrivateEvidence97',
             'Privacy97ExactExplicitLTSScopeRequired')
        need(self.evidence.is_dir(),'Privacy97LTSEvidenceRootRequired')
        return self


DEFAULT_SCOPE=LogScope(ROOT,ROOT/'Verification/Evidence/Unity6LTS95',
                      ROOT/'Verification/Evidence/Unity6LTS95/Privacy97',
                      ROOT/'.verification-cache/Unity6LTS95/PrivateEvidence97')


def load_redactor():
    reject_links(REDACTOR_PATH)
    need(sha(REDACTOR_PATH.read_bytes())==REDACTOR_SHA,'Privacy97Frozen94RedactorChanged')
    spec=importlib.util.spec_from_file_location('privacy97_frozen94_pure_redactor',REDACTOR_PATH)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    # Only this unchanged pure function is used. Never call94.publish, change
    # its constants/workspace, or disguise the LTS files as94 evidence.
    return module.redact


def source_logs(scope):
    scope.validated();found=[];seen=set()
    for directory,folders,files in os.walk(scope.evidence,followlinks=False):
        directory=Path(directory);reject_links(directory);folders.sort()
        for name in folders:reject_links(directory/name)
        for name in sorted(files):
            if name.casefold() not in NAMES:continue
            path=directory/name;reject_links(path)
            need(path.is_file(),'Privacy97RegularRawLogRequired')
            key=path.relative_to(scope.evidence).as_posix().casefold()
            need(key not in seen,'Privacy97CaseCollidingRawLogsRefused')
            seen.add(key);found.append(path)
    return sorted(found,key=lambda path:path.relative_to(scope.evidence).as_posix().casefold())


def read_raw(path):
    reject_links(path);before=path.stat()
    need(before.st_size<=MAX_LOG_BYTES,'Privacy97RawLogSizeBoundExceeded')
    with path.open('rb') as stream:raw=stream.read(MAX_LOG_BYTES+1)
    after=path.stat()
    need(len(raw)<=MAX_LOG_BYTES and len(raw)==before.st_size
         and (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),
         'Privacy97RawLogChangedDuringRead')
    return raw


def fresh_paths(output,scope,private_id):
    scope.validated();output=Path(output);reject_links(output)
    output=output.resolve()
    need(output.parent==scope.public.resolve()
         and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}',output.name) is not None,
         'Privacy97FreshDirectPublicSetRequired')
    need(not output.exists(),'Privacy97FreshPublicOutputRequired')
    need(re.fullmatch('[a-f0-9]{32}',private_id) is not None,'Privacy97ValidPrivateSetIdentifierRequired')
    private=scope.private/private_id;reject_links(private)
    need(not private.exists(),'Privacy97FreshPrivateOutputRequired')
    return output,private


def write_new(path,raw,readonly=False):
    reject_links(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(raw)
    if readonly:os.chmod(path,stat.S_IREAD)


def public_error(error):
    value={'errorType':type(error).__name__}
    if isinstance(error,RuntimeError) and re.fullmatch('[A-Za-z0-9]{1,120}',str(error)):
        value['category']=str(error)
    return value


def relative(path,scope):
    path=Path(path).resolve();need(path.is_relative_to(scope.anchor.resolve()),'Privacy97ArtifactOutsideScopeAnchor')
    return path.relative_to(scope.anchor.resolve()).as_posix()


def bound_path(raw_path,scope,parent):
    path=scope.anchor/str(raw_path);reject_links(path);path=path.resolve()
    need(path.is_relative_to(parent.resolve()) and path!=parent.resolve(),'Privacy97BoundArtifactOutsideRoleScope')
    return path


def verify_receipt(receipt_path,*,scope=DEFAULT_SCOPE):
    scope.validated();reject_links(receipt_path);receipt_path=Path(receipt_path).resolve()
    need(receipt_path.name=='Receipt.json' and receipt_path.parent.parent==scope.public.resolve(),
         'Privacy97ScopedReceiptRequired')
    need(not (receipt_path.parent/'Failure.json').exists(),'Privacy97FailedPublicationPreserved')
    value=json.loads(receipt_path.read_text('utf-8'))
    need(value.get('status')=='PASS_HOST_LTS97_REDACTED_LOG_DERIVATIVES'
         and value.get('frozen94RedactorSHA256')==REDACTOR_SHA
         and value.get('runnerSHA256')==sha(Path(__file__).read_bytes())
         and value.get('writersFinishedAcknowledged') is True,'Privacy97CompletedBoundReceiptRequired')
    private_root=bound_path(value['privateRoot'],scope,scope.private)
    need(private_root.parent==scope.private.resolve() and re.fullmatch('[a-f0-9]{32}',private_root.name) is not None,
         'Privacy97ExactPrivateSetRequired')
    redact=load_redactor();expected_paths=[]
    for entry in value['files']:
        raw=bound_path(entry['rawSource'],scope,scope.evidence)
        private=bound_path(entry['privateCopy'],scope,scope.private)
        public=bound_path(entry['publicDerivative'],scope,receipt_path.parent/'Public')
        need(raw.name.casefold() in NAMES and public.name.endswith('.sanitized.log')
             and raw!=private and raw!=public and private!=public,'Privacy97RawAndDerivativeRolesMustRemainSeparate')
        raw_relative=raw.relative_to(scope.evidence.resolve())
        need(private==private_root/'Logs'/raw_relative
             and public==receipt_path.parent/'Public'/raw_relative.parent/(raw_relative.stem+'.sanitized.log'),
             'Privacy97ExactPerLogDerivativeAndPrivatePathsRequired')
        need(private.stat().st_size==entry['rawBytes'] and public.stat().st_size==entry['publicBytes'],
             'Privacy97BoundArtifactSizeChanged')
        body=read_raw(raw);private_body=private.read_bytes();derivative=public.read_bytes()
        need(body==private_body and sha(body)==entry['rawSHA256']==entry['privateSHA256']
             and len(body)==entry['rawBytes'] and sha(derivative)==entry['publicSHA256']
             and len(derivative)==entry['publicBytes'],'Privacy97BoundRawPrivateOrDerivativeChanged')
        need(not private.stat().st_mode&stat.S_IWRITE,'Privacy97PrivateRawCopyMustRemainReadOnly')
        expected,changes=redact(body)
        need(derivative==expected and changes==entry['redactions']
             and entry['categoryCounts']==dict(Counter(row['category'] for row in changes)),
             'Privacy97DerivativeTransformationMismatch')
        expected_paths.append(raw)
    need(len(expected_paths)==len(set(expected_paths))==value['rawLogCount']
         and source_logs(scope)==expected_paths
         and value['redactedLogCount']==sum(bool(entry['redactions']) for entry in value['files'])
         and value.get('errors')==[],'Privacy97RawLogSetChangedAfterPublication')
    return value


def publish(output,*,writers_finished=False,scope=DEFAULT_SCOPE,private_id=None):
    need(writers_finished is True,'Privacy97RootWriterCompletionAcknowledgementRequired')
    private_id=private_id or uuid.uuid4().hex
    output,private=fresh_paths(output,scope,private_id)
    redact=load_redactor();logs=source_logs(scope)
    need(logs,'Privacy97NoRawLTSLogs')
    prepared=[];total=0
    # Validate the complete set before creating any public/private output. A
    # secret shape outside the frozen redactor's supported policy refuses all.
    for source in logs:
        raw=read_raw(source);total+=len(raw)
        need(total<=MAX_SET_BYTES,'Privacy97WholeRawLogSetSizeBoundExceeded')
        derivative,changes=redact(raw);prepared.append((source,raw,derivative,changes))
    need(source_logs(scope)==logs and all(read_raw(source)==raw for source,raw,_,_ in prepared),
         'Privacy97RawLogSetChangedDuringPreparation')
    output.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
    entries=[]
    try:
        for source,raw,derivative,changes in prepared:
            need(read_raw(source)==raw,'Privacy97RawLogChangedDuringPublication')
            source_relative=source.relative_to(scope.evidence)
            private_copy=private/'Logs'/source_relative
            public_copy=output/'Public'/source_relative.parent/(source_relative.stem+'.sanitized.log')
            write_new(private_copy,raw,readonly=True);write_new(public_copy,derivative)
            need(private_copy.read_bytes()==raw and read_raw(source)==raw,
                 'Privacy97RawLogPreservationFailed')
            expected,repeated=redact(raw)
            need(public_copy.read_bytes()==expected and repeated==changes,'Privacy97DerivativeTransformationMismatch')
            entries.append({'rawSource':relative(source,scope),'rawSHA256':sha(raw),'rawBytes':len(raw),
                            'privateCopy':relative(private_copy,scope),'privateSHA256':sha(private_copy.read_bytes()),
                            'publicDerivative':relative(public_copy,scope),'publicSHA256':sha(derivative),'publicBytes':len(derivative),
                            'redactions':changes,'categoryCounts':dict(Counter(row['category'] for row in changes)),
                            'changedLineCount':len({row['line'] for row in changes})})
        need(source_logs(scope)==logs and all(read_raw(source)==raw for source,raw,_,_ in prepared),
             'Privacy97RawLogSetChangedDuringPublication')
        need(sha(REDACTOR_PATH.read_bytes())==REDACTOR_SHA,'Privacy97Frozen94RedactorChangedAtExit')
        receipt={'schemaVersion':1,'status':'PASS_HOST_LTS97_REDACTED_LOG_DERIVATIVES',
                 'completedUtc':datetime.now(timezone.utc).isoformat(),'runnerSHA256':sha(Path(__file__).read_bytes()),
                 'frozen94Redactor':'Verification/Tools/Unity6Migration94/sanitize_logs94.py',
                 'frozen94RedactorSHA256':REDACTOR_SHA,'writersFinishedAcknowledged':True,
                 'writerProcessAbsenceIndependentlyProven':False,
                 'rawLogCount':len(entries),'redactedLogCount':sum(bool(row['redactions']) for row in entries),
                 'privateRoot':relative(private,scope),'files':entries,'errors':[],
                 'scope':'Host privacy publication of separate sanitized derivatives only. Root explicitly acknowledged all native writers finished. '
                         'Original LTS Unity.log/Console.log bytes and old94/95 receipts are unchanged; private raw copies are read-only and hash-bound. '
                         'Frozen94 pure redaction policy is reused exactly. No native/build/SDK/device acceptance or universal secret-detection claim. '
                         'New or changed raw logs require a fresh set.'}
        write_new(output/'Receipt.json',(json.dumps(receipt,indent=2)+'\n').encode('utf-8'))
        verify_receipt(output/'Receipt.json',scope=scope)
        return receipt
    except Exception as error:
        failure={'status':'FAIL_HOST_LTS97_LOG_DERIVATIVES','completedUtc':datetime.now(timezone.utc).isoformat(),
                 **public_error(error),'partialNewOutputsPreserved':True,'completedFiles':len(entries),
                 'scope':'No original raw log or old receipt was rewritten or removed. Partial new derivatives are not accepted.'}
        write_new(output/'Failure.json',(json.dumps(failure,indent=2)+'\n').encode('utf-8'))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--writers-finished',action='store_true');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not args.execute or not args.writers_finished or not args.out.is_absolute():
        parser.error('Explicit --execute --writers-finished and fresh absolute LTS Privacy97 output required')
    try:
        value=publish(args.out,writers_finished=True)
        print(json.dumps({key:value[key] for key in ('status','rawLogCount','redactedLogCount')}));return 0
    except Exception as error:
        print(json.dumps({'status':'FAIL_HOST_LTS97_LOG_DERIVATIVES',**public_error(error)}));return 1


if __name__=='__main__':raise SystemExit(main())
