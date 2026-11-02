"""Commit an audited frozen index without checking out or resetting live files.

Default execution is a dry run. Only --execute invokes normal git commit, with
hooks and signing unchanged. A private index-only three-way merge carries the
latest ordinary staged intent from old HEAD onto the new commit. Conflicts,
special index flags or concurrent index replacement stop without overwriting it.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess


ROOT = Path(__file__).resolve().parents[3]
INITIAL_HEAD = '196f606d025ac1d8f51b0653bdd1e94245811860'
BRANCH = 'master'


class SafeStop(Exception):
    def __init__(self, code, paths=None):
        super().__init__(code)
        self.code, self.paths = code, paths or []


def need(condition, code, paths=None):
    if not condition:
        raise SafeStop(code, paths)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


class Repo:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.environment = dict(os.environ)
        for key in ('GIT_INDEX_FILE', 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR'):
            self.environment.pop(key, None)
        self.environment['GIT_OPTIONAL_LOCKS'] = '0'
        top = Path(self.git('rev-parse', '--show-toplevel').decode().strip()).resolve()
        need(top == self.root, 'ExactRepositoryRootRequired')
        self.gitdir = Path(self.git('rev-parse', '--absolute-git-dir').decode().strip())
        self.index = self.gitdir / 'index'

    def git(self, *arguments, index=None, data=None, allow_failure=False):
        env = dict(self.environment)
        if index is not None:
            env['GIT_INDEX_FILE'] = str(Path(index).resolve())
        result = subprocess.run(['git', '-c', 'core.longpaths=true', *arguments],
                                cwd=self.root, env=env, input=data, capture_output=True)
        if result.returncode and not allow_failure:
            raise SafeStop('GitOperationFailed_' + arguments[0])
        return result if allow_failure else result.stdout

    def head(self):
        return self.git('rev-parse', '--verify', 'HEAD').decode().strip()

    def branch(self):
        return self.git('symbolic-ref', '--quiet', '--short', 'HEAD').decode().strip()

    def entries(self, index):
        entries = {}
        for row in self.git('ls-files', '--stage', '-z', index=index).split(b'\0'):
            if not row:
                continue
            info, name = row.split(b'\t', 1)
            mode, oid, level = info.decode('ascii').split()
            need(level == '0', 'UnmergedIndexRequiresReview')
            entries[name.decode('utf-8', 'surrogateescape')] = (mode, oid)
        return entries

    def tree_entries(self, tree):
        entries = {}
        for row in self.git('ls-tree', '-r', '-z', tree).split(b'\0'):
            if row:
                info, name = row.split(b'\t', 1)
                mode, _, oid = info.decode('ascii').split()
                entries[name.decode('utf-8', 'surrogateescape')] = (mode, oid)
        return entries

    def simple_index(self, index):
        entries = self.entries(index)
        debug = self.git('ls-files', '--debug', '-z', index=index)
        flags = re.findall(rb'flags: ([0-9a-fA-F]+)', debug)
        need(len(flags) == len(entries) and all(int(value, 16) == 0 for value in flags),
             'SpecialIndexFlagsRequireReview')
        for setting in ('core.sparseCheckout', 'core.splitIndex'):
            result = self.git('config', '--bool', '--get', setting, allow_failure=True)
            need(result.returncode in (0, 1), 'IndexConfigurationUnreadable')
            need(result.stdout.strip() != b'true', 'SparseOrSplitIndexRequiresReview')

    def stable_copy(self, source, target):
        need(source.is_file() and not source.is_symlink(), 'RegularIndexFileRequired')
        before = source.read_bytes()
        need(not target.exists(), 'FreshPrivateIndexRequired')
        shutil.copy2(source, target)
        need(target.read_bytes() == before and source.read_bytes() == before,
             'IndexChangedDuringCapture')
        return sha(before)

    def reconciliation(self, old_head, new_tree, source_index, folder, label):
        """Prepare a trivial three-way index merge; never update working files."""
        backup = folder / (label + '.backup')
        captured_sha = self.stable_copy(source_index, backup)
        working = folder / (label + '.user.index')
        shutil.copy2(backup, working)
        self.simple_index(working)
        user_tree = self.git('write-tree', index=working).decode().strip()
        merged = folder / (label + '.synchronized.index')
        self.git('read-tree', '--no-recurse-submodules', new_tree, index=merged)
        result = self.git('read-tree', '-i', '-m', '--no-recurse-submodules',
                          old_head, new_tree, user_tree, index=merged,
                          allow_failure=True)
        unmerged = self.git('ls-files', '--unmerged', '-z', index=merged)
        conflicts = sorted({row.split(b'\t', 1)[1].decode('utf-8', 'surrogateescape')
                            for row in unmerged.split(b'\0') if row})
        need(result.returncode == 0 and not conflicts,
             'StagedOverlayConflictRequiresReview', conflicts)
        staged = self.git('diff', '--cached', '--name-only', '-z', old_head,
                          index=working).split(b'\0')
        return dict(capturedSHA256=captured_sha, backup=str(backup),
                    synchronizedIndex=str(merged), userTree=user_tree,
                    synchronizedTree=self.git('write-tree', index=merged).decode().strip(),
                    stagedIntentPaths=[p.decode('utf-8', 'surrogateescape') for p in staged if p])

    def install_ordinary_index(self, prepared, expected_head, expected_branch):
        """Install only under our O_EXCL lock and an unchanged-index checksum."""
        lock = self.index.with_name(self.index.name + '.lock')
        fd, identity = None, None
        try:
            try:
                fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                raise SafeStop('ForeignIndexLockPreserved') from None
            info = os.fstat(fd)
            identity = (info.st_dev, info.st_ino)
            need(self.head() == expected_head and self.branch() == expected_branch,
                 'HeadOrBranchChangedBeforeIndexInstall')
            need(sha(self.index.read_bytes()) == prepared['capturedSHA256'],
                 'OrdinaryIndexChangedSinceReconciliation')
            mode = stat.S_IMODE(self.index.stat().st_mode)
            with os.fdopen(fd, 'wb') as stream:
                fd = None
                stream.write(Path(prepared['synchronizedIndex']).read_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(lock, mode)
            current = lock.stat()
            need((current.st_dev, current.st_ino) == identity, 'OwnedIndexLockReplaced')
            need(sha(self.index.read_bytes()) == prepared['capturedSHA256'],
                 'OrdinaryIndexChangedBeforeAtomicReplace')
            need(self.head() == expected_head and self.branch() == expected_branch,
                 'HeadOrBranchChangedBeforeAtomicReplace')
            os.replace(lock, self.index)
            identity = None
            return sha(self.index.read_bytes())
        finally:
            if fd is not None:
                os.close(fd)
            if identity is not None and lock.exists():
                current = lock.stat()
                if (current.st_dev, current.st_ino) == identity:
                    lock.unlink()


def bounded_path(root, value):
    path = Path(value)
    path = path if path.is_absolute() else root / path
    need(not path.is_symlink(), 'RegularInputFileRequired')
    path = path.resolve()
    need(path.is_relative_to(root), 'RepositoryContainedInputRequired')
    need(path.is_file() and not path.is_symlink(), 'RegularInputFileRequired')
    return path


def dotted(value, key):
    for part in key.split('.'):
        need(isinstance(value, dict) and part in value, 'RequiredReportFieldMissing')
        value = value[part]
    return value


def verify_inputs(repo, args, folder, expected_head):
    paths = {name: bounded_path(repo.root, getattr(args, name))
             for name in ('index', 'stage_manifest', 'audit_manifest', 'checks_manifest', 'message_file')}
    need(paths['index'] != repo.index.resolve(), 'AlternateIndexRequired')
    need(paths['index'].is_relative_to(repo.root / '.verification-cache/Review116/Git'),
         'OwnedAlternateIndexRequired')
    bound = {name: dict(path=path.relative_to(repo.root).as_posix(), sha256=sha(path.read_bytes()))
             for name, path in paths.items()}
    stage, audit, checks = [json.loads(paths[name].read_text('utf-8-sig'))
                            for name in ('stage_manifest', 'audit_manifest', 'checks_manifest')]
    need(stage['head'] == expected_head, 'StageHeadMismatch')
    need(stage['status'] == 'PREPARED_ALTERNATE_TESTED_SNAPSHOT_INDEX', 'FinalStageRequired')
    need(audit['status'] == 'PASS_ALTERNATE_INDEX_BYTE_AUDIT' and not audit['mismatches'],
         'PassingFinalByteAuditRequired')
    need(audit['stagedManifestSHA256'] == bound['stage_manifest']['sha256'],
         'AuditStageBindingMismatch')
    need(audit['whitespaceCheck'] == 'PASS_CR_AWARE', 'WhitespaceAuditRequired')
    need(checks['status'] == 'READY_FOR_TESTED_SNAPSHOT_COMMIT'
         and checks['allRequiredChecksPassed'] is True, 'RequiredExecutionChecksIncomplete')
    need(checks['expectedHead'] == expected_head and checks['expectedBranch'] == BRANCH,
         'FinalChecksHeadOrBranchMismatch')
    need(checks['stageManifestSHA256'] == bound['stage_manifest']['sha256']
         and checks['auditManifestSHA256'] == bound['audit_manifest']['sha256'],
         'FinalCheckManifestBindingMismatch')
    need(checks['expectedIndexSHA256'] == stage['indexSHA256'] == bound['index']['sha256'],
         'AuditedIndexChecksumMismatch')
    need(isinstance(checks['reports'], list) and checks['reports'], 'ExplicitExecutionReportsRequired')
    for item in checks['reports']:
        path = bounded_path(repo.root, item['path'])
        need(sha(path.read_bytes()) == item['sha256'], 'RequiredExecutionReportChanged')
        data = json.loads(path.read_text('utf-8-sig'))
        need(isinstance(item['assertions'], dict) and item['assertions'], 'ExplicitReportAssertionsRequired')
        for key, expected in item['assertions'].items():
            actual = dotted(data, key)
            need(type(actual) is type(expected) and actual == expected,
                 'RequiredExecutionReportAssertionFailed', [item['path']])
    frozen = folder / 'commit.index'
    need(repo.stable_copy(paths['index'], frozen) == checks['expectedIndexSHA256'],
         'AlternateIndexChangedBeforeFreeze')
    repo.simple_index(frozen)
    actual = repo.entries(frozen)
    expected = repo.tree_entries(expected_head)
    expected.update({name: (row['mode'], row['gitBlob']) for name, row in stage['files'].items()})
    need(actual == expected, 'ExactAuditedIndexTreeEntriesRequired')
    need(audit['selectedFileCount'] == len(stage['files']) and audit['totalIndexEntries'] == len(actual),
         'AuditEntryCountsMismatch')
    tree = repo.git('write-tree', index=frozen).decode().strip()
    if 'expectedTree' in checks:
        need(tree == checks['expectedTree'], 'ExpectedTreeMismatch')
    message = paths['message_file'].read_bytes()
    need(0 < len(message) <= 65536 and message.strip(), 'BoundedCommitMessageRequired')
    (folder / 'message.txt').write_bytes(message)
    return paths, bound, checks, frozen, tree


def run(args, root=ROOT, expected_head=INITIAL_HEAD):
    need(re.fullmatch(r'[A-Za-z0-9_-]{1,40}', args.tag) is not None, 'FreshSafeTagRequired')
    root = Path(root).resolve()
    folder = root / '.verification-cache/Review116/Git/CommitRuns' / args.tag
    receipt = root / 'Verification/Evidence/Review116/Repository' / ('CommitRun_' + args.tag + '.json')
    need(not folder.exists() and not receipt.exists(), 'FreshCommitRunRequired')
    folder.mkdir(parents=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    result = dict(schemaVersion=1, status='PREPARING', startedUtc=utc(), execute=args.execute,
                  commitInvoked=False, committed=False, ordinaryIndexReplaced=False,
                  privateDirectory=folder.relative_to(root).as_posix(),
                  workingFilesWrittenByHelper=False, hooksAndSigningBypassed=False)
    save(receipt, result)
    repo = None
    try:
        repo = Repo(root)
        need(repo.head() == expected_head and repo.branch() == BRANCH, 'HeadOrBranchConflictReviewRequired')
        need(repo.index.is_file() and not repo.index.is_symlink(), 'OrdinaryIndexRequired')
        need(not repo.index.with_name('index.lock').exists(), 'ForeignIndexLockPreserved')
        for marker in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply', 'sequencer'):
            need(not (repo.gitdir / marker).exists(), 'ActiveGitOperationRequiresReview')
        result.update(oldHead=expected_head, branch=BRANCH,
                      ordinaryIndexSHA256Before=sha(repo.index.read_bytes()))
        paths, bound, checks, frozen, tree = verify_inputs(repo, args, folder, expected_head)
        result.update(inputs=bound, expectedTree=tree, frozenCommitIndex=str(frozen.relative_to(root)),
                      requiredExecutionReportCount=len(checks['reports']))
        result['preCommitReconciliation'] = repo.reconciliation(expected_head, tree, repo.index, folder, 'before')
        need(tree != repo.git('rev-parse', expected_head + '^{tree}').decode().strip(), 'SnapshotHasNoChanges')
        if not args.execute:
            result['status'] = 'DRY_RUN_READY_TESTED_SNAPSHOT_COMMIT'
            return 0
        need(repo.head() == expected_head and repo.branch() == BRANCH, 'HeadOrBranchChangedBeforeCommit')
        for name, path in paths.items():
            need(sha(path.read_bytes()) == bound[name]['sha256'], 'CommitInputChangedAfterValidation')
        need(not repo.index.with_name('index.lock').exists(), 'ForeignIndexLockPreserved')
        result['commitInvoked'] = True
        save(receipt, result)
        completed = repo.git('commit', '--file', str(folder / 'message.txt'), index=frozen,
                             allow_failure=True)
        (folder / 'CommitConsole.log').write_bytes(completed.stdout + completed.stderr)
        result['gitCommitExitCode'] = completed.returncode
        new_head = repo.head()
        result.update(newHead=new_head, committed=new_head != expected_head)
        if completed.returncode:
            raise SafeStop('CommitFailedHeadUnchanged' if new_head == expected_head
                           else 'CommitReturnedFailureButHeadChangedRequiresReview')
        need(new_head != expected_head and repo.branch() == BRANCH, 'CommitHeadOrBranchRequiresReview')
        result['committedTree'] = repo.git('rev-parse', new_head + '^{tree}').decode().strip()
        parents = repo.git('rev-list', '--parents', '-n', '1', new_head).decode().split()[1:]
        need(result['committedTree'] == tree and parents == [expected_head],
             'CommitTreeOrParentChangedRequiresReview')
        # Capture again: a user may have staged or unstaged while hooks/signing ran.
        prepared = repo.reconciliation(expected_head, tree, repo.index, folder, 'after')
        result['postCommitReconciliation'] = prepared
        result['ordinaryIndexChangedDuringCommit'] = (
            prepared['capturedSHA256'] != result['preCommitReconciliation']['capturedSHA256'])
        result['ordinaryIndexSHA256After'] = repo.install_ordinary_index(prepared, new_head, BRANCH)
        result.update(ordinaryIndexReplaced=True, stagedIntentPreserved=True,
                      status='COMPLETED_TESTED_SNAPSHOT_COMMIT')
        status = repo.git('status', '--porcelain=v1', '-z', '--untracked-files=all')
        parts, records, offset = status.split(b'\0'), [], 0
        while offset < len(parts):
            item = parts[offset]
            offset += 1
            if not item:
                continue
            code, name = item[:2].decode('ascii'), item[3:].decode('utf-8', 'surrogateescape')
            records.append(dict(status=code, path=name))
            if 'R' in code or 'C' in code:
                offset += 1
        result['remainingWorkingPaths'] = records
        result['newerWorkingSourcePaths'] = [row for row in records if not row['path'].startswith('Verification/Evidence/')]
        return 0
    except SafeStop as error:
        result.update(status='COMMIT_CREATED_REQUIRES_REVIEW' if result['committed'] else 'BLOCKED_BEFORE_COMMIT',
                      failureCode=error.code, conflictPaths=error.paths,
                      requiresManualIndexReconciliation=result['committed'] and not result['ordinaryIndexReplaced'])
        return 2
    except Exception as error:
        result.update(status='COMMIT_CREATED_REQUIRES_REVIEW' if result['committed'] else 'BLOCKED_WITH_FAILURE_RECEIPT',
                      failureCode='Unexpected_' + type(error).__name__,
                      requiresManualIndexReconciliation=result['committed'] and not result['ordinaryIndexReplaced'])
        return 2
    finally:
        result['finishedUtc'] = utc()
        if repo is not None:
            try:
                result['observedFinalHead'] = repo.head()
                result['observedFinalBranch'] = repo.branch()
                result['ordinaryIndexSHA256ObservedFinal'] = sha(repo.index.read_bytes())
                if result['commitInvoked'] and result['observedFinalHead'] != expected_head:
                    result['committed'] = True
                    result.setdefault('newHead', result['observedFinalHead'])
                    if not result['ordinaryIndexReplaced']:
                        result.update(status='COMMIT_CREATED_REQUIRES_REVIEW',
                                      requiresManualIndexReconciliation=True)
            except Exception:
                result['finalObservationUnavailable'] = True
        result['retainedOrdinaryIndexBackups'] = [
            dict(path=path.relative_to(root).as_posix(), sha256=sha(path.read_bytes()))
            for path in sorted(folder.glob('*.backup'))]
        save(receipt, result)
        print(json.dumps(dict(status=result['status'], committed=result['committed'],
                              commit=result.get('newHead'), tree=result.get('committedTree', result.get('expectedTree')),
                              receipt=receipt.relative_to(root).as_posix(), failureCode=result.get('failureCode'))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=Path('.verification-cache/Review116/Git/tested.index'))
    parser.add_argument('--stage-manifest', type=Path, required=True)
    parser.add_argument('--audit-manifest', type=Path, required=True)
    parser.add_argument('--checks-manifest', type=Path, required=True)
    parser.add_argument('--message-file', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
