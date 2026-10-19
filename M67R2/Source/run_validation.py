from pathlib import Path
import os,subprocess,json,sys,shutil
R=Path(__file__).resolve().parents[1];project=(R.parent/'Unity') if (R.parent/'Unity').exists() else R/'Project/Heart_of_the_Rain_M66/Unity';U=project/'Assets/HeartOfTheRain';A=U/'App';sdk=Path(os.environ.get('M67_DOTNET_ROOT',str(Path(shutil.which('dotnet')).resolve().parent) if shutil.which('dotnet') else str(R.parent/'tmp/m67_dotnet')));out=R/'Validation/Build';out.mkdir(exist_ok=True)
dotnet=sdk/('dotnet.exe' if os.name=='nt' else 'dotnet');csc=next(sdk.glob('sdk/*/Roslyn/bincore/csc.dll'));refs=next(sdk.glob('packs/Microsoft.NETCore.App.Ref/*/ref/net8.0'))
env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_CLI_TELEMETRY_OPTOUT='1')
def run(name,sources):
 dll=out/(name+'.dll');subprocess.run([str(dotnet),str(csc),'-nologo','-target:exe','-out:'+str(dll)]+['-r:'+str(p) for p in refs.glob('*.dll')]+[str(p) for p in sources],check=True,env=env)
 dll.with_suffix('.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.0'}}}))
 subprocess.run([str(dotnet),str(dll),str(R)],check=True,env=env)
base=[A/'Home/Runtime/HomeLayoutEngine.cs',A/'Journey/Runtime/JourneySession.cs',A/'Journey/Runtime/JourneyLayout.cs',A/'Journey/Runtime/JourneyText.cs']+[p for p in (A/'Localization/Runtime').glob('*.cs') if p.name!='LocaleBootstrap.cs']
base += [A/'LevelComplete/Runtime'/n for n in ['LevelCompleteSession.cs','LevelCompleteLayout.cs','LevelCompleteMotion.cs','LevelCompleteText.cs']]+[A/'Celebrations/Runtime/CelebrationMotion.cs',A/'Celebrations/Runtime/CelebrationText.cs']
run('Completion',base+[R/'M66Reference/Source/CompletionChecks.cs'])
run('Celebration',base+[R/'Source/CelebrationChecks.cs'])
run('Victory',[A/'Celebrations/Runtime/VictoryMotion.cs',R/'Source/VictoryChecks.cs'])

# Compile and drive the actual production controller with an explicit fake UI host.
fakes=(R/'M66Reference/Source/FlowFakes.cs').read_text()+'''
namespace HeartOfTheRain.App.Celebrations {
 public sealed class VictoryCelebrationPlayer:UnityEngine.MonoBehaviour {
  public static bool Enabled=true;public bool IsVisible;public System.Action callback;
  public static bool TryPlay(HeartOfTheRain.App.Home.HomePage h,int level,System.Action after){if(!Enabled)return false;var p=h.gameObject.GetComponent<VictoryCelebrationPlayer>()??h.gameObject.AddComponent<VictoryCelebrationPlayer>();if(p.IsVisible)return false;p.IsVisible=true;p.callback=after;return true;}
  public void Finish(){if(!IsVisible)return;IsVisible=false;var f=callback;callback=null;f?.Invoke();}
  public void Cancel(){callback=null;Finish();}
 }
 public sealed class ChapterCelebrationPlayer:UnityEngine.MonoBehaviour {
  public static bool Enabled=true;public bool IsVisible;public System.Action callback;
  public static bool TryPlay(HeartOfTheRain.App.Home.HomePage h,int c,System.Action after){if(!Enabled||c!=1)return false;var p=h.gameObject.GetComponent<ChapterCelebrationPlayer>()??h.gameObject.AddComponent<ChapterCelebrationPlayer>();if(p.IsVisible)return false;p.IsVisible=true;p.callback=after;return true;}
  public void Finish(){if(!IsVisible)return;IsVisible=false;var f=callback;callback=null;f?.Invoke();}
  public void Cancel(){callback=null;Finish();}
 }
}
'''
(out/'FlowFakes.cs').write_text(fakes)
checks=(R/'Source/CompletionFlowChecks.cs').read_text().replace('"PROJECT_REPLAY_PATH"',json.dumps(str(U/'M48/Resources/HOTR_Playtests/Campaign_Replays.json')))
(out/'CompletionFlowChecks.cs').write_text(checks)
flow=[U/'M46/Runtime'/n for n in ['BoardModel.cs','StartingPowersPure.cs','LivePowerPlan.cs','ReviewPlan.cs','GoldenSeekerComboPlan.cs','BoardPresentation.cs','ReviewScenario.cs']]
flow+=list((U/'Boosters/Runtime').glob('*Pure.cs'))+list((U/'M48/Runtime').glob('*Pure.cs'))+[U/'M47/Runtime/FeedbackPlanPure.cs',R/'CoreReference/Tests/UnityMathShim.cs',A/'Home/Runtime/HomeLayoutEngine.cs',A/'PreLevel/Runtime/PreLevelSession.cs',A/'PreLevel/Runtime/PreLevelLayout.cs',A/'PreLevel/Runtime/HomeLevelFlow.cs',A/'EndLevel/Runtime/EndLevelSession.cs',out/'FlowFakes.cs',out/'CompletionFlowChecks.cs',A/'LevelComplete/Runtime/LevelCompleteSession.cs',A/'Celebrations/Runtime/CelebrationMotion.cs']
flow+=[p for p in (A/'Localization/Runtime').glob('*.cs') if p.name!='LocaleBootstrap.cs']
run('CompletionFlow',flow)

sys.path.insert(0,str(R.parent/'tmp/m67_python'))
from tree_sitter import Language,Parser
import tree_sitter_c_sharp
parser=Parser(Language(tree_sitter_c_sharp.language()));fail=[];count=0
for p in U.rglob('*.cs'):
 count+=1
 if parser.parse(p.read_bytes()).root_node.has_error:fail.append(str(p.relative_to(U)))
report={'status':'PASS' if not fail else 'FAIL','csharp_files':count,'syntax_errors':fail,'unity_api_compilation':'NOT_RUN','shader_compilation':'NOT_RUN'}
(R/'Validation/Syntax.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));assert not fail
