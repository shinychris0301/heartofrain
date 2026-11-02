"""Actual local host containment check; no Unity, app, providers or user data."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

from run_connected import OwnedJob, ROOT, listener_closed, resume_owned_primary, sha, utc


def main():
    output = ROOT / 'Verification/Evidence/Review93/Environment/ConnectedJob.json'
    if output.exists():
        raise RuntimeError('ExistingHostObservationPreserved')
    private = ROOT / '.verification-cache/Review93/OwnedJob' / uuid.uuid4().hex
    private.mkdir(parents=True)
    metadata = private / 'connection.json'
    script = private / 'listener.py'
    script.write_text("import json,os,socket,time,sys\n"
                      "s=socket.socket();s.bind(('127.0.0.1',0));s.listen()\n"
                      "open(sys.argv[1],'w').write(json.dumps({'pid':os.getpid(),'origin':'http://127.0.0.1:'+str(s.getsockname()[1])}))\n"
                      "time.sleep(120)\n", encoding='utf-8')
    job, process, server_handle = OwnedJob(), None, None
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes, kernel.OpenProcess.restype = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes, kernel.WaitForSingleObject.restype = [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD
    kernel.CloseHandle.argtypes, kernel.CloseHandle.restype = [wintypes.HANDLE], wintypes.BOOL
    record = {'status': 'RUNNING', 'startedUtc': utc(), 'runnerSHA256': sha(Path(__file__)),
              'connectedHelperSHA256': sha(Path(__file__).with_name('run_connected.py')),
              'scope': 'Actual Windows venv launcher and local TCP child under an owned job; host containment only, not backend/Unity/device acceptance.'}
    try:
        process = subprocess.Popen([str(ROOT / 'Backend/.venv/Scripts/python.exe'), '-B', str(script), str(metadata)],
                                   creationflags=subprocess.CREATE_NO_WINDOW | 0x4,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        job.assign(process.pid)
        resume_owned_primary(process)
        deadline = time.monotonic() + 15
        while not metadata.exists() and time.monotonic() < deadline:
            time.sleep(.05)
        value = json.loads(metadata.read_text('utf-8'))
        if listener_closed(value['origin']):
            raise RuntimeError('OwnedChildListenerDidNotStart')
        server_handle = kernel.OpenProcess(0x100000, False, value['pid'])
        if not server_handle:
            raise RuntimeError('OwnedChildWaitHandleUnavailable')
        record.update(launcherPid=process.pid, actualServerPid=value['pid'],
                      venvRedirectorObserved=process.pid != value['pid'], assignedBeforeResume=True,
                      listenerOpened=True)
        job.close()
        process.wait(timeout=10)
        record.update(launcherStopped=process.poll() is not None,
                      actualServerStopped=kernel.WaitForSingleObject(server_handle, 10000) == 0,
                      listenerClosed=listener_closed(value['origin']))
        if not all(record[k] for k in ('launcherStopped', 'actualServerStopped', 'listenerClosed')):
            raise RuntimeError('OwnedJobDidNotContainActualServer')
        record['status'] = 'PASS_ACTUAL_HOST_CONNECTED_JOB93'
    finally:
        job.close()
        if process and process.poll() is None:
            process.wait(timeout=10)
        if server_handle:
            kernel.CloseHandle(server_handle)
        record['finishedUtc'] = utc()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
