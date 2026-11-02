#if UNITY_EDITOR
using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification
{
    public static class SpriteScale94
    {
        const string Asset = "Assets/ImporterScale94/TM_WellRally.png";
        [Serializable] sealed class Preparation { public string status, assetSHA256, metaSHA256, templateSHA256; }
        [Serializable] sealed class Report
        {
            public string status = "FAIL_NATIVE_SPRITE_SCALE94", utc, unity, project, activeBuildTarget, error;
            public string assetSHA256, originalMetaSHA256, importedMetaSHA256, guid, spriteGuid, textureGuid;
            public string importerPPUBits, spritePPUBits, heightScalePPUBits;
            public long spriteFileID, textureFileID;
            public int checks, sourceWidth, sourceHeight, textureWidth, textureHeight, mipmapCount, spriteMode;
            public float importerPPU, spritePPU, heightScalePPU, sourceToRectScaleX, sourceToRectScaleY;
            public Rect spriteRect;
            public Vector4 importerBorder, spriteBorder;
            public Vector2 importerPivot, spritePivot;
            public bool originalMetaWasReserialized, ppuMatchesHeightScale, inputPNGUnchanged;
            public string scope = "One exact original PNG/meta copied into an existing tiny private project; actual native importer/Sprite/Texture2D readbacks. No PPU correction, importer write, main/full-candidate change, model command, device rendering or broad migration approval.";
        }
        static Report report;
        static void Check(bool value, string reason) { report.checks++; if (!value) throw new InvalidOperationException(reason); }
        static string Hash(string path) { using (var h=SHA256.Create()) using(var s=File.OpenRead(path)) return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant(); }
        static string Bits(float value) { return BitConverter.ToInt32(BitConverter.GetBytes(value),0).ToString("x8"); }
        static void NoLinks(string path) { for(var p=new FileInfo(path) as FileSystemInfo;p!=null;p=Directory.GetParent(p.FullName)) if(p.Exists&&(p.Attributes&FileAttributes.ReparsePoint)!=0) throw new InvalidOperationException("Linked path refused"); }
        public static void Run()
        {
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};string output=null;
            try
            {
                string project=Path.GetFullPath(Path.Combine(Application.dataPath,".."));report.project=project;
                var folder=new DirectoryInfo(project);var model=folder.Parent;var migration=model==null?null:model.Parent;var cache=migration==null?null:migration.Parent;var workspace=cache==null?null:cache.Parent;
                Check((folder.Name=="Baseline2022"||folder.Name=="Candidate6")&&model!=null&&model.Name=="ModelProbe"&&migration!=null&&migration.Name=="Unity6Migration94"&&cache!=null&&cache.Name==".verification-cache"&&workspace!=null,"Exact existing private model-probe projects only");
                string version=Environment.GetEnvironmentVariable("HOTR_SCALE94_VERSION");
                Check(version==Application.unityVersion&&(folder.Name=="Baseline2022"?version=="2022.3.62f3":version=="6000.6.6f1"),"Exact project/engine version agreement");
                string supplied=Environment.GetEnvironmentVariable("HOTR_SCALE94_OUT");
                Check(!string.IsNullOrEmpty(supplied)&&Path.IsPathRooted(supplied),"Explicit absolute output required");
                output=Path.GetFullPath(supplied);
                string allowed=Path.GetFullPath(Path.Combine(workspace.FullName,"Verification/Evidence/Unity6Migration94/SpriteScale"))+Path.DirectorySeparatorChar;
                Check(output.StartsWith(allowed,StringComparison.OrdinalIgnoreCase),"Scoped sprite-scale output required");
                NoLinks(output);Directory.CreateDirectory(output);
                string prepared=Environment.GetEnvironmentVariable("HOTR_SCALE94_PREPARED");
                Check(!string.IsNullOrEmpty(prepared)&&Path.IsPathRooted(prepared)&&Path.GetFullPath(prepared).StartsWith(allowed,StringComparison.OrdinalIgnoreCase),"Bound explicit sprite-scale preparation required");
                NoLinks(prepared);
                var preparation=JsonUtility.FromJson<Preparation>(File.ReadAllText(prepared));
                Check(preparation.status=="PREPARED_TWO_NATIVE_SPRITE_SCALE94_PROJECTS","Exact prepared original source copies required");
                string asset=Path.Combine(project,Asset), original=Path.Combine(workspace.FullName,"Unity/Assets/HeartOfTheRain/App/Teams/Art/TM_WellRally.png");
                NoLinks(asset);NoLinks(original);NoLinks(original+".meta");
                report.assetSHA256=Hash(asset);report.originalMetaSHA256=Hash(original+".meta");report.importedMetaSHA256=Hash(asset+".meta");
                Check(report.assetSHA256==preparation.assetSHA256&&Hash(original)==preparation.assetSHA256&&report.originalMetaSHA256==preparation.metaSHA256,"Exact original PNG and source metadata remain unchanged");
                Check(Hash(Path.Combine(project,"Assets/Editor/SpriteScale94.cs"))==preparation.templateSHA256,"Exact identical native readback template");
                report.originalMetaWasReserialized=report.importedMetaSHA256!=report.originalMetaSHA256;
                var importer=AssetImporter.GetAtPath(Asset) as TextureImporter;
                var sprite=AssetDatabase.LoadAssetAtPath<Sprite>(Asset);var texture=AssetDatabase.LoadAssetAtPath<Texture2D>(Asset);
                Check(importer!=null&&sprite!=null&&texture!=null,"Actual importer/Sprite/Texture2D resolve");
                importer.GetSourceTextureWidthAndHeight(out report.sourceWidth,out report.sourceHeight);
                report.activeBuildTarget=EditorUserBuildSettings.activeBuildTarget.ToString();report.spriteMode=(int)importer.spriteImportMode;
                report.textureWidth=texture.width;report.textureHeight=texture.height;report.mipmapCount=texture.mipmapCount;report.spriteRect=sprite.rect;
                report.importerPPU=importer.spritePixelsPerUnit;report.spritePPU=sprite.pixelsPerUnit;
                report.sourceToRectScaleX=sprite.rect.width/report.sourceWidth;report.sourceToRectScaleY=sprite.rect.height/report.sourceHeight;
                report.heightScalePPU=report.importerPPU*report.sourceToRectScaleY;
                report.importerPPUBits=Bits(report.importerPPU);report.spritePPUBits=Bits(report.spritePPU);report.heightScalePPUBits=Bits(report.heightScalePPU);
                report.ppuMatchesHeightScale=Mathf.Abs(report.spritePPU-report.heightScalePPU)<.0001f;
                report.importerBorder=importer.spriteBorder;report.spriteBorder=sprite.border;report.importerPivot=importer.spritePivot;report.spritePivot=sprite.pivot;
                report.guid=AssetDatabase.AssetPathToGUID(Asset);
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(sprite,out report.spriteGuid,out report.spriteFileID);
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(texture,out report.textureGuid,out report.textureFileID);
                Check(report.activeBuildTarget=="Android"&&report.guid=="2942989e23b753738db9843c2436a5c9"&&report.spriteGuid==report.guid&&report.textureGuid==report.guid,"Original GUID and exact Android import target");
                Check(report.sourceWidth==2170&&report.sourceHeight==725&&report.spriteMode==(int)SpriteImportMode.Single,"Original source dimensions and single-sprite mode");
                report.inputPNGUnchanged=Hash(asset)==preparation.assetSHA256&&Hash(original)==preparation.assetSHA256&&Hash(original+".meta")==preparation.metaSHA256;
                Check(report.inputPNGUnchanged,"Readback did not change original/copy PNG or original metadata");
                report.status="RECORDED_NATIVE_SPRITE_SCALE94_REQUIRES_COMPARISON";
            }
            catch(Exception error) { report.error=error.ToString(); }
            if(output!=null)using(var f=new FileStream(Path.Combine(output,"Native.json"),FileMode.CreateNew,FileAccess.Write,FileShare.Read))using(var w=new StreamWriter(f,new UTF8Encoding(false)))w.Write(JsonUtility.ToJson(report,true));
            else Debug.LogError("Sprite-scale probe refused before scoped output");
            EditorApplication.Exit(report.status.StartsWith("RECORDED_",StringComparison.Ordinal)?0:1);
        }
    }
}
#endif
