using System;
using System.Text;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;

namespace HeartOfTheRain.App.ServerGameplay {
    // The existing identity protocol is unchanged. Its encrypted credential
    // document additionally binds the explicitly selected server origin here.
    public sealed class OriginBoundIdentityStore82 : IProtectedSessionStore82 {
        [Serializable] sealed class Envelope { public int version=1; public string origin,payload; }
        readonly IProtectedSessionStore82 inner; readonly string origin;
        readonly UTF8Encoding utf8=new UTF8Encoding(false,true); bool closed;
        public OriginBoundIdentityStore82(IProtectedSessionStore82 store,string canonicalOrigin) {
            inner=store??throw new ArgumentNullException(nameof(store)); origin=canonicalOrigin;
            if(string.IsNullOrEmpty(origin))throw new ArgumentException("ExplicitIdentityOriginRequired");
        }
        byte[] Decode(byte[] raw) {
            if(raw==null)return null;
            var value=JsonUtility.FromJson<Envelope>(utf8.GetString(raw));
            if(value==null||value.version!=1||value.origin!=origin||value.payload==null||JsonUtility.ToJson(value)!=utf8.GetString(raw))throw new InvalidOperationException("ProtectedIdentityOriginMismatch");
            byte[] plain=Convert.FromBase64String(value.payload);
            if(plain.Length<1||Convert.ToBase64String(plain)!=value.payload)throw new InvalidOperationException("InvalidProtectedIdentityEnvelope");return plain;
        }
        void Alive(){if(closed)throw new ObjectDisposedException(nameof(OriginBoundIdentityStore82));}
        public byte[] Read(){Alive();return Decode(inner.Read());}
        public void CompareExchange(string expectedDigest,byte[] replacement) {
            Alive();byte[] before=inner.Read(),plain=Decode(before);
            if((plain==null?"":IdentityProtocol82.Sha(plain))!=expectedDigest)throw new InvalidOperationException("ProtectedIdentityRevisionConflict");
            byte[] next=replacement==null?null:utf8.GetBytes(JsonUtility.ToJson(new Envelope{origin=origin,payload=Convert.ToBase64String(replacement)}));
            inner.CompareExchange(before==null?"":IdentityProtocol82.Sha(before),next);
        }
        public void Dispose(){if(closed)return;closed=true;inner.Dispose();}
    }
}
