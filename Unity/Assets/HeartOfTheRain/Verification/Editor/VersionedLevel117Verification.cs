#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.App.Profile;

namespace HeartOfTheRain.Verification {
    public static class VersionedLevel117Verification {
        [Serializable] sealed class Report {public string status,error="",scope="Editor model and temporary in-memory profile; no Android or hosted replay verification";public int checks,levels;}
        public static void Run(){
            var report=new Report();
            void Check(bool value,string message){report.checks++;if(!value)throw new Exception(message);}
            void Reject(Action action,string message){bool rejected=false;try{action();}catch(InvalidOperationException){rejected=true;}Check(rejected,message);}
            try{
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                var fake=ScriptableObject.CreateInstance<M46Assets>();fake.levels=(TextAsset[])ui.boards.levels.Clone();
                for(int n=1;n<=50;n++){
                    var old=Resources.Load<TextAsset>("HOTR_LegacyLevels117/C01_L"+n.ToString("D3"));
                    Check(old!=null,"Archive exists L"+n);
                    string disk=File.ReadAllText("Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/C01_L"+n.ToString("D3")+".json");
                    Check(old.text==disk,"Unity text matches archived UTF8 text L"+n);
                    var current=fake.levels[n-1];var different=new TextAsset(current.text+"\n ");fake.levels[n-1]=different;
                    var legacy=VersionedLevel117.Resolve(fake,n,ProfileJson.Hash(old.text));var active=VersionedLevel117.Resolve(fake,n,ProfileJson.Hash(different.text));
                    Check(JsonUtility.ToJson(legacy)==JsonUtility.ToJson(JsonUtility.FromJson<LevelData>(old.text)),"Hash selects legacy L"+n);
                    Check(JsonUtility.ToJson(active)==JsonUtility.ToJson(JsonUtility.FromJson<LevelData>(different.text)),"Hash selects active L"+n);
                    var graphics=VersionedLevel117.ResolveGraphics(fake,n,ProfileJson.Hash(old.text));
                    Check(graphics!=null&&graphics.level==n&&graphics.config==ProfileJson.Hash(old.text),"Original graphics are bound to the exact old config L"+n);
                    string Sha(string resource){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes("Assets/HeartOfTheRain/M48/Resources/"+resource+".png"))).Replace("-","").ToLowerInvariant();}
                    Check(Sha(graphics.surface)==graphics.surfaceSHA256&&Sha(graphics.mask)==graphics.maskSHA256,"Original graphics source bytes match manifest L"+n);
                    Check(VersionedLevel117.ResolveGraphics(fake,n,ProfileJson.Hash(different.text))==null,"Active hash selects active graphics L"+n);
                    Reject(()=>VersionedLevel117.Resolve(fake,n,new string('0',64)),"Unknown hash rejected L"+n);
                    Reject(()=>VersionedLevel117.ResolveGraphics(fake,n,new string('0',64)),"Unknown graphics version rejected L"+n);
                    fake.levels[n-1]=current;UnityEngine.Object.DestroyImmediate(different);report.levels++;
                }
                int number=50;var oldText=Resources.Load<TextAsset>("HOTR_LegacyLevels117/C01_L050");var oldLevel=JsonUtility.FromJson<LevelData>(oldText.text);
                var replacement=new TextAsset(fake.levels[number-1].text+"\n ");fake.levels[number-1]=replacement;
                string oldHash=ProfileJson.Hash(oldText.text);var binding=VersionedLevel117.ResolveGraphics(fake,number,oldHash);
                Reject(()=>VersionedLevel117.ValidateGraphics(new LegacyLevelGraphics117{level=number,config=oldHash,width=binding.width,height=binding.height,surface=binding.surface,mask="M48Textures/does-not-exist"},number,oldHash),"Missing legacy mask fails closed");
                Reject(()=>VersionedLevel117.ValidateGraphics(new LegacyLevelGraphics117{level=number,config=oldHash,width=binding.width+1,height=binding.height,surface=binding.surface,mask=binding.mask},number,oldHash),"Wrong graphics dimensions fail closed");
                Reject(()=>VersionedLevel117.ValidateGraphics(binding,number,new string('0',64)),"Graphics with a mismatched attempt hash fail closed");
                var bank=new M46AtlasBank(ui.boards);Check(bank.BoardSurface(number-1,binding.surface,binding.width,binding.height).texture==Resources.Load<Texture2D>(binding.surface)&&bank.BoardMask(number-1,binding.mask,binding.width,binding.height).texture==Resources.Load<Texture2D>(binding.mask),"Renderer binds the original surface and mask");bank.Dispose();
                var profileData=PlayerProfile.New(new[]{5,5,3,2});profileData.coins=1800;profileData.completed=49;profileData.currentLevel=50;var profile=new ProfileService(new MemoryProfileRepository(profileData));
                string id=Guid.NewGuid().ToString("N");profile.Reserve(id,number,ProfileJson.Hash(oldText.text),new int[4],50,1);profile.CommitStart(id);
                var board=new BoardModel(oldLevel,23018u);var checkpoint=board.Checkpoint();checkpoint.board.moves=0;checkpoint.board.status="Out of moves";
                var service=new DevelopmentContinueService(profile,new ContinueRules{enabled=true},()=>1000,n=>JsonUtility.FromJson<LevelData>(fake.levels[n-1].text),true,a=>VersionedLevel117.Resolve(fake,a.level,a.config));
                service.Capture(id,checkpoint);service.SetView(id,"shop");profile.RecoverInterrupted();
                var saved=service.Read(id);Check(saved.continuation.view=="shop"&&profile.Read().lives==5,"Legacy shop and life survive recovery");
                var restored=BoardModel.FromCheckpoint(VersionedLevel117.Resolve(fake,number,saved.config),JsonUtility.FromJson<BoardCheckpoint>(saved.continuation.checkpoint));
                Check(JsonUtility.ToJson(restored.Checkpoint())==JsonUtility.ToJson(checkpoint),"Legacy checkpoint restores exact geometry, RNG and pieces");
                string op=service.Prepare(id,service.Quote(id).id);var receipt=service.Purchase(id,op);var again=service.Purchase(id,op);
                Check(receipt.outcome=="Applied"&&again.operation==op&&profile.Read().coins==900&&profile.Read().lives==5,"Legacy purchase is applied once with no life debit");
                var paid=BoardModel.FromCheckpoint(oldLevel,JsonUtility.FromJson<BoardCheckpoint>(receipt.afterCheckpoint));Check(paid.Moves==5&&paid.Level.rows==oldLevel.rows&&paid.Level.columns==oldLevel.columns,"Paid checkpoint uses original layout");
                service.Acknowledge(id,op);profile.RecoverInterrupted();Check(service.Read(id).continuation.phase=="Purchased"&&profile.Read().coins==900,"Paid checkpoint remains recoverable once");
                Reject(()=>VersionedLevel117.Resolve(fake,0,ProfileJson.Hash(oldText.text)),"Out-of-range level rejected");
                UnityEngine.Object.DestroyImmediate(replacement);UnityEngine.Object.DestroyImmediate(fake);
            }catch(Exception e){report.error=e.ToString();}
            report.status=report.error==""?"PASS_VERSIONED_LEVEL117":"FAIL_VERSIONED_LEVEL117";
            string dir=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_VERSIONED_LEVEL_OUTPUT")??"../Verification/Evidence/Review117/VersionedLevels");Directory.CreateDirectory(dir);File.WriteAllText(Path.Combine(dir,"VersionedLevels117.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.error==""?0:1);
        }
    }
}
#endif
