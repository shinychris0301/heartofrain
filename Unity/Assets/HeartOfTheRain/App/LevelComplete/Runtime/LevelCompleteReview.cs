using System.Collections;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.App.LevelComplete {
 // Explicit visual fixture: neither a real win nor a campaign reward grant.
 public sealed class LevelCompleteReview:MonoBehaviour {
  public HomePage home;public LevelCompleteAssets assets;public int initialLevel=18;
  GameplayScreen board;LevelCompleteModal modal;
  IEnumerator Start(){if(!home||!assets)yield break;home.Build();yield return null;
   board=new GameObject("M66 isolated visual review board").AddComponent<GameplayScreen>();board.uiAssets=assets.preLevel.gameplay;board.initialLevel=initialLevel;board.showLevelIntro=false;board.pendingStartingPowers=new int[0];board.ReviewInputBlocked=true;
   float until=Time.realtimeSinceStartup+15;while(board&&!board.InitializationComplete&&Time.realtimeSinceStartup<until)yield return null;
   if(!board||!board.InitializationComplete){Debug.LogError("M66 review board failed to initialize.");if(board)Destroy(board.gameObject);yield break;}
   board.SetPause(true);home.SetPresentation(false,false);modal=gameObject.AddComponent<LevelCompleteModal>();modal.home=home;modal.assets=assets;
   var fixture=new HomeState{currentLevel=initialLevel,completedLevelsInChapter=initialLevel-1,coins=1250,stars=0};var session=new LevelCompleteSession();session.Arm(1,initialLevel);session.TrySettle(initialLevel,"Won",false,fixture,50,assets.preLevel.rewardCoins,assets.preLevel.rewardStars);
   modal.Requested=_=>{modal.Hide();board.gameObject.SetActive(false);Destroy(board.gameObject);board=null;home.SetPresentation(true,true);};board.GetComponent<GameplayHUD>().ExternalResultVisible=()=>modal&&modal.IsVisible;modal.Show(session.View);var feedback=board.GetComponent<GameplayFeedback>();feedback.SetSoundEnabled(PlayerPrefs.GetInt("HeartOfTheRain.Settings.v1.sound",1)!=0);feedback.Play("level_win",1,"success");
  }
  void OnDestroy(){if(board)Destroy(board.gameObject);}
 }
}
