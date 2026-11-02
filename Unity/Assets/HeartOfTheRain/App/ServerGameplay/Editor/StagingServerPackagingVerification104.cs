#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace HeartOfTheRain.App.ServerGameplay.Editor {
    // Runs only in the prepared separate Unity2022 project. The callback is a
    // test delegate, never BuildPipeline.BuildPlayer or a contacted backend.
    public static class StagingServerPackagingVerification104 {
        [Serializable] sealed class Report {
            public string status="FAIL_NATIVE_STAGING_PACKAGING104",unity,scope="Actual isolated Unity2022 AssetDatabase/TextAsset/Resources import and owned cleanup with synthetic success/throwing delegates. No APK, HTTP, provider, deployment or device operation.",error;
            public int checks;public bool successCleanup,exceptionCleanup,settingsRestored,ordinaryProfileUsed=false,actualBuildPipeline=false,networkContacted=false;
        }
        static Report report;
        static void Check(bool condition,string code){report.checks++;if(!condition)throw new InvalidOperationException(code);}
        static void Empty(){
            Check(!File.Exists(ServerStagingConfiguration104.ResourceAssetPath),"payload_cleanup");Check(!File.Exists(ServerStagingConfiguration104.ResourceAssetPath+".meta"),"asset_meta_cleanup");
            string folder=Path.GetDirectoryName(ServerStagingConfiguration104.ResourceAssetPath);Check(!Directory.Exists(folder),"folder_cleanup");Check(!File.Exists(folder+".meta"),"folder_meta_cleanup");Check(!File.Exists(StagingServerBuild104.LeaseFile),"marker_cleanup");
        }
        static void Imported(string expected){
            var loaded=Resources.Load<TextAsset>(ServerStagingConfiguration104.ResourceKey);
            try{
                Check(loaded!=null,"actual_resource_import");Check(loaded.text==expected,"canonical_resource_bytes");
                Check(AssetDatabase.GetAssetPath(loaded)==ServerStagingConfiguration104.ResourceAssetPath,"canonical_resource_path");
                string priorReviewPath=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG");
                try{
                    Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",null);
                    ServerGameplayConfiguration actual;string error;
                    Check(ServerGameplayConfiguration.TryRead(out actual,out error),"actual_runtime_resource_selection");
                    Check(actual!=null&&error==null&&ServerStagingConfiguration104.CanonicalJson(actual)==expected,"actual_runtime_resource_config");
                }finally{Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",priorReviewPath);}
                Check(StagingServerBuild104.VerifyActiveBuildBoundaryForVerification(BuildTarget.Android,BuildOptions.Development).Length==0,"active_boundary");
                Check(StagingServerBuild104.VerifyActiveBuildBoundaryForVerification(BuildTarget.Android,BuildOptions.None).Length>0,"release_boundary_rejected");
                Check(PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android)==ServerStagingConfiguration104.PackageName,"separate_package");Check(!PlayerSettings.Android.useCustomKeystore,"debug_signing");
            }finally{if(loaded)Resources.UnloadAsset(loaded);}
        }
        public static void Run(){
            report=new Report{unity=Application.unityVersion};string output=Environment.GetEnvironmentVariable("HOTR_STAGING104_NATIVE_OUT");
            try{
                string json=File.ReadAllText(Environment.GetEnvironmentVariable(StagingServerBuild104.ConfigVariable)),receipt=Environment.GetEnvironmentVariable(StagingServerBuild104.IsolationVariable);
                ServerGameplayConfiguration c;string error;Check(ServerStagingConfiguration104.TryParsePackaged(json,out c,out error),"fixture_config_valid");string canonical=ServerStagingConfiguration104.CanonicalJson(c);
                Check(StagingServerBuild104.Preflight(json,receipt).Length==0,"owned_isolation_receipt");
                Check(PlayerSettings.companyName=="HeartRainStaging104"&&PlayerSettings.productName=="HeartRainStaging104","isolated_editor_identity");
                string package=PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android);bool signing=PlayerSettings.Android.useCustomKeystore,bundle=EditorUserBuildSettings.buildAppBundle,export=EditorUserBuildSettings.exportAsGoogleAndroidProject;
                var result=StagingServerBuild104.RunWithBuildDelegate(json,receipt,()=>Imported(canonical));
                Check(result.cleaned&&result.settingsRestored&&!result.built,"success_delegate_not_apk");Empty();report.successCleanup=true;
                StagingServerBuild104.BuildOutcome failed=null;bool caught=false;try{StagingServerBuild104.RunWithBuildDelegate(json,receipt,()=>{Imported(canonical);throw new InvalidOperationException("SyntheticPackagingFailure104");},observed=>failed=observed);}catch(InvalidOperationException e){caught=e.Message=="SyntheticPackagingFailure104";}
                Check(caught,"throwing_delegate_observed");Empty();report.exceptionCleanup=true;
                Check(failed!=null&&failed.exceptionObserved&&failed.delegateInvoked&&failed.cleanupAttempted&&failed.cleaned&&failed.settingsRestored&&!failed.built&&!failed.buildInvoked&&failed.errors==-1,"failure_outcome_remains_truthful");
                Check(PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android)==package&&PlayerSettings.Android.useCustomKeystore==signing&&EditorUserBuildSettings.buildAppBundle==bundle&&EditorUserBuildSettings.exportAsGoogleAndroidProject==export,"all_changed_settings_restored");report.settingsRestored=true;
                var absent=Resources.Load<TextAsset>(ServerStagingConfiguration104.ResourceKey);Check(!absent,"resource_absent_after_cleanup");if(absent)Resources.UnloadAsset(absent);
                report.status="PASS_NATIVE_STAGING_PACKAGING104";
            }catch(Exception e){report.error=e is InvalidOperationException?e.Message:"isolated_packaging_verification_failed";}
            if(!string.IsNullOrEmpty(output)){Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"StagingPackaging104.json"),JsonUtility.ToJson(report,true));}
            if(Application.isBatchMode)EditorApplication.Exit(report.status.StartsWith("PASS",StringComparison.Ordinal)?0:1);
        }
        public static void RunPolicy(){
            report=new Report{unity=Application.unityVersion,scope="Actual native C# build-boundary policy and disposable on-disk ownership lease tests. Import/build delegates are synthetic; no main Assets/settings changes, BuildPipeline, APK, HTTP, provider or device operation."};
            string output=Environment.GetEnvironmentVariable("HOTR_STAGING104_NATIVE_OUT"),channel=Environment.GetEnvironmentVariable("HOTR_BUILD_CHANNEL");
            try{
                string path=ServerStagingConfiguration104.ResourceAssetPath,package=ServerStagingConfiguration104.PackageName;
                Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.Android,BuildOptions.Development,"com.owner.ordinary",false,Array.Empty<string>()).Length==0,"ordinary_no_payload_allowed");
                Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.Android,BuildOptions.Development,package,false,Array.Empty<string>()).Length>0,"staging_missing_payload_rejected");
                Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.Android,BuildOptions.Development,package,false,new[]{path},true).Length==0,"owned_development_policy");
                Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.Android,BuildOptions.None,package,false,new[]{path},true).Length>0,"nondevelopment_policy");
                Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.StandaloneWindows64,BuildOptions.Development,package,false,new[]{path},true).Length>0,"nonandroid_policy");
                Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.Android,BuildOptions.Development,"com.owner.ordinary",false,new[]{path},true).Length>0,"package_policy");
                Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.Android,BuildOptions.Development,package,true,new[]{path},true).Length>0,"signing_policy");
                Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.Android,BuildOptions.Development,package,false,new[]{path}).Length>0,"unowned_policy");
                Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.Android,BuildOptions.Development,package,false,new[]{path},true,true).Length>0,"stale_policy");
                foreach(string shadow in new[]{"Assets/Other/Resources/HOTR_Server/ManagedStaging.bytes","Packages/fixture/Resources/hotr_server/managedstaging.json","Assets/Other/Resources/HOTR_Server/ManagedStaging/nested.txt","Assets/Other/Resources/HOTR_Server/ManagedStaging"}){
                    Check(StagingServerBuild104.ReservedResourcePath(shadow),"shadow_key_detected");Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.Android,BuildOptions.Development,package,false,new[]{path,shadow},true).Length>0,"shadow_policy_rejected");
                }
                Environment.SetEnvironmentVariable("HOTR_BUILD_CHANNEL","rustore");Check(StagingServerBuild104.VerifyBuildBoundary(BuildTarget.Android,BuildOptions.Development,package,false,new[]{path},true).Length>0,"rustore_policy");Environment.SetEnvironmentVariable("HOTR_BUILD_CHANNEL",channel);
                string json="{\"version\":1,\"mode\":\"ManagedGuestServer\",\"origin\":\"https://staging.hotr-native-fixture.net\",\"identityScope\":\"review-vk-staging\",\"allowDevelopmentLoopback\":false,\"socialEnabled\":true}";
                string basis=Path.GetFullPath(Path.Combine("..",".verification-cache","Review104","LeaseCases",Guid.NewGuid().ToString("N")));
                Func<string,string> fresh=name=>{string root=Path.Combine(basis,name);Directory.CreateDirectory(Path.Combine(root,"Assets/HeartOfTheRain/Resources"));return root;};
                Action<string> empty=root=>{Check(!File.Exists(Path.Combine(root,path)),"fixture_payload_cleaned");Check(!File.Exists(Path.Combine(root,path)+".meta"),"fixture_asset_meta_cleaned");Check(!File.Exists(Path.Combine(root,StagingServerBuild104.LeaseFile)),"fixture_marker_cleaned");Check(!Directory.Exists(Path.GetDirectoryName(Path.Combine(root,path))),"fixture_folder_cleaned");Check(!File.Exists(Path.GetDirectoryName(Path.Combine(root,path))+".meta"),"fixture_folder_meta_cleaned");};
                string success=fresh("success"),successInput=Path.DirectorySeparatorChar=='\\'?success.Replace('\\','/').Replace("/success","/SUCCESS"):success;int importCalls=0,buildCalls=0;StagingServerBuild104.ExerciseFileLeaseForVerification(successInput,json,()=>importCalls++,()=>buildCalls++);Check(importCalls==1&&buildCalls==1,"fixture_mixed_separator_case_delegates_once");empty(success);
                string importFailure=fresh("import_failure");bool caught=false;try{StagingServerBuild104.ExerciseFileLeaseForVerification(importFailure,json,()=>{throw new InvalidOperationException("synthetic_import");},null);}catch(InvalidOperationException e){caught=e.Message=="synthetic_import";}Check(caught,"import_failure_observed");empty(importFailure);
                string buildFailure=fresh("build_failure");caught=false;try{StagingServerBuild104.ExerciseFileLeaseForVerification(buildFailure,json,null,()=>{throw new InvalidOperationException("synthetic_build");});}catch(InvalidOperationException e){caught=e.Message=="synthetic_build";}Check(caught,"build_failure_observed");empty(buildFailure);
                string occupied=fresh("occupied_meta"),folder=Path.GetDirectoryName(Path.Combine(occupied,path));File.WriteAllText(folder+".meta","synthetic_foreign_meta");caught=false;try{StagingServerBuild104.ExerciseFileLeaseForVerification(occupied,json,null,null);}catch(InvalidOperationException e){caught=e.Message=="StagingLeasePathOccupied";}Check(caught&&File.ReadAllText(folder+".meta")=="synthetic_foreign_meta","foreign_meta_preserved");Check(!File.Exists(Path.Combine(occupied,StagingServerBuild104.LeaseFile)),"occupied_never_owned");
                string occupiedAsset=fresh("occupied_asset");Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(occupiedAsset,path)));File.WriteAllText(Path.Combine(occupiedAsset,path),"synthetic_preexisting_resource");caught=false;try{StagingServerBuild104.ExerciseFileLeaseForVerification(occupiedAsset,json,null,null);}catch(InvalidOperationException e){caught=e.Message=="StagingLeasePathOccupied";}Check(caught&&File.ReadAllText(Path.Combine(occupiedAsset,path))=="synthetic_preexisting_resource","preexisting_resource_preserved");
                string foreign=fresh("foreign_payload");caught=false;try{StagingServerBuild104.ExerciseFileLeaseForVerification(foreign,json,null,()=>File.WriteAllText(Path.Combine(foreign,path),"synthetic_foreign_payload"));}catch(InvalidOperationException e){caught=e.Message=="ForeignStagingBytesPreserved";}Check(caught&&File.ReadAllText(Path.Combine(foreign,path))=="synthetic_foreign_payload"&&File.Exists(Path.Combine(foreign,StagingServerBuild104.LeaseFile)),"foreign_payload_and_proof_preserved");
                string changed=fresh("changed_marker");caught=false;try{StagingServerBuild104.ExerciseFileLeaseForVerification(changed,json,null,()=>File.WriteAllText(Path.Combine(changed,StagingServerBuild104.LeaseFile),"synthetic_foreign_marker"));}catch(InvalidOperationException e){caught=e.Message=="StagingOwnershipChangedPreserved";}Check(caught&&File.Exists(Path.Combine(changed,path))&&File.ReadAllText(Path.Combine(changed,StagingServerBuild104.LeaseFile))=="synthetic_foreign_marker","changed_marker_preserves_all_bytes");
                report.status="PASS_NATIVE_STAGING_POLICY104";
            }catch(Exception e){report.error=e is InvalidOperationException?e.Message:"staging_policy_verification_failed";}
            finally{Environment.SetEnvironmentVariable("HOTR_BUILD_CHANNEL",channel);}
            if(!string.IsNullOrEmpty(output)){Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"StagingPolicy104.json"),JsonUtility.ToJson(report,true));}
            if(Application.isBatchMode)EditorApplication.Exit(report.status.StartsWith("PASS",StringComparison.Ordinal)?0:1);
        }
    }
}
#endif
