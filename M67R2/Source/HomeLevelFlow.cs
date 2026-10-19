using System;
using HeartOfTheRain.App.Celebrations;
using System.Collections;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.EndLevel;
using HeartOfTheRain.App.LevelComplete;
using HeartOfTheRain.App.Journey;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.App.PreLevel
{
    [DisallowMultipleComponent]
    public sealed class HomeLevelFlow:MonoBehaviour
    {
        public HomePage home;public PreLevelAssets assets;public GameplaySettingsAssets settingsAssets;public EndLevelAssets endLevelAssets;
        PreLevelSession session;PreLevelModal modal;GameplayScreen gameplay;readonly LevelCompleteSession completion=new LevelCompleteSession();
        public PreLevelViewData Preview {get{return session==null?null:session.View;}}
        public bool Playing {get{return gameplay&&gameplay.Ready;}}
        public bool CanOpenAppSettings {get{return session!=null&&!session.IsOpen&&!gameplay&&!session.View.busy;}}
        public int[] StartingStockSnapshot(){return session==null?new int[4]:Enumerable.Range(0,4).Select(i=>session.Count(i)).ToArray();}
        public bool RetryVisible {get{return session!=null&&session.IsOpen&&session.View.retry&&modal&&modal.IsVisible;}}
        void Start()
        {
            if(!home||!assets||!assets.home||!assets.gameplay){Debug.LogError("Assign Home and PreLevelAssets.",this);enabled=false;return;}
            session=new PreLevelSession(assets.initialStock);modal=gameObject.AddComponent<PreLevelModal>();modal.home=home;modal.assets=assets;modal.Requested=Handle;
            home.PreLevelRequested.AddListener(Open);
        }
        public void Open(int level){OpenPreview(level,false);}
        void OpenPreview(int level,bool retry)
        {
            if(session==null||gameplay||session.View.busy||completion.IsOpen)return;
            int index=Mathf.Clamp(level-1,0,assets.gameplay.boards.levels.Length-1);
            var data=JsonUtility.FromJson<LevelData>(assets.gameplay.boards.levels[index].text);
            int completed=Math.Max(home.State.currentLevel-1,(home.State.chapterNumber-1)*50+home.State.completedLevelsInChapter);bool rewardEligible=index+1==completed+1;
            session.Open(index+1,home.State.lives,data.goals.Select(g=>new PreLevelGoal{family=g.family,count=g.count}).ToArray(),rewardEligible?assets.rewardCoins:0,rewardEligible?assets.rewardStars:0,retry:retry);
            home.SetPresentation(true,false);modal.Show(session.View);
        }
        void Update()
        {
            if(session==null||!session.IsOpen||session.View.busy||session.View.lives==home.State.lives)return;
            session.RefreshLives(home.State.lives);modal.Show(session.View);
        }
        void Handle(string action)
        {
            if(action=="close")
            {if(session.Close()){modal.Hide();home.SetPresentation(true,true);}return;}
            if(action.StartsWith("toggle:",StringComparison.Ordinal))
            {int index;if(int.TryParse(action.Substring(7),out index))session.Toggle(index);modal.Show(session.View);return;}
            if(action=="play")
            {
                session.RefreshLives(home.State.lives);
                PreLevelTicket ticket;
                if(session.TryBegin(out ticket)){modal.Show(session.View);StartCoroutine(Launch(ticket));}
                else modal.Show(session.View);
            }
        }
        IEnumerator Launch(PreLevelTicket ticket)
        {
            var go=new GameObject("Level "+ticket.level);gameplay=go.AddComponent<GameplayScreen>();
            gameplay.uiAssets=assets.gameplay;gameplay.initialLevel=ticket.level;gameplay.showLevelIntro=false;
            gameplay.pendingStartingPowers=(int[])ticket.powerKinds.Clone();gameplay.ReviewInputBlocked=true;
            float until=Time.realtimeSinceStartup+15;
            while(gameplay&&!gameplay.InitializationComplete&&Time.realtimeSinceStartup<until)yield return null;
            // Ready is not sufficient: verify the one-shot grant finished before consuming inventory.
            if(!gameplay||!gameplay.InitializationComplete||!gameplay.HasStartedWithPowers||!string.IsNullOrEmpty(gameplay.StartingPowerError))
            {
                if(gameplay)Destroy(gameplay.gameObject);gameplay=null;
                session.Fail(ticket,"Could not start. Please try again.");modal.Show(session.View);yield break;
            }
            if(!session.Complete(ticket)){Destroy(gameplay.gameObject);gameplay=null;yield break;}
            var launched=gameplay;
            if(settingsAssets)gameplay.gameObject.AddComponent<GameplaySettingsController>().Configure(gameplay,settingsAssets,home,decision=>ConfirmExit(launched,decision),endLevelAssets);
            if(completion.Arm(ticket.id,ticket.level)){
                var hud=gameplay.GetComponent<GameplayHUD>();hud.ResultRequested=(won,number)=>TryShowCompletion(launched,won,number);hud.ExternalResultVisible=()=>completion.IsOpen;
            }
            gameplay.ReviewInputBlocked=false;modal.Hide();home.SetPresentation(false,false);
        }
        bool TryShowCompletion(GameplayScreen source,bool won,int number)
        {
            if(!won||!source||source!=gameplay||!source.Ready||number!=source.CurrentLevel)return false;
            if(completion.IsOpen)return true;
            if(!completion.TrySettle(number,source.Model.Status,source.Busy,home.State,Math.Min(50,assets.gameplay.boards.levels.Length),assets.rewardCoins,assets.rewardStars))return false;
            source.ReviewInputBlocked=true;source.SetPause(true);source.GetComponent<GameplayHUD>().Close(false);
            home.ApplyState(home.State);var journey=home.GetComponent<JourneyPage>();if(journey)journey.UseHomeProgress();
            if(CelebrationMotion.ShouldPlayFinale(number,completion.View.firstClear,completion.View.completedAfter)&&ChapterCelebrationPlayer.TryPlay(home,completion.View.chapter,()=>FinishCompletion("continue")))return true;
            source.GetComponent<GameplayFeedback>().Play("level_win",1,"success");
            if(!VictoryCelebrationPlayer.TryPlay(home,number,()=>FinishCompletion("continue")))FinishCompletion("continue");
            return true;
        }
        void FinishCompletion(string action)
        {
            if(action!="continue"&&action!="home")return;if(!completion.IsOpen)return;var result=completion.View;if(!completion.Close())return;
            if(gameplay){gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;}modal.Hide();home.SetPresentation(true,true);
            if(action=="home")return;
            if(result.chapterComplete){var journey=home.GetComponent<JourneyPage>();if(journey){journey.UseHomeProgress();journey.Show();journey.Request("view:"+result.chapter);journey.Request("next");}return;}
            if(result.hasNext)OpenPreview(result.nextLevel,false);
        }
        void ConfirmExit(GameplayScreen source,EndLevelDecision decision)
        {
            if(!source||source!=gameplay||decision==null||decision.Level!=gameplay.CurrentLevel)return;
            home.State.currentLevel=gameplay.CurrentLevel;home.State.lives=decision.LivesAfter;home.ApplyState(home.State);
            gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;
            modal.Hide();OpenPreview(decision.Level,true);
        }
        // Review-only shortcut: bypasses life loss. Player exit uses the M58 confirmation.
        public void ReturnHomeForReview()
        {
            if(session==null||session.View.busy)return;
            var victory=home.GetComponent<VictoryCelebrationPlayer>();if(victory&&victory.IsVisible)victory.Cancel();
            var cinematic=home.GetComponent<ChapterCelebrationPlayer>();if(cinematic&&cinematic.IsVisible)cinematic.Cancel();
            if(gameplay){gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;}
            if(completion.IsOpen)completion.Close();modal.Hide();home.SetPresentation(true,true);
        }
        void OnDestroy(){if(home){var v=home.GetComponent<VictoryCelebrationPlayer>();if(v&&v.IsVisible)v.Cancel();var c=home.GetComponent<ChapterCelebrationPlayer>();if(c&&c.IsVisible)c.Cancel();home.PreLevelRequested.RemoveListener(Open);}if(gameplay)Destroy(gameplay.gameObject);}
    }
}
