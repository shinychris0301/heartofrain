namespace HeartOfTheRain.App.Localization
{
    // Story identity, unlocks and source attribution stay in JourneyCatalog.
    // Language changes select text only; English and missing entries use source text.
    public static class StoryLocale
    {
        public static string Title(int chapter, string source) { return Get(chapter, 0, source); }
        public static string Opening(int chapter, string source) { return Get(chapter, 1, source); }
        public static string Ending(int chapter, string source) { return Get(chapter, 2, source); }
        static string Get(int chapter, int field, string source)
        {
            int locale = GameLocale.Current - 1;
            if (locale < 0 || locale >= StoryLocaleCatalog.Chapters.Length || chapter < 1) return source;
            var chapters = StoryLocaleCatalog.Chapters[locale];
            if (chapter > chapters.Length) return source;
            var row = chapters[chapter - 1];
            return row == null || row.Length <= field || string.IsNullOrWhiteSpace(row[field]) ? source : row[field];
        }
    }
}
