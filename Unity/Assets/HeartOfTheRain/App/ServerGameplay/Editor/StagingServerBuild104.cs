#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.App.ServerGameplay.Editor {
    // Staging packaging only. A marker left by an interrupted process never
    // authorizes an ordinary build: the additional lease exists only in memory.
    public static class StagingServerBuild104 {
        public const string ConfigVariable="HOTR_STAGING104_CONFIG", IsolationVariable="HOTR_STAGING104_ISOLATION";
        public const string LeaseFile=".hotr-staging104-lease.json";
        static OwnedFiles active;
        [Serializable] public sealed class IsolationReceipt {
            public int version; public string status,sourceRoot,project,nonce,configSHA256,unity;
            public string[] copiedPaths,copiedSHA256;
        }
        [Serializable] public sealed class BuildOutcome {
            public string status="BLOCKED_STAGING104",code,unity,configSHA256,output;
            public bool built,cleaned,settingsRestored,delegateInvoked,buildInvoked,buildSucceeded,artifactExists,cleanupAttempted,settingsRestoreAttempted,exceptionObserved;
            public long artifactBytes;
            public int errors=-1,warnings=-1;
        }
        [Serializable] sealed class Ownership {public int version=1,ownerPid;public string nonce,payloadSHA256,assetMetaSHA256,folderMetaSHA256;}
        static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
        static string Full(string p)=>Path.GetFullPath(p).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar);
        static bool Under(string path,string parent)=>Full(path).StartsWith(Full(parent)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase);
        static string Sha(byte[] value){using(var h=SHA256.Create())return string.Concat(h.ComputeHash(value).Select(b=>b.ToString("x2")));}
        static string ReadSmall(string path){var f=new FileInfo(path);if(!f.Exists||f.Length<2||f.Length>8192)throw new InvalidOperationException("StagingConfigurationMissingOrOversized");return File.ReadAllText(path,Utf8);}
        static string Canonical(string json){ServerGameplayConfiguration c;string why;if(!ServerStagingConfiguration104.TryParsePackaged(json,out c,out why))throw new InvalidOperationException("StagingConfigurationInvalid");return ServerStagingConfiguration104.CanonicalJson(c);}
        static void PlainPath(string path){for(var d=new DirectoryInfo(Path.GetDirectoryName(Full(path)));d!=null;d=d.Parent)if(d.Exists&&(d.Attributes&FileAttributes.ReparsePoint)!=0)throw new InvalidOperationException("LinkedStagingPathRejected");if(File.Exists(path)&&(File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0)throw new InvalidOperationException("LinkedStagingPathRejected");}
        static IsolationReceipt Receipt(string path,string canonical){
            if(string.IsNullOrEmpty(path))throw new InvalidOperationException("IsolationReceiptRequired");
            PlainPath(path);if(new FileInfo(path).Length>4*1024*1024)throw new InvalidOperationException("IsolationReceiptInvalid");
            var r=JsonUtility.FromJson<IsolationReceipt>(File.ReadAllText(path,Utf8));string project=Full("."),source=r==null?"":r.sourceRoot;
            if(r==null||r.version!=1||r.status!="PREPARED_STAGING104"||r.unity!="2022.3.62f3"||Application.unityVersion!=r.unity||
               string.IsNullOrEmpty(source)||!Directory.Exists(Path.Combine(source,"Unity"))||!File.Exists(Path.Combine(source,"AGENTS.md"))||
               Full(r.project)!=project||!Under(project,Path.Combine(source,".verification-cache","Review104","Candidates"))||
               Full(path)!=Full(Path.Combine(Directory.GetParent(project).FullName,"Preparation.json"))||
               r.configSHA256!=Sha(Utf8.GetBytes(canonical))||!System.Text.RegularExpressions.Regex.IsMatch(r.nonce??"",@"\A[0-9a-f]{32}\z")||
               r.copiedPaths==null||r.copiedSHA256==null||r.copiedPaths.Length==0||r.copiedPaths.Length!=r.copiedSHA256.Length)
                throw new InvalidOperationException("IsolationReceiptInvalid");
            var seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            for(int i=0;i<r.copiedPaths.Length;i++){
                string relative=r.copiedPaths[i],target=Full(Path.Combine(project,relative??""));
                if(!seen.Add(relative??"")||!Under(target,project)||!(relative.StartsWith("Assets/",StringComparison.Ordinal)||relative.StartsWith("Packages/",StringComparison.Ordinal)||relative.StartsWith("ProjectSettings/",StringComparison.Ordinal)))throw new InvalidOperationException("IsolationReceiptInvalid");
                PlainPath(target);if(!File.Exists(target)||Sha(File.ReadAllBytes(target))!=r.copiedSHA256[i])throw new InvalidOperationException("IsolatedSourceChanged");
            }
            return r;
        }
        public static string[] Preflight(string json,string isolationReceipt){
            try{string canonical=Canonical(json);Receipt(isolationReceipt,canonical);if(File.Exists(LeaseFile)||Directory.Exists(Path.GetDirectoryName(ServerStagingConfiguration104.ResourceAssetPath))||File.Exists(Path.GetDirectoryName(ServerStagingConfiguration104.ResourceAssetPath)+".meta"))return new[]{"StaleOrForeignStagingResource"};return Array.Empty<string>();}
            catch(Exception e){return new[]{SafeCode(e)};}
        }
        static string SafeCode(Exception e){string s=e.Message;return new[]{"StagingConfigurationInvalid","StagingConfigurationMissingOrOversized","IsolationReceiptRequired","IsolationReceiptInvalid","IsolatedSourceChanged","LinkedStagingPathRejected","StagingAndroidTargetMustBeSelectedBeforeBuild","PreserveExistingStagingAttempt","StagingAndroidBuildFailed","StagingAndroidArtifactMissing","StagingBuildPreflightBlocked","StagingLeasePathOccupied","StagingResourcesParentMissing","StagingLeaseChangedDuringImport","StagingOwnershipChangedPreserved","ForeignStagingBytesPreserved","ForeignStagingFilesPreserved","StagingSettingsRestoreFailed"}.Contains(s)?s:"StagingBuildOperationFailed";}
        public static bool ReservedResourcePath(string path){
            if(string.IsNullOrEmpty(path)||path.EndsWith(".meta",StringComparison.OrdinalIgnoreCase))return false;
            string normalized=path.Replace('\\','/');int index=normalized.LastIndexOf("/Resources/",StringComparison.OrdinalIgnoreCase);if(index<0)return false;
            string key=normalized.Substring(index+11);if(key.StartsWith(ServerStagingConfiguration104.ResourceKey+"/",StringComparison.OrdinalIgnoreCase))return true;int dot=key.LastIndexOf('.');if(dot>=0)key=key.Substring(0,dot);
            return string.Equals(key,ServerStagingConfiguration104.ResourceKey,StringComparison.OrdinalIgnoreCase);
        }
        static string[] ReservedPaths()=>AssetDatabase.GetAllAssetPaths().Where(ReservedResourcePath).ToArray();
        public static string[] VerifyActiveBuildBoundaryForVerification(BuildTarget target,BuildOptions options){
            bool owns=active!=null&&active.Matches();return VerifyBuildBoundary(target,options,PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android),PlayerSettings.Android.useCustomKeystore,ReservedPaths(),owns,File.Exists(LeaseFile)&&!owns);
        }
        // Pure policy seam. The build guard derives ownership itself; callers
        // cannot create its private active lease by passing a test boolean.
        public static string[] VerifyBuildBoundary(BuildTarget target,BuildOptions options,string package,bool customSigning,string[] resourcePaths,bool ownedLease=false,bool staleMarker=false){
            var errors=new List<string>();var paths=(resourcePaths??Array.Empty<string>()).Where(ReservedResourcePath).ToArray();
            if(paths.Length==0&&!ownedLease&&!staleMarker&&package!=ServerStagingConfiguration104.PackageName)return errors.ToArray();
            if(paths.Length==0&&package==ServerStagingConfiguration104.PackageName)errors.Add("StagingConfiguredPayloadRequired");
            if(staleMarker||!ownedLease)errors.Add("UnownedOrStaleStagingPayload");
            if(paths.Length!=1||paths[0]!=ServerStagingConfiguration104.ResourceAssetPath)errors.Add("StagingResourceCollisionOrWrongType");
            if(target!=BuildTarget.Android)errors.Add("StagingAndroidOnly");
            if((options&BuildOptions.Development)==0)errors.Add("StagingDevelopmentBuildRequired");
            if(package!=ServerStagingConfiguration104.PackageName)errors.Add("StagingPackageMismatch");
            if(customSigning)errors.Add("StagingDebugSigningRequired");
            if(Environment.GetEnvironmentVariable("HOTR_BUILD_CHANNEL")=="rustore")errors.Add("StagingCannotUseRuStoreChannel");
            return errors.ToArray();
        }
        internal static void Guard(BuildReport report){
            if(SdkCheckoutBuild125.GuardIfSelected(report))return;
            if(HeartOfTheRain.App.Advertising.Editor.AdvertisingBuild107.GuardManagedBuild(report))return;
            bool owns=active!=null&&active.Matches();var errors=VerifyActiveBuildBoundaryForVerification(report.summary.platform,report.summary.options);
            if(errors.Length>0)throw new BuildFailedException(string.Join(",",errors));
            if(owns){ServerGameplayConfiguration c;string why;var imported=AssetDatabase.LoadMainAssetAtPath(ServerStagingConfiguration104.ResourceAssetPath) as TextAsset;
                if(!imported||!ServerStagingConfiguration104.TryParsePackaged(imported.text,out c,out why)||imported.text!=File.ReadAllText(ServerStagingConfiguration104.ResourceAssetPath,Utf8))throw new BuildFailedException("StagingPayloadInvalidOrWrongType");}
        }
        sealed class OwnedFiles : IDisposable {
            readonly string root,folder,asset,assetMeta,folderMeta,marker;readonly byte[] payload,am,fm,proof;bool cleaned,ownsMarker;
            public OwnedFiles(string project,string canonical,string nonce){
                root=Full(project);asset=Full(Path.Combine(root,ServerStagingConfiguration104.ResourceAssetPath));folder=Full(Path.GetDirectoryName(asset));assetMeta=Full(asset+".meta");folderMeta=Full(folder+".meta");marker=Full(Path.Combine(root,LeaseFile));
                payload=Utf8.GetBytes(canonical);am=Utf8.GetBytes("fileFormatVersion: 2\nguid: "+Guid.NewGuid().ToString("N")+"\nTextScriptImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n");
                fm=Utf8.GetBytes("fileFormatVersion: 2\nguid: "+Guid.NewGuid().ToString("N")+"\nfolderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n");
                proof=Utf8.GetBytes(JsonUtility.ToJson(new Ownership{nonce=nonce,ownerPid=System.Diagnostics.Process.GetCurrentProcess().Id,payloadSHA256=Sha(payload),assetMetaSHA256=Sha(am),folderMetaSHA256=Sha(fm)}));
            }
            static bool Equal(string path,byte[] expected)=>File.Exists(path)&&File.ReadAllBytes(path).SequenceEqual(expected);
            static void Exclusive(string path,byte[] bytes){using(var f=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None)){f.Write(bytes,0,bytes.Length);f.Flush(true);}}
            public void Create(Action import){
                foreach(var p in new[]{folder,folderMeta,asset,assetMeta,marker}){PlainPath(p);if(File.Exists(p)||Directory.Exists(p))throw new InvalidOperationException("StagingLeasePathOccupied");}
                if(!Directory.Exists(Path.GetDirectoryName(folder)))throw new InvalidOperationException("StagingResourcesParentMissing");
                Exclusive(marker,proof);ownsMarker=true;
                try{Directory.CreateDirectory(folder);Exclusive(folderMeta,fm);Exclusive(asset,payload);Exclusive(assetMeta,am);import?.Invoke();if(!Matches())throw new InvalidOperationException("StagingLeaseChangedDuringImport");}
                catch{Dispose();throw;}
            }
            public bool Matches()=>!cleaned&&Equal(marker,proof)&&Equal(asset,payload)&&Equal(assetMeta,am)&&Equal(folderMeta,fm);
            public void Dispose(){
                if(cleaned||!ownsMarker)return;if(!Equal(marker,proof))throw new InvalidOperationException("StagingOwnershipChangedPreserved");
                foreach(var pair in new[]{Tuple.Create(asset,payload),Tuple.Create(assetMeta,am),Tuple.Create(folderMeta,fm)})if(File.Exists(pair.Item1)&&!Equal(pair.Item1,pair.Item2))throw new InvalidOperationException("ForeignStagingBytesPreserved");
                if(Directory.Exists(folder)&&Directory.EnumerateFileSystemEntries(folder).Any(p=>!string.Equals(Full(p),asset,StringComparison.OrdinalIgnoreCase)&&!string.Equals(Full(p),assetMeta,StringComparison.OrdinalIgnoreCase)))throw new InvalidOperationException("ForeignStagingFilesPreserved");
                foreach(var p in new[]{asset,assetMeta})if(File.Exists(p))File.Delete(p);
                if(Directory.Exists(folder))Directory.Delete(folder,false);if(File.Exists(folderMeta))File.Delete(folderMeta);File.Delete(marker);cleaned=true;
            }
        }
        // Uses the identical on-disk lease primitive in a disposable path only.
        // Import/build delegates are synthetic; this never claims an APK build.
        public static void ExerciseFileLeaseForVerification(string disposableProject,string canonicalJson,Action import,Action build){
            string root=Full(disposableProject),workspace=Full("..");
            if(!Under(root,Path.Combine(workspace,".verification-cache","Review104"))||root==Full(".")||active!=null)throw new InvalidOperationException("DisposableStagingFixtureRequired");
            var lease=new OwnedFiles(root,Canonical(canonicalJson),Guid.NewGuid().ToString("N"));lease.Create(import);try{build?.Invoke();}finally{lease.Dispose();}
        }
        public static BuildOutcome RunWithBuildDelegate(string json,string isolationReceipt,Action build,Action<BuildOutcome> observeOutcome=null){
            string canonical=Canonical(json);var receipt=Receipt(isolationReceipt,canonical);if(active!=null||Preflight(json,isolationReceipt).Length!=0)throw new InvalidOperationException("StagingBuildPreflightBlocked");
            string app=PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android);bool signing=PlayerSettings.Android.useCustomKeystore,bundle=EditorUserBuildSettings.buildAppBundle,export=EditorUserBuildSettings.exportAsGoogleAndroidProject;
            var outcome=new BuildOutcome{unity=Application.unityVersion,configSHA256=Sha(Utf8.GetBytes(canonical))};var lease=new OwnedFiles(Full("."),canonical,receipt.nonce);
            try{
                PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,ServerStagingConfiguration104.PackageName);PlayerSettings.Android.useCustomKeystore=false;EditorUserBuildSettings.buildAppBundle=false;EditorUserBuildSettings.exportAsGoogleAndroidProject=false;
                lease.Create(()=>AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport));active=lease;outcome.delegateInvoked=true;build();outcome.status="PASS_STAGING104_BUILD_DELEGATE";
            }catch(Exception e){outcome.status="FAIL_STAGING104_BUILD_DELEGATE";outcome.code=SafeCode(e);outcome.exceptionObserved=true;throw;}
            finally{
                active=null;
                outcome.cleanupAttempted=true;
                try{lease.Dispose();outcome.cleaned=true;AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);}
                catch(Exception e){outcome.status="FAIL_STAGING104_CLEANUP";outcome.code=SafeCode(e);outcome.exceptionObserved=true;throw;}
                finally{
                    outcome.settingsRestoreAttempted=true;
                    try{PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,app);PlayerSettings.Android.useCustomKeystore=signing;EditorUserBuildSettings.buildAppBundle=bundle;EditorUserBuildSettings.exportAsGoogleAndroidProject=export;outcome.settingsRestored=PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android)==app&&PlayerSettings.Android.useCustomKeystore==signing&&EditorUserBuildSettings.buildAppBundle==bundle&&EditorUserBuildSettings.exportAsGoogleAndroidProject==export;if(!outcome.settingsRestored)throw new InvalidOperationException("StagingSettingsRestoreFailed");}
                    catch{outcome.status="FAIL_STAGING104_SETTINGS_RESTORE";outcome.code="StagingSettingsRestoreFailed";outcome.exceptionObserved=true;throw;}
                    finally{observeOutcome?.Invoke(outcome);}
                }
            }
            return outcome;
        }
        public static void Run(){
            BuildOutcome outcome=new BuildOutcome{unity=Application.unityVersion};string receiptPath=Environment.GetEnvironmentVariable(IsolationVariable),json=null,reportPath=null,output=null;BuildReport actual=null;bool invoked=false;
            try{
                if(EditorUserBuildSettings.activeBuildTarget!=BuildTarget.Android)throw new InvalidOperationException("StagingAndroidTargetMustBeSelectedBeforeBuild");
                json=ReadSmall(Environment.GetEnvironmentVariable(ConfigVariable));string canonical=Canonical(json);Receipt(receiptPath,canonical);
                reportPath=Path.Combine(Directory.GetParent(Full(".")).FullName,"Build.json");output=Path.Combine(Directory.GetParent(Full(".")).FullName,"Build","HeartOfTheRain_Staging104.apk");
                if(Directory.Exists(Path.GetDirectoryName(output))||File.Exists(reportPath))throw new InvalidOperationException("PreserveExistingStagingAttempt");
                outcome=RunWithBuildDelegate(json,receiptPath,()=>{
                    Directory.CreateDirectory(Path.GetDirectoryName(output));
                    invoked=true;
                    actual=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{HeartOfTheRain.App.Launch.LaunchPage.ScenePath,HeartOfTheRain.App.Launch.LaunchPage.GameScenePath},locationPathName=output,target=BuildTarget.Android,options=BuildOptions.Development});
                    if(actual.summary.result!=BuildResult.Succeeded)throw new InvalidOperationException("StagingAndroidBuildFailed");
                },observed=>outcome=observed);
                if(!File.Exists(output))throw new InvalidOperationException("StagingAndroidArtifactMissing");
                outcome.status="PASS_ANDROID_STAGING104_BUILD";
            }catch(Exception e){if(!outcome.status.StartsWith("FAIL",StringComparison.Ordinal))outcome.status=invoked?"FAIL_ANDROID_STAGING104_BUILD":"BLOCKED_STAGING104";if(outcome.code==null)outcome.code=SafeCode(e);outcome.exceptionObserved=true;}
            finally{
                outcome.buildInvoked=invoked;outcome.buildSucceeded=actual!=null&&actual.summary.result==BuildResult.Succeeded;
                if(actual!=null){outcome.errors=(int)actual.summary.totalErrors;outcome.warnings=(int)actual.summary.totalWarnings;}
                if(output!=null){outcome.output=output;outcome.artifactExists=File.Exists(output);if(outcome.artifactExists)outcome.artifactBytes=new FileInfo(output).Length;}
                outcome.built=outcome.buildSucceeded&&outcome.artifactExists;
            }
            if(reportPath!=null&&!File.Exists(reportPath))File.WriteAllText(reportPath,JsonUtility.ToJson(outcome,true),Utf8);
            if(Application.isBatchMode)EditorApplication.Exit(outcome.built&&outcome.cleaned&&outcome.settingsRestored?0:1);
        }
    }
    public sealed class StagingServerBuildGuard104:IPreprocessBuildWithReport {
        public int callbackOrder=>-20000;
        public void OnPreprocessBuild(BuildReport report)=>StagingServerBuild104.Guard(report);
    }
}
#endif
