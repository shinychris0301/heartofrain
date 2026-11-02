using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
namespace HeartOfTheRain.App.OnlineSocial {
 public sealed partial class SocialBackendClient82 {
  void MailRow111(Dictionary<string,object> row,string team) {
   Need(Id(Text(row,"messageId",32))&&Text(row,"teamId",32)==team);Number(row,"sequence",1);
   UserText(Text(row,"senderLabel",256,true),64,true);UserText(Text(row,"title",480),120);UserText(Text(row,"body",8000),2000,false,true);
   long sent=Number(row,"sentAtUtc",1),read=Number(row,"readAtUtc"),expiry=Number(row,"expiresAtUtc");Need(read==0||read>=sent);Need(expiry==0||expiry>=sent);
   long coins=Number(row,"rewardCoins",0,1000000),lives=Number(row,"rewardLives",0,5);string state=Text(row,"claimState",24),block=Text(row,"claimBlockedReason",40);bool can=Flag(row,"canClaim");
   Need(new[]{"None","Ready","CapacityBlocked","Claimed","Expired"}.Contains(state));Need(new[]{"None","FullLives","WalletMigrationRequired","WalletRefundReviewRequired"}.Contains(block));
   Need((state=="None")==(coins==0&&lives==0));Need(!can||state=="Ready"&&block=="None");
  }
  public void GetTeamMail111(string team,long before,Action<SocialReply82<SocialMailList111>> done) {
   if(!Input(done,()=>{Segment(team);Need(before>=0);}))return;
   Send("GET","/v1/teams/"+team+"/mail?limit=8"+(before>0?"&before="+before.ToString(CultureInfo.InvariantCulture):""),null,json=>Read<SocialMailList111>(json,row=>{
    Need(Text(row,"teamId",32)==team);Number(row,"serverUtc",1);Number(row,"unreadCount",0,int.MaxValue);long cursor=Number(row,"olderCursor");bool more=Flag(row,"hasOlder");long prev=before>0?before:long.MaxValue,last=0;var seen=new HashSet<string>(StringComparer.Ordinal);var items=Array(row,"messages",8);foreach(var item in items){var value=Obj(item);MailRow111(value,team);long seq=Number(value,"sequence",1);Need(seq<prev&&seen.Add(Text(value,"messageId",32)));prev=last=seq;}Need(cursor==(items.Count==0?0:last));Need(!more||items.Count>0);
   }),done);
  }
  public void GetTeamMailDetail111(string team,string id,Action<SocialReply82<SocialMailDetail111>> done) {
   if(!Input(done,()=>{Segment(team);Segment(id);}))return;
   Send("GET","/v1/teams/"+team+"/mail/"+id,null,json=>Read<SocialMailDetail111>(json,row=>{Number(row,"serverUtc",1);var value=Obj(SocialJson82.Field(row,"message"));MailRow111(value,team);Need(Text(value,"messageId",32)==id);}),done);
  }
  void MailReward111(Dictionary<string,object> value){Need(Id(Text(value,"messageId",32)));Number(value,"sequence",1);long sent=Number(value,"sentAtUtc",1),expiry=Number(value,"expiresAtUtc");Need(expiry==0||expiry>=sent);long coins=Number(value,"rewardCoins",0,1000000),lives=Number(value,"rewardLives",0,5);Need(coins>0||lives>0);string state=Text(value,"claimState",24),block=Text(value,"claimBlockedReason",40);bool can=Flag(value,"canClaim");Need(state=="Ready"||state=="CapacityBlocked");Need(new[]{"None","FullLives","WalletMigrationRequired","WalletRefundReviewRequired"}.Contains(block));Need(!can||state=="Ready"&&block=="None");}
  public void GetOwnedMail111(long after,Action<SocialReply82<SocialOwnedMail111>> done){if(!Input(done,()=>Need(after>=0)))return;Send("GET","/v1/mail/rewards/owned?after="+after.ToString(CultureInfo.InvariantCulture)+"&limit=8",null,json=>Read<SocialOwnedMail111>(json,row=>{Number(row,"serverUtc",1);long cursor=Number(row,"nextCursor"),previous=after;bool more=Flag(row,"hasMore");var seen=new HashSet<string>(StringComparer.Ordinal);var items=Array(row,"rewards",8);foreach(var item in items){var value=Obj(item);MailReward111(value);long sequence=Number(value,"sequence",1);Need(sequence>previous&&seen.Add(Text(value,"messageId",32)));previous=sequence;}Need(cursor==(items.Count==0?after:previous));Need(!more||items.Count>0);}),done);}
  public void ClaimOwnedMail111(string command,string id,Action<SocialReply82<SocialMutation82>> done)=>Mutate("mail.claim-owned","/v1/mail/rewards/"+id+"/claim",new Command{commandId=command},command,done);
  public void ReadTeamMail111(string command,string team,string id,Action<SocialReply82<SocialMutation82>> done)=>Mutate("mail.read","/v1/teams/"+team+"/mail/"+id+"/read",new Command{commandId=command},command,done);
  public void ClaimTeamMail111(string command,string team,string id,Action<SocialReply82<SocialMutation82>> done)=>Mutate("mail.claim","/v1/teams/"+team+"/mail/"+id+"/claim",new Command{commandId=command},command,done);
  void MailReceipt111(Dictionary<string,object> row,SocialPendingCommand82 pending){
   var parts=pending.path.Split('/');bool owned=pending.operation=="mail.claim-owned";Need(Text(row,"operation",24)==(owned?"mail.claim":pending.operation)&&Id(Text(row,"receiptId",32))&&Id(Text(row,"teamId",32))&&Text(row,"messageId",32)==parts[owned?4:5]&&(owned||Text(row,"teamId",32)==parts[3]));Number(row,"serverUtc",1);
   if(pending.operation=="mail.read"){Number(row,"readAtUtc",1);return;}
   string state=Text(row,"state",24);Need(state=="Claimed"||state=="CapacityBlocked");Number(row,"rewardCoins",0,1000000);Number(row,"rewardLives",0,5);Number(row,"walletRevision",1);Number(row,"coins",0,int.MaxValue);long max=Number(row,"maxLives",5,5);Number(row,"lives",0,max);Number(row,"nextLifeAt");
  }
 }
}
