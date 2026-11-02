using System;
using HeartOfTheRain.App.OnlineSocial;
using UnityEngine;

namespace HeartOfTheRain.App.Profile {
    // Server metadata only. This controller never writes appearance preferences,
    // campaign state, inventory or wallet balances.
    public sealed class ServerProfileController83:IDisposable {
        readonly SocialBackendClient82 client;readonly IDisposable store;readonly Func<long> owner;readonly long generation;
        SocialProfile82 profile;SocialRecords82 records;bool busy,closed;string error;
        public event Action Changed;
        public ServerProfileController83(SocialBackendClient82 client,IDisposable ownedStore=null,Func<long> ownerGeneration=null){
            this.client=client??throw new ArgumentNullException(nameof(client));store=ownedStore;owner=ownerGeneration;generation=owner==null?0:owner();
        }
        static T Copy<T>(T value) where T:class=>value==null?null:JsonUtility.FromJson<T>(JsonUtility.ToJson(value));
        bool Active(){
            if(closed)return false;bool valid;try{valid=client.Configured&&(owner==null||owner()==generation);}catch(Exception){valid=false;}
            if(valid)return true;profile=null;records=null;busy=false;error="ProfileOwnerChanged";client.Cancel();return false;
        }
        public SocialProfile82 Profile=>Active()?Copy(profile):null;
        public SocialRecords82 Records=>Active()?Copy(records):null;
        public bool Busy=>busy||client.Busy;
        public string Error=>error;
        public SocialPendingCommand82 Pending {get{if(!Active())return null;try{return client.PendingCommand;}catch(Exception){return null;}}}
        public bool PendingRename=>Pending?.operation=="profile.name";
        void Notify(){var listeners=Changed;if(listeners==null)return;foreach(Action listener in listeners.GetInvocationList())try{listener();}catch(Exception){}}
        void Fail(string why,Action<bool,string> done){
            busy=false;error=why??"ProfileServiceUnavailable";
            if(error=="SocialHttp401"||error=="SocialHttp410"||error=="ProfileOwnerChanged"){profile=null;records=null;}
            Notify();done?.Invoke(false,error);
        }
        public bool Refresh(Action<bool,string> done=null){
            if(!Active()||Busy)return false;busy=true;error=null;Notify();
            client.GetProfile(client.PlayerId,reply=>{
                if(!Active()){Fail("ProfileOwnerChanged",done);return;}
                if(reply==null||!reply.Succeeded){Fail(reply?.error,done);return;}
                var received=Copy(reply.value);
                client.GetRecords(0,100,result=>{
                    if(!Active()){Fail("ProfileOwnerChanged",done);return;}
                    if(result==null||!result.Succeeded){Fail(result?.error,done);return;}
                    if(result.value.completedLevels!=received.completedLevels){Fail("ProfileProgressChanged",done);return;}
                    profile=received;records=Copy(result.value);busy=false;error=null;Notify();done?.Invoke(true,null);
                });
            });return true;
        }
        public bool Rename(string name,Action<bool,string> done=null){
            if(!Active()||Busy||profile==null)return false;
            var pending=Pending;if(pending!=null&&pending.operation!="profile.name"){Fail("AnotherSocialActionNeedsConfirmation",done);return false;}
            if(pending==null){string clean,why;if(!ProfileRules.TryName(name,out clean,out why)){Fail(why,done);return false;}name=clean;}
            busy=true;error=null;Notify();
            Action<SocialReply82<SocialMutation82>> completed=reply=>{
                if(!Active()){Fail("ProfileOwnerChanged",done);return;}
                if(reply==null||!reply.Succeeded){Fail(reply?.error,done);return;}
                if(reply.value.playerId!=client.PlayerId){Fail("ProfileOwnerChanged",done);return;}
                // Preserve the server's opt-in value. A rename is never an
                // implicit leaderboard consent or an appearance-store write.
                profile=new SocialProfile82{playerId=reply.value.playerId,displayName=reply.value.displayName,completedLevels=reply.value.completedLevels,leaderboardOptIn=reply.value.leaderboardOptIn};
                busy=false;error=null;Notify();done?.Invoke(true,null);
            };
            if(pending!=null)client.ResumePending(completed);else client.UpdateName(Guid.NewGuid().ToString("N"),name,completed);
            return true;
        }
        public void Dispose(){if(closed)return;closed=true;busy=false;profile=null;records=null;client.Dispose();store?.Dispose();Changed=null;}
    }
}
