"""Bounded read-only log observation of the exact newly installed app PID."""
import json,re
from pathlib import Path
from phone109 import Phone109,ROOT,PACKAGE,base
def main():
 out=ROOT/'Verification/Evidence/Review109/Physical/RuntimeLog01';out.mkdir(parents=True,exist_ok=False)
 build=ROOT/'Verification/Evidence/Review109/Native/AndroidBuildLts01/BuildDevelopment109.json';phone=Phone109(out,build);phone.identity();before=phone.installed();pid=phone.adb('shell','pidof',PACKAGE,check=False)
 if not re.fullmatch('[0-9]+',pid):raise ValueError('ExactRunningCurrentAppPidRequired109')
 text=phone.adb('logcat','-d','--pid='+pid,'-v','threadtime','-t','4000',timeout=30);raw=phone.private/'RuntimeLogcat.txt';raw.write_text(text,encoding='utf-8')
 terms=['FATAL EXCEPTION','NullReferenceException','MissingReferenceException','AndroidJavaException','DllNotFoundException','TypeLoadException','ClassNotFoundException','Failed to create texture','Failed to compile shader']
 matches={term:sum(term.lower() in line.lower() for line in text.splitlines()) for term in terms};after=phone.installed()
 result=dict(status='PASS_BOUNDED_CURRENT_APP_LOG_OBSERVATION109' if not any(matches.values()) and before==after else 'REQUIRES_REVIEW_BOUNDED_APP_LOG109',installedSHA256=before['installedSHA256'],selectedErrorSignatureCounts=matches,logLineCount=len(text.splitlines()),rawLog=base.bound(raw),profilePreferencesUnchanged=before==after,candidateAfter=after,scope='Read-only bounded current installed app-PID log snapshot after ordinary Home/Teams navigation. Zero selected signatures is not proof of all errors, no provider traffic, performance, gameplay or whole-device certification.')
 base.save(out/'Report.json',result);print(json.dumps(dict(status=result['status'],selectedErrorCount=sum(matches.values()),logLines=result['logLineCount'])))
if __name__=='__main__':main()
