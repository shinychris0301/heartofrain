using System.Collections.Generic;
using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.AccountDesign {
    public static class AccountText {
        static readonly Dictionary<string,string[]> Words=new Dictionary<string,string[]> {
            {"saveTitle",new[]{"Save your journey","Guarda tu aventura","Sauvegardez votre aventure","Sichere deine Reise","Сохраните путешествие"}},
            {"saveIntro",new[]{"Keep your progress safe and continue on another device.","Protege tu progreso y continúa en otro dispositivo.","Protégez votre progression et continuez sur un autre appareil.","Bewahre deinen Fortschritt und spiele auf einem anderen Gerät weiter.","Сохраните прогресс и продолжайте на другом устройстве."}},
            {"apple",new[]{"Continue with Apple","Continuar con Apple","Continuer avec Apple","Mit Apple fortfahren","Продолжить с Apple"}},
            {"google",new[]{"Continue with Google","Continuar con Google","Continuer avec Google","Mit Google fortfahren","Продолжить с Google"}},
            {"vk",new[]{"Sign up with VK","Registrarse con VK","S’inscrire avec VK","Mit VK registrieren","Регистрация через VK"}},
            {"promise",new[]{"Your levels, boosters, and chosen avatar stay with you.","Conserva tus niveles, potenciadores y avatar.","Conservez vos niveaux, vos boosters et votre avatar.","Deine Level, Booster und dein Avatar bleiben erhalten.","Ваши уровни, усилители и аватар останутся с вами."}},
            {"notNow",new[]{"Not now","Ahora no","Plus tard","Nicht jetzt","Не сейчас"}},
            {"accountTitle",new[]{"Your account","Tu cuenta","Votre compte","Dein Konto","Ваш аккаунт"}},
            {"saved",new[]{"Journey saved","Aventura guardada","Aventure sauvegardée","Reise gespeichert","Прогресс сохранён"}},
            {"connected",new[]{"Connected","Conectada","Connecté","Verbunden","Подключено"}},
            {"cloud",new[]{"Cloud save","Guardado en la nube","Sauvegarde cloud","Cloud-Speicher","Облачное сохранение"}},
            {"continue",new[]{"Continue","Continuar","Continuer","Weiter","Продолжить"}},
            {"keep",new[]{"Keep playing this journey","Seguir con esta aventura","Continuer cette aventure","Diese Reise weiterspielen","Продолжить эту игру"}},
            {"offlineTitle",new[]{"You’re offline","Sin conexión","Vous êtes hors ligne","Du bist offline","Нет подключения"}},
            {"offlineIntro",new[]{"You’re offline. Your progress stays saved on this device; cloud saving is not available yet.","Sin conexión. Tu progreso sigue guardado en este dispositivo; el guardado en la nube aún no está disponible.","Vous êtes hors ligne. Votre progression reste enregistrée sur cet appareil ; la sauvegarde dans le cloud n’est pas encore disponible.","Du bist offline. Dein Fortschritt bleibt auf diesem Gerät gespeichert; Cloud-Speichern ist noch nicht verfügbar.","Нет подключения. Прогресс сохраняется на этом устройстве; облачное сохранение пока недоступно."}},
            {"retry",new[]{"Try again","Reintentar","Réessayer","Erneut versuchen","Повторить"}},
            {"errorTitle",new[]{"Couldn’t connect","No se pudo conectar","Connexion impossible","Verbindung fehlgeschlagen","Не удалось подключиться"}},
            {"errorIntro",new[]{"Sign-in did not finish. Your current journey has not changed.","No se completó el inicio de sesión. Tu aventura actual no ha cambiado.","La connexion n’a pas abouti. Votre aventure actuelle n’a pas changé.","Die Anmeldung wurde nicht abgeschlossen. Deine aktuelle Reise ist unverändert.","Вход не завершён. Текущее путешествие не изменилось."}},
            {"close",new[]{"Close","Cerrar","Fermer","Schließen","Закрыть"}},
            {"saving",new[]{"Connecting…","Conectando…","Connexion…","Verbindung läuft…","Подключение…"}},
            {"copy",new[]{"Copy player ID","Copiar ID de jugador","Copier l’identifiant","Spieler-ID kopieren","Копировать ID игрока"}},
            {"copied",new[]{"Copied","Copiado","Copié","Kopiert","Скопировано"}},
            {"saveProgress",new[]{"Save Progress","Guardar progreso","Sauvegarder","Fortschritt speichern","Сохранить прогресс"}},
            {"saveLocalStatus",new[]{"Saved on this device","Guardado en este dispositivo","Sauvegardé sur cet appareil","Auf diesem Gerät gespeichert","Сохранено на этом устройстве"}},
            {"saveCloudStatus",new[]{"Connected · Journey saved","Cuenta vinculada · Aventura guardada","Compte lié · Aventure sauvegardée","Konto verbunden · Abenteuer gespeichert","Аккаунт привязан · Прогресс сохранён"}},
            {"linkUnavailable",new[]{"Account linking is not available yet. Your journey stays on this device.","La vinculación de cuentas aún no está disponible. Tu aventura sigue en este dispositivo.","La liaison de compte est indisponible pour le moment. Votre aventure reste sur cet appareil.","Die Kontoverknüpfung ist noch nicht verfügbar. Dein Abenteuer bleibt auf diesem Gerät.","Привязка аккаунта пока недоступна. Ваш прогресс остаётся на этом устройстве."}},
            {"syncPending",new[]{"Waiting to sync","Esperando sincronización","En attente de synchronisation","Synchronisierung ausstehend","Ожидание синхронизации"}},
            {"syncFailed",new[]{"Sync failed. Your local journey is unchanged.","La sincronización falló. Tu aventura local no ha cambiado.","Échec de synchronisation. Votre aventure locale est inchangée.","Synchronisierung fehlgeschlagen. Dein lokales Abenteuer ist unverändert.","Синхронизация не удалась. Прогресс на устройстве не изменён."}},
            {"localUnverified",new[]{"Local save could not be verified. Please try again.","No se pudo verificar la partida local. Inténtalo de nuevo.","Impossible de vérifier la sauvegarde locale. Réessayez.","Lokaler Spielstand konnte nicht geprüft werden. Bitte erneut versuchen.","Не удалось проверить локальное сохранение. Повторите попытку."}},
            {"saveUnavailable",new[]{"Save unavailable","Guardado no disponible","Sauvegarde indisponible","Speichern nicht verfügbar","Сохранение недоступно"}},
            {"syncFailedBadge",new[]{"Sync failed","Error de sincronización","Échec de synchronisation","Synchronisierung fehlgeschlagen","Ошибка синхронизации"}},
        };
        public static string T(string key){if(key!=null&&key.StartsWith("server",System.StringComparison.Ordinal))return HeartOfTheRain.App.ServerAccount.ServerAccountText83.T(key);string[] v;return Words.TryGetValue(key,out v)?v[GameLocale.Current]:key;}
    }
}
