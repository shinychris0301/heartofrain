#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.Leaderboard;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Teams;
using UnityEngine;

namespace HeartOfTheRain.Verification
{
    public static partial class Regional89Verification
    {
        // Controlled native transport completions exercise the real parser,
        // owner fencing, protected-outbox CAS and session/page callbacks. No
        // iterator is sent over HTTP; this memory fixture is not a keystore.
        sealed class RegionMemoryStore:IProtectedSessionStore82 {
            byte[] data;
            public byte[] Read()=>data==null?null:(byte[])data.Clone();
            public void CompareExchange(string expected,byte[] replacement){if((data==null?"":IdentityProtocol82.Sha(data))!=expected)throw new InvalidOperationException("Controlled CAS conflict");data=(byte[])replacement.Clone();}
            public void Dispose(){if(data!=null)Array.Clear(data,0,data.Length);data=null;}
        }
        static readonly SocialPane82[] RankPanes={SocialPane82.GlobalRanks,SocialPane82.RegionalRanks,SocialPane82.GlobalTeamRanks,SocialPane82.RegionalTeamRanks};
        static string RegionJson(string player,string code)=>JsonUtility.ToJson(new SocialRegion89{playerId=player,regionCode=code,regionSource="player_selected_country",locationVerified=false});
        static void CompleteControlled(SocialBackendClient82 client,string json,string error=null,bool unknown=false){
            const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
            object pending=typeof(SocialBackendClient82).GetField("active",flags).GetValue(client);Check(pending!=null,"Controlled actual transport request exists");
            typeof(SocialBackendClient82).GetMethod("Complete",flags).Invoke(client,new[]{pending,json,error,(object)unknown});
            pending.GetType().GetMethod("Release",BindingFlags.Public|BindingFlags.Instance).Invoke(pending,null);
        }
        static void SeedRanks(SocialPageSession82 session,SocialBackendClient82 client,string player){
            foreach(string scope in new[]{"global","regional"}){
                Check(session.RefreshRanks(scope),"Seed actual typed "+scope+" player cache");
                CompleteControlled(client,JsonUtility.ToJson(new SocialLeaderboard82{scope=scope,regionCode=scope=="global"?"":"RU",scoreSource="server_verified_completed_levels",tiesShareRank=true,nextOffset=1,entries=new[]{new SocialRank82{playerId=player,displayName="Fixture",score=1,rank=1}}}));
                Check(session.RefreshTeamRanks(scope),"Seed actual typed "+scope+" team cache");
                CompleteControlled(client,JsonUtility.ToJson(new SocialTeamLeaderboard89{scope=scope,regionCode=scope=="global"?"":"RU",scoreSource="server_verified_opted_in_team_completed_levels",teamRegionSource="current_leader_selected_country",tiesShareRank=true,nextOffset=1,entries=new[]{new SocialTeamRank89{teamId=new string('7',32),name="Fixture team",score=1,memberCount=1,rank=1}}}));
            }
        }
        static void RanksAbsent(SocialPageSession82 session,string name){
            foreach(var pane in RankPanes)Check(pane==SocialPane82.GlobalRanks||pane==SocialPane82.RegionalRanks?session.Snapshot<SocialLeaderboard82>(pane)==null:session.Snapshot<SocialTeamLeaderboard89>(pane)==null,name+" drops cached "+pane);
        }
        static void ControlledRecovery(LeaderboardAssets art,TeamsAssets teamArt){
            string player=new string('5',32);long ownerGeneration=1;var access=new SocialAccess82(player,IdentityProtocol82.NewSecret());var routines=new List<IEnumerator>();
            using(var store=new RegionMemoryStore())using(var client=new SocialBackendClient82("http://127.0.0.1:1",()=>access,routine=>routines.Add(routine),store,true,true))using(var session=new SocialPageSession82(client,null,()=>ownerGeneration)){
                session.Show(SocialPane82.RegionalRanks);Check(session.RefreshRegion(),"Initial region fetch submitted");CompleteControlled(client,null,"SocialNetworkUnavailable");
                Check(session.RankingStatus(SocialPane82.RegionalRanks).state==SocialViewState82.Offline&&session.Snapshot<SocialRegion89>(SocialPane82.Region)==null,"Initial failed region GET stays offline rather than becoming unset");
                var go=new GameObject("Controlled actual ranking page status");var players=go.AddComponent<OnlinePlayersPage82>();var teams=go.AddComponent<OnlineTeamsPage82>();
                try{
                    players.ConfigureForVerification(art,session,_=>{});teams.ConfigureForVerification(teamArt,session,_=>{});
                    var hidden=BindingFlags.NonPublic|BindingFlags.Instance;typeof(OnlinePlayersPage82).GetField("regional",hidden).SetValue(players,true);typeof(OnlineTeamsPage82).GetField("regional",hidden).SetValue(teams,true);typeof(OnlineTeamsPage82).GetField("tab",hidden).SetValue(teams,2);
                    var pv=(OnlinePlayersView82)typeof(OnlinePlayersPage82).GetMethod("View",hidden).Invoke(players,null);var tv=(OnlineTeamsView82)typeof(OnlineTeamsPage82).GetMethod("View",hidden).Invoke(teams,null);
                    Check(!pv.countryLoaded&&pv.status==OnlinePlayersText82.T("Offline"),"Actual player page promotes country-read failure");Check(!tv.countryLoaded&&tv.status==OnlineTeamsText82.T("Offline"),"Actual team page promotes country-read failure");
                    Check(OnlinePlayersLayout82.Build(420,900,pv).chrome.elements.Any(v=>v.id=="online-players-status"&&v.text==OnlinePlayersText82.T("Offline")),"Player offline status is visible without a country picker");
                    Check(OnlineTeamsLayout82.Build(420,900,tv).content.elements.Any(v=>v.id=="online-team-country-required"&&v.text.Replace("\n"," ")==OnlineTeamsText82.T("Unavailable")),"Team offline body does not pretend no country selected");
                }finally{UnityEngine.Object.DestroyImmediate(go);}
                Check(session.RefreshRegion(),"Known unset country fetch");CompleteControlled(client,RegionJson(player,""));Check(session.Snapshot<SocialRegion89>(SocialPane82.Region)?.regionCode==""&&session.RankingStatus(SocialPane82.RegionalRanks).state==SocialViewState82.NotLoaded,"Successful explicit unset is distinct from network failure");
                Check(session.RefreshRegion(),"Known country fetch");CompleteControlled(client,RegionJson(player,"RU"));SeedRanks(session,client,player);
                string command=Guid.NewGuid().ToString("N");Check(session.SetRegion(command,"US"),"Country update submitted with durable intent");CompleteControlled(client,null,"SocialNetworkUnavailable",true);Check(session.PendingCommand?.commandId==command,"Uncertain country update retains exact intent");
                Check(session.ResumePending(),"Explicit retry of country intent");CompleteControlled(client,RegionJson(player,"US"));Check(session.PendingCommand==null&&session.Snapshot<SocialRegion89>(SocialPane82.Region)==null,"Recovered country mutation requires fresh country read");RanksAbsent(session,"Recovered country intent");
                Check(session.RefreshRegion(),"Reload after recovered country mutation");CompleteControlled(client,RegionJson(player,"RU"));SeedRanks(session,client,player);
                command=Guid.NewGuid().ToString("N");Check(session.SetLeaderboardConsent(command,false),"Privacy update submitted");CompleteControlled(client,null,"SocialNetworkUnavailable",true);Check(session.PendingCommand?.commandId==command,"Uncertain privacy update retained");
                Check(session.ReconcilePending(),"Read committed privacy receipt");CompleteControlled(client,JsonUtility.ToJson(new SocialOperationReceipt82{commandId=command,operation="social.profile.consent",status="Committed",receiptScope="owner_operation_receipt",payloadDigest=IdentityProtocol82.Sha("controlled-normalized-receipt"),digestScope="server_normalized_model_not_client_json",response=new SocialMutation82{playerId=player,displayName="Fixture",completedLevels=1,leaderboardOptIn=false}}));
                Check(session.PendingCommand==null,"Confirmed privacy receipt clears exact intent");RanksAbsent(session,"Committed privacy reconciliation");Check(session.Snapshot<SocialRegion89>(SocialPane82.Region)?.regionCode=="RU","Consent recovery does not erase unrelated country");
                Check(session.RefreshRegion(),"Delayed country read submitted under old owner");ownerGeneration++;access=new SocialAccess82(new string('6',32),IdentityProtocol82.NewSecret());CompleteControlled(client,RegionJson(player,"US"));
                Check(session.PlayerId==null&&session.Snapshot<SocialRegion89>(SocialPane82.Region)==null,"Delayed region reply cannot cross account generation");
                Check(client.VerificationRequests==0,"Controlled callbacks did not issue real HTTP");
            }
            foreach(var routine in routines)(routine as IDisposable)?.Dispose();
        }
    }
}
#endif
