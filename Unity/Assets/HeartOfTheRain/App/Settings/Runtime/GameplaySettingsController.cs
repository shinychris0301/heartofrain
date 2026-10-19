using System;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.EndLevel;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.App.Settings
{
    [DisallowMultipleComponent]
    public sealed class GameplaySettingsController:MonoBehaviour
    {
        sealed class Preferences:ISettingsStore
        {public int Read(string k,int d){return PlayerPrefs.GetInt(k,d);} public void Write(string k,int v){PlayerPrefs.SetInt(k,v);}public void Flush(){PlayerPrefs.Save();}}
        GameplayScreen game;GameplayHUD hud;GameplayFeedback feedback;GameplaySettingsModal modal;AudioSource music;
        GameSettingsState state;Action<EndLevelDecision> exitConfirmed;EndLevelModal endModal;EndLevelSession endSession=new EndLevelSession();HomePage home;bool configured,leaving,suspended;
        public bool IsVisible {get{return (modal&&modal.IsVisible)||(endModal&&endModal.IsVisible);}}
        public bool IsSettingsVisible {get{return modal&&modal.IsVisible;}}
        public bool IsEndLevelVisible {get{return endModal&&endModal.IsVisible;}}
        public void Configure(GameplayScreen screen,GameplaySettingsAssets assets,HomePage home,Action<EndLevelDecision> onExit,EndLevelAssets endAssets=null)
        {
            if(configured||!screen||!screen.Ready||!assets||!home)throw new InvalidOperationException("Settings require a ready gameplay screen, assets and Home.");
            configured=true;this.home=home;game=screen;hud=screen.GetComponent<GameplayHUD>();feedback=screen.GetComponent<GameplayFeedback>();exitConfirmed=onExit;
            state=new GameSettingsState(new Preferences());modal=gameObject.AddComponent<GameplaySettingsModal>();modal.assets=assets;modal.home=home;modal.Requested=Handle;
            if(endAssets){endModal=gameObject.AddComponent<EndLevelModal>();endModal.assets=endAssets;endModal.home=home;endModal.Requested=HandleEndLevel;}
            hud.SettingsRequested=Show;hud.ExternalSettingsVisible=()=>IsVisible;hud.CloseExternalSettings=Hide;
            music=gameObject.AddComponent<AudioSource>();music.playOnAwake=false;music.spatialBlend=0;music.loop=true;music.volume=.17f;music.clip=assets.reviewMusic;
            Apply();if(music.clip)music.Play();
        }
        void Apply(){feedback.SetSoundEnabled(state.Sound);game.HintsEnabled=state.Hints;music.mute=!state.Music;}
        public void Show(){if(!configured||leaving||IsEndLevelVisible||(hud.ExternalResultVisible!=null&&hud.ExternalResultVisible()))return;hud.Close(false);game.SetPause(true);feedback.Play("ui_open",.65f);modal.Show(state);}
        void Hide(){if(modal)modal.Hide();if(endModal)endModal.Hide();endSession.Cancel();}
        void Update()
        {
            if(IsEndLevelVisible&&endSession.View.lives!=home.State.lives)
            {endSession.RefreshLives(home.State.lives);endModal.Show(endSession.View);}
        }
        public void ShowEndLevel()
        {
            if(!configured||leaving||IsEndLevelVisible||(hud.ExternalResultVisible!=null&&hud.ExternalResultVisible()))return;
            modal.Hide();game.SetPause(true);
            if(!endSession.Open(game.CurrentLevel,home.State.lives))return;
            feedback.Play("ui_open",.65f);
            if(endModal)endModal.Show(endSession.View);
            else hud.ShowExitConfirmation(()=>{endSession.Cancel();game.SetPause(false);},()=>{endSession.Open(game.CurrentLevel,home.State.lives);CommitExit();});
        }
        void HandleEndLevel(string action)
        {
            if(leaving||!endSession.IsOpen)return;
            if(action=="cancel"){endSession.Cancel();Hide();feedback.Play("ui_tap",.55f);game.SetPause(false);return;}
            if(action=="confirm")CommitExit();
        }
        void CommitExit()
        {
            if(leaving)return;EndLevelDecision decision;
            if(!endSession.Confirm(home.State.lives,out decision))return;
            leaving=true;game.ReviewInputBlocked=true;Hide();music.Stop();exitConfirmed?.Invoke(decision);
        }
        void Handle(string action)
        {
            if(leaving)return;
            if(action.StartsWith("toggle:",StringComparison.Ordinal))
            {if(state.Toggle(action.Substring(7))){Apply();feedback.Play("ui_tap",.55f);modal.Show(state);}return;}
            if(action=="resume"){Hide();feedback.Play("ui_tap",.55f);game.SetPause(false);return;}
            if(action=="exit")ShowEndLevel();
        }

        void OnApplicationPause(bool value){suspended=value;if(music){if(value)music.Pause();else music.UnPause();}}
        void OnApplicationFocus(bool value){if(music&&!suspended){if(value)music.UnPause();else music.Pause();}}
        void OnDestroy(){if(hud){hud.SettingsRequested=null;hud.ExternalSettingsVisible=null;hud.CloseExternalSettings=null;}}
    }
}
