using System;
using System.Collections.Generic;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.App.PreLevel
{
    // Presentation descriptors only. No attempt, wallet, inventory or save writes.
    public sealed class ObstacleIntroductionCard
    {
        public readonly string Family, ArtKey;public readonly int FirstLevel;
        readonly string[] titles, instructions;
        internal ObstacleIntroductionCard(string family,string artKey,int firstLevel,string[] titles,string[] instructions)
        {Family=family;ArtKey=artKey;FirstLevel=firstLevel;this.titles=titles;this.instructions=instructions;}
        static int Locale(int locale)=>locale>=0&&locale<5?locale:4;
        public string Title(int locale)=>titles[Locale(locale)];
        public string Instruction(int locale)=>instructions[Locale(locale)];
    }

    // A monotonic presentation clock only; it never starts/settles an attempt.
    // Sampling the pause/focus transition anchors prevents background catch-up.
    public sealed class ObstacleIntroductionClock
    {
        public const double RevealSeconds=.18, VisibleSeconds=1.5;
        double anchor,elapsed;bool sampled,foreground;
        public double ForegroundSeconds=>elapsed;
        public double FullyVisibleSeconds=>Math.Max(0,elapsed-RevealSeconds);
        public float RevealProgress=>(float)Math.Max(0,Math.Min(1,elapsed/RevealSeconds));
        public bool Finished=>elapsed>=RevealSeconds+VisibleSeconds;
        public void Reset(double now,bool visible)
        {anchor=now;elapsed=0;sampled=true;foreground=visible;}
        public void Sample(double now,bool visible)
        {
            if(double.IsNaN(now)||double.IsInfinity(now)||now<0)return;
            if(!sampled){Reset(now,visible);return;}
            double delta=Math.Max(0,now-anchor);anchor=Math.Max(anchor,now);
            if(foreground)elapsed+=delta;
            foreground=visible;
        }
    }

    public static class ObstacleIntroductionRules
    {
        // Locale order matches the existing stable indices: English, Spanish,
        // French, German, Russian. Artwork keys already exist in M48GameplayUIAssets.
        static readonly ObstacleIntroductionCard[] Cards={
            new ObstacleIntroductionCard("crate","crate_1",1,
                new[]{"Supply crates","Cajas de suministros","Caisses de provisions","Vorratskisten","Ящики с припасами"},
                new[]{"Match beside crates or use power-ups to break their layers.",
                    "Combina junto a las cajas o usa potenciadores para romper sus capas.",
                    "Alignez des pièces près des caisses ou utilisez des bonus pour les briser.",
                    "Bilde Kombinationen neben Kisten oder nutze Extras, um ihre Schichten zu entfernen.",
                    "Собирайте комбинации рядом с ящиками или разбивайте их усилителями."}),
            new ObstacleIntroductionCard("moss","moss_1",1,
                new[]{"Well overgrowth","Maleza del pozo","Végétation du puits","Brunnenbewuchs","Заросли у колодца"},
                new[]{"Match beside the overgrowth or hit it with power-ups to clear it.",
                    "Combina junto a la maleza o golpéala con potenciadores para quitarla.",
                    "Alignez des pièces près de la végétation ou frappez-la avec des bonus.",
                    "Bilde Kombinationen neben dem Bewuchs oder entferne ihn mit Extras.",
                    "Собирайте комбинации рядом с зарослями или убирайте их усилителями."}),
            new ObstacleIntroductionCard("stone","stone_1",7,
                new[]{"Rune stones","Piedras rúnicas","Pierres runiques","Runensteine","Рунные камни"},
                new[]{"Match beside the stones or use power-ups to clear their layers.",
                    "Combina junto a las piedras o usa potenciadores para quitar sus capas.",
                    "Alignez des pièces près des pierres ou utilisez des bonus pour les briser.",
                    "Bilde Kombinationen neben Steinen oder entferne ihre Schichten mit Extras.",
                    "Собирайте комбинации рядом с камнями или разбивайте их слои усилителями."}),
            new ObstacleIntroductionCard("pail","pail_Full",10,
                new[]{"Restoration jars","Jarras de restauración","Jarres de restauration","Wiederaufbaukrüge","Сосуды восстановления"},
                new[]{"Clear tiles below a restoration jar to guide it to a marked exit.",
                    "Quita las fichas bajo la jarra para llevarla hasta una salida marcada.",
                    "Retirez les pièces sous la jarre pour la guider vers une sortie indiquée.",
                    "Entferne Steine unter dem Krug, um ihn zu einem markierten Ausgang zu bringen.",
                    "Убирайте фишки под сосудом, чтобы опустить его к отмеченному выходу."}),
            new ObstacleIntroductionCard("case","case_1",14,
                new[]{"Sealed supply cases","Cajas selladas","Caisses scellées","Versiegelte Kisten","Запечатанные ящики"},
                new[]{"Break sealed cases with power-ups or tools. Nearby matches cannot damage them.",
                    "Rompe las cajas selladas con potenciadores o herramientas, no con combinaciones cercanas.",
                    "Brisez ces caisses avec des bonus ou des outils. Les alignements voisins sont sans effet.",
                    "Öffne versiegelte Kisten mit Extras oder Werkzeugen. Benachbarte Kombinationen helfen nicht.",
                    "Разбивайте запечатанные ящики усилителями или инструментами. Комбинации рядом не помогают."}),
            new ObstacleIntroductionCard("gate","gate_1",18,
                new[]{"Water sluices","Compuertas","Écluses","Wasserschleusen","Водяные затворы"},
                new[]{"Match water drops beside a sluice, or hit it with power-ups, to open it.",
                    "Combina gotas de agua junto a la compuerta o golpéala con potenciadores para abrirla.",
                    "Alignez des gouttes près de l’écluse ou frappez-la avec des bonus pour l’ouvrir.",
                    "Kombiniere Wassertropfen neben der Schleuse oder öffne sie mit Extras.",
                    "Собирайте капли воды рядом с затвором или открывайте его усилителями."}),
            new ObstacleIntroductionCard("crystal","crystalIcon",21,
                new[]{"Storm Crystals","Cristales de tormenta","Cristaux de tempête","Sturmkristalle","Грозовые кристаллы"},
                new[]{"Nearby matches and power-ups remove one section at a time. Clear the whole column.",
                    "Las combinaciones cercanas y los potenciadores quitan una sección. Despeja toda la columna.",
                    "Les alignements voisins et les bonus retirent une section. Détruisez toute la colonne.",
                    "Benachbarte Kombinationen und Extras entfernen je einen Abschnitt. Räume die ganze Säule ab.",
                    "Комбинации рядом и усилители убирают по одной секции. Разрушьте весь столб."}),
            new ObstacleIntroductionCard("pod","pod_3",28,
                new[]{"Water Spirit Pods","Cápsulas de espíritus","Cocons d’esprits d’eau","Wassergeistkapseln","Коконы водяных духов"},
                new[]{"Match beside the pod or use power-ups to release the water spirit inside.",
                    "Combina junto a la cápsula o usa potenciadores para liberar al espíritu de agua.",
                    "Alignez des pièces près du cocon ou utilisez des bonus pour libérer l’esprit d’eau.",
                    "Bilde Kombinationen neben der Kapsel oder befreie den Wassergeist mit Extras.",
                    "Собирайте комбинации рядом с коконом или используйте усилители, чтобы освободить духа."}),
            new ObstacleIntroductionCard("cabinet","cabinet_5",36,
                new[]{"Rainlight Cabinets","Armarios de luz de lluvia","Armoires de lumière","Regenlichtschränke","Шкафы дождевого света"},
                new[]{"Match beside the cabinet or use power-ups to open it and release its rainlights.",
                    "Combina junto al armario o usa potenciadores para abrirlo y liberar sus luces.",
                    "Alignez des pièces près de l’armoire ou utilisez des bonus pour libérer ses lumières.",
                    "Bilde Kombinationen neben dem Schrank oder öffne ihn mit Extras und befreie die Regenlichter.",
                    "Собирайте комбинации рядом со шкафом или используйте усилители, чтобы выпустить дождевой свет."})
        };

        public static ObstacleIntroductionCard[] All=>(ObstacleIntroductionCard[])Cards.Clone();

        // Cheap launch path. The native campaign audit below verifies this
        // explicit nine-family index against every actual live level asset.
        public static ObstacleIntroductionCard[] Plan(LevelData current,int completedLevels,bool retry,bool previouslyStarted)
        {
            if(current==null||current.globalLevel<1||retry||previouslyStarted
                ||current.globalLevel<=Math.Max(0,completedLevels))return new ObstacleIntroductionCard[0];
            var present=new HashSet<string>(StringComparer.Ordinal);
            if(current.obstacles!=null)foreach(var obstacle in current.obstacles)
                if(obstacle!=null&&obstacle.family!=null)present.Add(obstacle.family);
            var result=new List<ObstacleIntroductionCard>();
            foreach(var card in Cards)if(card.Family!="crate"&&card.Family!="moss"
                &&card.FirstLevel==current.globalLevel&&present.Contains(card.Family))result.Add(card);
            return result.ToArray();
        }

        // The caller supplies real campaign data and durable progression/attempt
        // history. The current Reserved attempt is not a previously started one.
        // Crates and moss are covered by the existing first-time match tutorial.
        public static ObstacleIntroductionCard[] Plan(LevelData current,IEnumerable<LevelData> campaign,
            int completedLevels,bool retry,bool previouslyStarted)
        {
            if(current==null||campaign==null||current.globalLevel<1||retry||previouslyStarted
                ||current.globalLevel<=Math.Max(0,completedLevels))return new ObstacleIntroductionCard[0];
            var present=new HashSet<string>(StringComparer.Ordinal);
            if(current.obstacles!=null)foreach(var obstacle in current.obstacles)
                if(obstacle!=null&&obstacle.family!=null)present.Add(obstacle.family);
            var first=new Dictionary<string,int>(StringComparer.Ordinal);
            foreach(var level in campaign)
            {
                if(level==null||level.globalLevel<1||level.obstacles==null)continue;
                foreach(var obstacle in level.obstacles)
                {
                    if(obstacle==null||obstacle.family==null)continue;
                    int before;if(!first.TryGetValue(obstacle.family,out before)||level.globalLevel<before)
                        first[obstacle.family]=level.globalLevel;
                }
            }
            var result=new List<ObstacleIntroductionCard>();
            foreach(var card in Cards)
            {
                int earliest;
                if(card.Family!="crate"&&card.Family!="moss"&&present.Contains(card.Family)
                    &&first.TryGetValue(card.Family,out earliest)&&earliest==current.globalLevel)result.Add(card);
            }
            return result.ToArray();
        }
    }
}
