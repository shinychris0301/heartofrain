using System.Collections;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.LevelComplete;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.App.Celebrations
{
    // Isolated review receipt; never writes player rewards or campaign progress.
    public sealed class CelebrationReview:MonoBehaviour
    {
        public HomePage home;public LevelCompleteAssets assets;public int initialLevel=18;
        GameplayScreen board;
        IEnumerator Start()
        {
            if(!home||!assets)yield break;home.Build();yield return null;
            board=new GameObject("M67 isolated review board").AddComponent<GameplayScreen>();
            board.uiAssets=assets.preLevel.gameplay;board.initialLevel=initialLevel;board.showLevelIntro=false;
            board.pendingStartingPowers=new int[0];board.ReviewInputBlocked=true;
            float until=Time.realtimeSinceStartup+15;
            while(board&&!board.InitializationComplete&&Time.realtimeSinceStartup<until)yield return null;
            if(!board||!board.InitializationComplete){Debug.LogError("M67 review board failed to initialize.");yield break;}
            board.SetPause(true);home.SetPresentation(false,false);
            System.Action finish=()=>{if(board){board.gameObject.SetActive(false);Destroy(board.gameObject);board=null;}home.SetPresentation(true,true);};
            board.GetComponent<GameplayHUD>().ExternalResultVisible=()=>ChapterCelebrationPlayer.IsPlaying(home)||VictoryCelebrationPlayer.IsPlaying(home);
            if(initialLevel==50&&ChapterCelebrationPlayer.TryPlay(home,1,finish))yield break;
            if(!VictoryCelebrationPlayer.TryPlay(home,initialLevel,finish)){finish();yield break;}
            var feedback=board.GetComponent<GameplayFeedback>();
            feedback.SetSoundEnabled(PlayerPrefs.GetInt("HeartOfTheRain.Settings.v1.sound",1)!=0);feedback.Play("level_win",1,"success");
        }
        void OnDestroy(){if(home){var v=home.GetComponent<VictoryCelebrationPlayer>();if(v&&v.IsVisible)v.Cancel();var p=home.GetComponent<ChapterCelebrationPlayer>();if(p&&p.IsVisible)p.Cancel();}if(board)Destroy(board.gameObject);}
    }
}
