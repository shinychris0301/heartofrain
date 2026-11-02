using System;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.Profile {
    public static class DirectEconomyMigration132 {
        public static PlayerProfile Create(RuStoreServerWallet wallet,bool sessionReady,bool pendingAttempt){
            if(!sessionReady||pendingAttempt||wallet==null||wallet.activeAttempt!=null||!Guid.TryParseExact(wallet.playerId,"N",out _)||
                wallet.starting==null||wallet.starting.Length!=4||wallet.tools==null||wallet.tools.Length!=4)
                throw new InvalidOperationException("DirectEconomyMigrationWaiting");
            var player=PlayerProfile.New(wallet.starting);player.playerId=wallet.playerId;
            player.coins=wallet.coins;player.stars=wallet.stars;player.lives=wallet.lives;player.maxLives=wallet.maxLives;
            player.completed=wallet.completed;player.currentLevel=wallet.currentLevel;player.tools=(int[])wallet.tools.Clone();
            player.livesRefillDueUnix=wallet.nextLifeAt;player.Validate();return player;
        }
    }
}
