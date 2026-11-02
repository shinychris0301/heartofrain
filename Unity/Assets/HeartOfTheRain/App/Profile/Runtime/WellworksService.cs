using System;
using System.Linq;
using UnityEngine;
namespace HeartOfTheRain.App.Profile {
    [Serializable] public sealed class WellworksMilestone {
        public int level;public RewardGrant grant=new RewardGrant();
    }
    [Serializable] public sealed class WellworksSchedule {
        public WellworksMilestone[] milestones=new WellworksMilestone[0];
        public void Validate(){
            if(milestones==null||milestones.Length>50)throw new InvalidOperationException("Invalid Wellworks schedule");
            int previous=0;foreach(var m in milestones){if(m==null||m.level<=previous||m.level>50||m.grant==null)throw new InvalidOperationException("Invalid Wellworks milestone");m.grant.Validate();if(m.grant.stars!=0)throw new InvalidOperationException("Wellworks cannot change story stars");int kinds=(m.grant.coins>0?1:0)+m.grant.starting.Count(v=>v>0)+m.grant.tools.Count(v=>v>0);if(kinds<1||kinds>3)throw new InvalidOperationException("Milestones require one to three reward types");previous=m.level;}
        }
        public WellworksSchedule Copy()=>JsonUtility.FromJson<WellworksSchedule>(JsonUtility.ToJson(this));
    }
    // Permanent Chapter 1 milestones. Keys deliberately exclude configuration
    // versions: updating quantities must never reopen an already claimed stage.
    public sealed class WellworksService {
        readonly ProfileService profile;readonly WellworksSchedule schedule;readonly bool enabled;
        public WellworksService(ProfileService profile,WellworksSchedule schedule,bool enabled){this.profile=profile??throw new ArgumentNullException(nameof(profile));if(schedule==null)throw new ArgumentNullException(nameof(schedule));schedule.Validate();this.schedule=schedule.Copy();this.enabled=enabled;}
        public bool Enabled=>enabled&&schedule.milestones.Length>0;
        public WellworksSchedule Schedule=>schedule.Copy();
        public static string Key(int level)=>"wellworks/chapter-1/"+level;
        public static bool Claimed(PlayerProfile p,int level)=>p.rewards.Any(r=>r.key==Key(level));
        public string Badge(PlayerProfile p){if(!Enabled)return "Unavailable";if(schedule.milestones.Any(m=>p.completed>=m.level&&!Claimed(p,m.level)))return "Ready";var next=schedule.milestones.FirstOrDefault(m=>!Claimed(p,m.level));return next==null?"✓":p.completed+"/"+next.level;}
        public RewardGrant Claim(int level){
            if(!Enabled)throw new InvalidOperationException("Wellworks rewards are unavailable");
            var m=schedule.milestones.FirstOrDefault(v=>v.level==level);if(m==null)throw new InvalidOperationException("Unknown Wellworks milestone");
            return profile.Change(p=>{
                // A persisted receipt remains final even when review quantities
                // change. Display its saved grant, never issue a replacement.
                if(Claimed(p,level))return null;
                if(p.completed<level)throw new InvalidOperationException("Milestone not reached");
                ProfileService.ApplyGrant(p,Key(level),"wellworks",m.grant);return m.grant.Copy();
            });
        }
    }
}
