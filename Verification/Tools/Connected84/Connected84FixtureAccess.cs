using System;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.EndLevel;
using HeartOfTheRain.M47;

// Fixture-only accessors. These files are added ONLY to the isolated copied
// project; no ordinary runtime source or visibility is changed.
namespace HeartOfTheRain.App.ServerGameplay {
    public sealed partial class ServerGameSession {
        internal string Connected84IdentityKeyFingerprint=>identity?.View.keyFingerprint;
        internal string Connected84BackupForProtectedStore(){
            if(!Ready||Busy||identity==null||identity.View.hasPending)throw new InvalidOperationException("FixtureBackupUnavailable");
            return identity.RecoverySecretForExplicitBackup();
        }
    }
}
namespace HeartOfTheRain.App.PreLevel {
    public sealed partial class HomeLevelFlow {
        internal GameplayScreen Connected84ActualBoard=>gameplay;
        internal void Connected84ExplicitForfeit(){
            if(!gameplay||!gameplay.Ready||gameplay.Busy)throw new InvalidOperationException("FixtureBoardNotIdle");
            var exit=new EndLevelSession();EndLevelDecision decision;
            if(!exit.Open(gameplay.CurrentLevel,home.State.lives)||!exit.Confirm(home.State.lives,out decision))throw new InvalidOperationException("FixtureExplicitDecisionInvalid");
            ConfirmExit(gameplay,decision);
        }
    }
}
