using System;
using UnityEngine;

namespace HeartOfTheRain.App.OnlineIdentity
{
    // One explicit owner supplies an isolated scope. Loading the assembly does
    // not touch the Keystore, normal profiles or any credential file.
    public sealed class AndroidDeviceIdentity82 : IDeviceIdentityKey82, IProtectedSessionStore82
    {
#if UNITY_ANDROID && !UNITY_EDITOR
        AndroidJavaObject bridge;
#endif
        bool disposed;
        public bool IsAndroidKeystore => true;
        public AndroidDeviceIdentity82(string scope)
        {
#if UNITY_ANDROID && !UNITY_EDITOR
            using(var version = new AndroidJavaClass("android.os.Build$VERSION")) if(version.GetStatic<int>("SDK_INT") < 26) throw new NotSupportedException("IdentityApi26Required");
            using(var unity = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
            using(var activity = unity.GetStatic<AndroidJavaObject>("currentActivity"))
            using(var context = activity.Call<AndroidJavaObject>("getApplicationContext")) bridge = new AndroidJavaObject("com.heartoftherain.identity.DeviceIdentity82", context, scope);
#else
            throw new NotSupportedException("AndroidKeystoreUnavailableOnThisPlatform");
#endif
        }
        void Alive() { if(disposed) throw new ObjectDisposedException(nameof(AndroidDeviceIdentity82)); }
        public byte[] PublicSpkiDer() {
            Alive();
#if UNITY_ANDROID && !UNITY_EDITOR
            return Convert.FromBase64String(bridge.Call<string>("publicKeySpki"));
#else
            throw new NotSupportedException();
#endif
        }
        public byte[] SignSha256Der(byte[] message) {
            Alive(); if(message == null || message.Length < 1 || message.Length > 4096) throw new ArgumentException("InvalidIdentityMessage");
#if UNITY_ANDROID && !UNITY_EDITOR
            return Convert.FromBase64String(bridge.Call<string>("signSha256Der", Convert.ToBase64String(message)));
#else
            throw new NotSupportedException();
#endif
        }
        public byte[] Read() {
            Alive();
#if UNITY_ANDROID && !UNITY_EDITOR
            string value = bridge.Call<string>("readProtected"); return value == null ? null : Convert.FromBase64String(value);
#else
            throw new NotSupportedException();
#endif
        }
        public bool VerifySha256Der(byte[] message, byte[] signature) {
            Alive(); if(message == null || message.Length < 1 || message.Length > 4096 || signature == null || signature.Length < 8 || signature.Length > 80) return false;
#if UNITY_ANDROID && !UNITY_EDITOR
            return bridge.Call<bool>("verifySha256Der", Convert.ToBase64String(message), Convert.ToBase64String(signature));
#else
            throw new NotSupportedException();
#endif
        }
        public void CompareExchange(string expectedDigest, byte[] replacement) {
            Alive();
#if UNITY_ANDROID && !UNITY_EDITOR
            bridge.Call("compareExchange", expectedDigest, replacement == null ? null : Convert.ToBase64String(replacement));
#else
            throw new NotSupportedException();
#endif
        }
        public bool[] Diagnostics() {
            Alive();
#if UNITY_ANDROID && !UNITY_EDITOR
            return bridge.Call<bool[]>("diagnostics");
#else
            throw new NotSupportedException();
#endif
        }
        public void Dispose() {
            if(disposed) return; disposed = true;
#if UNITY_ANDROID && !UNITY_EDITOR
            bridge?.Call("close"); bridge?.Dispose(); bridge = null;
#endif
        }
    }
}
