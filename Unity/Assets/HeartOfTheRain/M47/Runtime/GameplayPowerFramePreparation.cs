using System;
using System.Collections;
using System.Collections.Generic;
using HeartOfTheRain.M46;
using UnityEngine;
namespace HeartOfTheRain.M47 {
    public sealed partial class GameplayScreen {
        M46AtlasBank powerPreparationOwner;
        Action<Sprite> powerPreparationGeometry;
        int queuePresentationPrefetches;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        [NonSerialized] public bool VerificationSkipTurnPreparation;
        bool verificationUseCheckpoint76Sampling;
        public bool VerificationUseCheckpoint76Sampling {
            get=>verificationUseCheckpoint76Sampling;
            set {verificationUseCheckpoint76Sampling=value;if(presentation!=null)presentation.VerificationUseCheckpoint76Sampling=value;}
        }
        public bool VerificationTurnPreparationPending=>queuePresentationPrefetches>0||bank!=null&&bank.PowerPreparationPending;
        public M46AtlasBank.PowerPreparationBatch VerificationLastPowerPreparationBatch=>bank==null?default(M46AtlasBank.PowerPreparationBatch):bank.LastPowerPreparationBatch;
#endif
        // Texture requests begin at the same point as the previous prefetcher.
        // Native sprite/quad preparation then runs ahead of later effects. It
        // never gates a swap, extends an animation or changes readiness rules.
        IEnumerator PrefetchQueuePresentation(HashSet<string> resources){
            var owner=bank;var target=effects;
            queuePresentationPrefetches++;
            try {
            var textures=owner.Prewarm(resources);
            try {while(textures.MoveNext())yield return textures.Current;}
            finally {(textures as IDisposable)?.Dispose();}
            if(owner!=bank||target!=effects||owner.LoadError!=null||!PresentationWarmupEnabled)yield break;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationSkipTurnPreparation)yield break;
#endif
            if(powerPreparationOwner!=owner){powerPreparationOwner=owner;powerPreparationGeometry=target.PrepareSprite;}
            yield return owner.WarmPowerFrames(resources,powerPreparationGeometry);
            }finally {if(owner==bank)queuePresentationPrefetches--;}
        }
    }
}
