using System.Collections.Generic;
using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.Profile
{
    public static class ProfileText
    {
        // en/es/fr/de/ru; player-entered names never pass through this catalog.
        static readonly Dictionary<string,string[]> words=new Dictionary<string,string[]>{
            {"Profile",new[]{"Profile","Perfil","Profil","Profil","Профиль"}},
            {"Avatars",new[]{"Avatars","Avatares","Avatars","Avatare","Аватары"}},
            {"Banners",new[]{"Banners","Fondos","Bannières","Banner","Фоны"}},
            {"Frames",new[]{"Frames","Marcos","Cadres","Rahmen","Рамки"}},
            {"Stats",new[]{"Stats","Datos","Stats","Statistik","Данные"}},
            {"No team",new[]{"No team","Sin equipo","Sans équipe","Kein Team","Без команды"}},
            {"Join",new[]{"Join","Unirse","Rejoindre","Beitreten","Вступить"}},
            {"Level",new[]{"Level","Nivel","Niveau","Level","Уровень"}},
            {"Choose your avatar",new[]{"Choose your avatar","Elige tu avatar","Choisissez votre avatar","Avatar auswählen","Выберите аватар"}},
            {"Choose your banner",new[]{"Choose your banner","Elige tu fondo","Choisissez votre bannière","Banner auswählen","Выберите баннер"}},
            {"Choose your frame",new[]{"Choose your frame","Elige tu marco","Choisissez votre cadre","Rahmen auswählen","Выберите рамку"}},
            {"Your journey",new[]{"Your journey","Tu aventura","Votre aventure","Deine Reise","Ваше путешествие"}},
            {"Selected",new[]{"Selected","Seleccionado","Sélectionné","Ausgewählt","Выбрано"}},
            {"Change name",new[]{"Change name","Cambiar nombre","Changer de nom","Namen ändern","Изменить имя"}},
            {"Name hint",new[]{"Choose a name other players will see.","Elige el nombre que verán los demás.","Choisissez le nom visible par les autres.","Wähle den Namen, den andere sehen.","Выберите имя, которое увидят другие."}},
            {"Save",new[]{"Save","Guardar","Enregistrer","Speichern","Сохранить"}},
            {"Cancel",new[]{"Cancel","Cancelar","Annuler","Abbrechen","Отмена"}},
            {"Close",new[]{"Close","Cerrar","Fermer","Schließen","Закрыть"}},
            {"name-empty",new[]{"Please enter a name.","Introduce un nombre.","Saisissez un nom.","Bitte einen Namen eingeben.","Введите имя."}},
            {"name-long",new[]{"Use 20 characters or fewer.","Usa como máximo 20 caracteres.","Utilisez 20 caractères maximum.","Höchstens 20 Zeichen verwenden.","Используйте не более 20 символов."}},
            {"name-invalid",new[]{"Please use a single line of visible text.","Usa una sola línea de texto visible.","Utilisez une seule ligne de texte visible.","Bitte nur eine Zeile sichtbaren Text eingeben.","Введите одну строку видимого текста."}},
            {"save-failed",new[]{"Could not save. Please try again.","No se pudo guardar. Inténtalo de nuevo.","Échec de l’enregistrement. Réessayez.","Speichern fehlgeschlagen. Erneut versuchen.","Не удалось сохранить. Повторите попытку."}},
            {"selection-invalid",new[]{"This item is unavailable.","Este objeto no está disponible.","Cet élément est indisponible.","Dieses Element ist nicht verfügbar.","Этот предмет недоступен."}},
            {"Chapter",new[]{"Chapter","Capítulo","Chapitre","Kapitel","Глава"}},
            {"Chapter progress",new[]{"Chapter progress","Progreso del capítulo","Progression du chapitre","Kapitelfortschritt","Прогресс главы"}},
            {"Stars",new[]{"Stars","Estrellas","Étoiles","Sterne","Звёзды"}},
            {"Village",new[]{"Village Well","Pozo del pueblo","Puits du village","Dorfbrunnen","Деревенский колодец"}},
            {"Twilight",new[]{"Twilight","Crepúsculo","Crépuscule","Dämmerung","Сумерки"}},
            {"Lantern",new[]{"Lantern","Farol","Lanterne","Laterne","Фонарь"}},
            {"Raindrop",new[]{"Raindrop","Gota de lluvia","Goutte de pluie","Regentropfen","Капля дождя"}},
            {"Heart",new[]{"Heart","Corazón","Cœur","Herz","Сердце"}},
            {"Compass",new[]{"Compass","Brújula","Boussole","Kompass","Компас"}},
            {"Gold",new[]{"Gold","Oro","Or","Gold","Золото"}},
            {"Sapphire",new[]{"Sapphire","Zafiro","Saphir","Saphir","Сапфир"}},
            {"Ivory",new[]{"Ivory","Marfil","Ivoire","Elfenbein","Слоновая кость"}},
            {"RainkeeperGold",new[]{"Rainkeeper Gold","Oro del Guardián","Or du Gardien","Regenhüter Gold","Золото Хранителя"}},
            {"LanternSapphire",new[]{"Lantern Sapphire","Zafiro del Farol","Saphir Lanterne","Laternen-Saphir","Сапфир Фонаря"}},
            {"GardenIvory",new[]{"Garden Ivory","Marfil del Jardín","Ivoire du Jardin","Garten-Elfenbein","Слоновая кость сада"}}
        };
        public static string T(string key){string[] a;return words.TryGetValue(key,out a)?a[GameLocale.Current]:key;}
        public static IEnumerable<KeyValuePair<string,string[]>> Entries=>words;
    }
}
