"""Package only the already approved Windows replay bundle; never rebuild it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import zipfile

APPROVAL_SHA256='cffc33acb67c7e8d3c7c77b5d9f52bcaeb37920a44975143c7cfa638021d8c43'
EXPECTED_FILES=176
EXPECTED_BYTES=71463004

class PackageError(Exception):
    pass

def need(condition,code):
    if not condition:
        raise PackageError(code)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def plain(path):
    for entry in reversed((path,*path.parents)):
        try:
            info=entry.lstat()
        except FileNotFoundError:
            continue
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,
             'linked_source_rejected')
        if stat.S_ISREG(info.st_mode):
            need(info.st_nlink==1,'hardlinked_source_rejected')

def unique(pairs):
    result={}
    for name,value in pairs:
        need(name not in result,'duplicate_json_key')
        result[name]=value
    return result

def parse(raw):
    return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique)

def inventory(bundle):
    plain(bundle)
    need(bundle.is_dir(),'worker_directory_required')
    files={}
    def walk(directory):
        for entry in sorted(os.scandir(directory),key=lambda item:item.name):
            path=Path(entry.path)
            plain(path)
            info=entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                walk(path)
            else:
                need(stat.S_ISREG(info.st_mode),'nonregular_source_rejected')
                files[path.relative_to(bundle).as_posix()]=path
    walk(bundle)
    return files

def collect(bundle,approval):
    plain(approval)
    raw=approval.read_bytes()
    need(sha(raw)==APPROVAL_SHA256,'approved_receipt_hash_mismatch')
    approved=parse(raw)
    need(set(approved)=={'version','kind','unity','executable','pins','files'}
         and approved['version']==1 and approved['kind']=='PinnedUnityReplayWorker'
         and approved['unity']=='2022.3.62f3' and approved['executable']=='PinnedReplayWorker.exe'
         and approved['pins']=='ReplayPins/manifest.json','approved_receipt_shape_mismatch')
    actual=inventory(bundle)
    need(len(actual)==EXPECTED_FILES and set(actual)==set(approved['files']),'worker_inventory_mismatch')
    entries={}
    total=0
    for relative,path in actual.items():
        need(re.fullmatch(r'[A-Za-z0-9_./ -]+',relative)
             and all(part not in ('','.','..') for part in relative.split('/')),'worker_path_invalid')
        raw_file=path.read_bytes()
        need(sha(raw_file)==approved['files'][relative],'worker_file_hash_mismatch')
        entries['Worker/'+relative]={'sha256':sha(raw_file),'bytes':len(raw_file)}
        total+=len(raw_file)
    need(total==EXPECTED_BYTES,'worker_size_mismatch')
    entries['Local_Approval.json']={'sha256':sha(raw),'bytes':len(raw)}
    return actual,raw,entries,total

def verify_archive(path,entries):
    need(path.is_file(),'archive_missing')
    with zipfile.ZipFile(path) as archive:
        infos=archive.infolist()
        names=[entry.filename for entry in infos]
        need(len(names)==len(set(names))==len(set(name.casefold() for name in names))==177
             and set(names)==set(entries),'archive_inventory_mismatch')
        for info in infos:
            need(not info.is_dir() and not info.flag_bits&1,'archive_entry_invalid')
            need(info.file_size==entries[info.filename]['bytes'],'archive_size_mismatch')
            with archive.open(info) as stream:
                raw=stream.read(info.file_size+1)
                need(len(raw)==info.file_size and stream.read(1)==b'','archive_expanded_size_mismatch')
            need(sha(raw)==entries[info.filename]['sha256'],'archive_file_hash_mismatch')
    return sha(path.read_bytes())

def build(bundle,approval,destination):
    need(not os.path.lexists(destination) and destination.parent.is_dir(),'fresh_archive_destination_required')
    actual,approval_raw,entries,total=collect(bundle,approval)
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for relative,path in actual.items():
            raw=path.read_bytes()
            need(sha(raw)==entries['Worker/'+relative]['sha256'],'worker_changed_while_packaging')
            archive.writestr('Worker/'+relative,raw)
        archive.writestr('Local_Approval.json',approval_raw)
    archive_hash=verify_archive(destination,entries)
    # Exact inventories/content are checked again; source is never rewritten.
    _,after_approval,after_entries,after_total=collect(bundle,approval)
    need(approval_raw==after_approval and entries==after_entries and total==after_total,
         'source_changed_while_packaging')
    return {'status':'PASS_EXACT_APPROVED_WORKER_ARCHIVE126','approvalSHA256':APPROVAL_SHA256,
            'workerFiles':EXPECTED_FILES,'workerBytes':total,'archiveEntries':177,
            'archiveSHA256':archive_hash,'archiveBytes':destination.stat().st_size,
            'files':entries,'sourceUnchanged':True,'rebuilt':False,'pinsChanged':False,
            'qualifiedOnVps':False,'productionEnabled':False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--approval',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        need(not args.receipt.exists() and args.receipt.parent.is_dir(),'fresh_receipt_required')
        result=build(args.bundle.absolute(),args.approval.absolute(),args.out.absolute())
        args.receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({key:result[key] for key in ('status','workerFiles','workerBytes',
              'archiveEntries','archiveSHA256','archiveBytes','sourceUnchanged')}))
        return 0
    except (PackageError,OSError,ValueError,zipfile.BadZipFile):
        print(json.dumps({'status':'BLOCKED_APPROVED_WORKER_PACKAGE126'}))
        return 1

if __name__=='__main__':
    raise SystemExit(main())

