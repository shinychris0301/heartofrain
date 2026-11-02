using System;
using System.Globalization;
using System.Linq;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;

namespace HeartOfTheRain.App.OnlineSocial
{
    // The connected Friends page uses the R3 card roles. Only received social
    // snapshots are rendered in a player build; the art-proof roster is Editor-only.
    public static class FriendsParity118
    {
        static int Locale => GameLocale.ResolveStored(GameLocale.Current);
        static string L(string en, string es, string fr, string de, string ru)
            => new[] { en, es, fr, de, ru }[Locale];
        static string T(string key) => OnlinePlayersText82.T(key);
        static string Num(long value) => value.ToString("N0", CultureInfo.GetCultureInfo(new[] { "en-US", "es-ES", "fr-FR", "de-DE", "ru-RU" }[Locale]));

        static HomeElement Add(HomeFrame f, string id, string kind, float x, float y, float w, float h, string parent = "")
        {
            var e = new HomeElement { id = id, kind = kind, x = x, y = y, width = w, height = h, parent = parent };
            f.elements.Add(e); return e;
        }
        static void Art(HomeFrame f, string id, string asset, float x, float y, float w, float h, bool sliced = true, string parent = "")
        {
            var e = Add(f, id, "sprite", x, y, w, h, parent);
            e.asset = asset; e.sliced = sliced; e.preserveAspect = !sliced; e.color = "#FFFFFF";
        }
        static void Text(HomeFrame f, string id, string value, float x, float y, float w, float h, int size, string color = "#073354", bool left = false)
        {
            var e = Add(f, id, left ? "ranknameleft115" : "text", x, y, w, h);
            e.text = value ?? ""; e.fontSize = size; e.color = color;
        }
        static void Hit(HomeFrame f, string id, string action, string label, float x, float y, float w, float h, bool enabled)
        {
            var e = Add(f, id, "group", x, y, w, h);
            e.action = enabled ? action : "disabled"; e.label = label;
        }
        static void Button(HomeFrame f, string id, string action, string label, float x, float y, float w, float h, bool enabled, string tone = "Blue", int size = 13)
        {
            Art(f, id + "-art", enabled ? "TA_Button_" + tone : "TA_Button_Disabled", x, y, w, h);
            Text(f, id + "-label", label, x + 5, y + 3, w - 10, h - 6, size, enabled ? "#FFFFFF" : "#617F90");
            Hit(f, id, action, label, x, y, w, h, enabled);
        }
        static void Avatar(HomeFrame f, string id, float x, float y, float size, string portrait = null)
        {
            Art(f, id + "-frame", "TA_Button_Blue", x, y, size, size);
            if (string.IsNullOrEmpty(portrait))
                Art(f, id + "-fallback", "TA_Icon_People", x + size * .22f, y + size * .22f, size * .56f, size * .56f, false);
            else
            {
                Art(f, id + "-mask", "LB2_AvatarMask", x + 3, y + 3, size - 6, size - 6, false);
                f.elements[f.elements.Count - 1].kind = "mask";
                Art(f, id + "-portrait", portrait, 0, 0, size - 6, size - 6, false, id + "-mask");
            }
        }
        static void FriendRow(HomeFrame f, SocialProfile82 p, float x, float y, float w, bool enabled, bool search, SocialRelationship82 relation = null, string portrait = null, string team = null)
        {
            string id = (search ? "online-search-result115-" : "online-friend-") + p.playerId;
            const float h = 76;
            Art(f, id + "-base", "TA_Panel_Cream", x, y, w, h);
            Avatar(f, id + "-avatar", x + 9, y + 9, 58, portrait);
            float actionWidth = search ? 94 : 48;
            float textWidth = Math.Max(42, w - 82 - actionWidth - 10);
            Text(f, id + "-name", p.displayName, x + 74, y + 9, textWidth, 26, 16, "#073354", true);
            if (!string.IsNullOrEmpty(team)) Text(f, id + "-team", team, x + 74, y + 36, textWidth, 16, 11, "#527487", true);
            // The adjacent arrow already carries the verified level count.
            // No peer-team field exists in the service contract yet, so show
            // an honest localized label instead of repeating that count.
            else Text(f, id + "-cleared", L("Level", "Nivel", "Niveau", "Level", "\u0423\u0440\u043e\u0432\u0435\u043d\u044c"), x + 74, y + 36, textWidth, 19, 11, "#527487", true);
            Art(f, id + "-up", "TA_Stat_up", x + 74, y + 57, 12, 12, false);
            Text(f, id + "-level", Num(p.completedLevels), x + 89, y + 54, 50, 17, 11, "#174C69", true);
            if (!search)
            {
                Art(f, id + "-manage-base", "TA_Button_Blue", x + w - 57, y + 14, 48, 48);
                Art(f, id + "-manage-art", "TC_Icon_More", x + w - 45, y + 26, 24, 24, false);
                Hit(f, id + "-manage", "player:" + p.playerId, p.displayName, x + w - 57, y + 14, 48, 48, enabled);
            }
            else
            {
                bool ready = relation != null;
                if (ready && relation.state == "None")
                {
                    Button(f, id + "-add", "search-add115:" + p.playerId, T("Add"), x + w - 102, y + 14, 94, 48, enabled, "Blue", 12);
                    f.elements[f.elements.Count - 1].label = T("Add") + " " + p.displayName;
                }
                else if (ready && relation.state == "Incoming")
                {
                    Button(f, id + "-accept", "search-accept115:" + relation.requestId, T("Accept"), x + w - 102, y + 14, 94, 48, enabled, "Blue", 12);
                    f.elements[f.elements.Count - 1].label = T("Accept") + " " + p.displayName;
                }
                else if (ready && (relation.state == "Outgoing" || relation.state == "Friends"))
                {
                    Art(f, id + "-state-base", "TA_Button_Disabled", x + w - 102, y + 14, 94, 48);
                    Text(f, id + "-state", relation.state == "Outgoing" ? L("Sent", "Enviada", "Envoyee", "Gesendet", "\u041e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043e") : T("Friends"), x + w - 98, y + 17, 86, 42, 11, "#FFFFFF");
                }
            }
            Hit(f, id, "player:" + p.playerId, p.displayName, x, y, Math.Max(48, w - actionWidth - 9), h, enabled);
        }

        public static float Populate(OnlineTeamsFrame82 r, OnlinePlayersView82 v, float x, float w, float y, bool enabled)
        {
            var f = r.content;
            if (v.tab == 2 || v.tab == 3) return SecondaryList(f, v, x, w, y, enabled);
            if (v.friendSecondary118) return SecondaryMenu(f, x, w, y, enabled);
            if (v.searchOpen115) return Search(f, v, x, w, y, enabled);
            if (v.friendsRank115) return Ranking(f, v, x, w, y, enabled);
            return Default(f, v, x, w, y, enabled);
        }

        static float Default(HomeFrame f, OnlinePlayersView82 v, float x, float w, float y, bool enabled)
        {
            // The viewport already begins below the R3 tabs. Keep the summary
            // close to that edge so three rows and the count fit at 360x640.
            Art(f, "online-friends-summary118", "TA_Panel_Blue", x, y, w, 84);
            Art(f, "online-friends-summary-icon118", "TA_Icon_People", x + 12, y + 21, 38, 38, false);
            Text(f, "online-friends-summary-title118", L("Your friends", "Tus amigos", "Vos amis", "Deine Freunde", "\u0412\u0430\u0448\u0438 \u0434\u0440\u0443\u0437\u044c\u044f"), x + 60, y + 13, w - 172, 27, 17, "#FFFFFF", true);
            Text(f, "online-friends-summary-sub118", L("Play together", "Jueguen juntos", "Jouez ensemble", "Spielt zusammen", "\u0418\u0433\u0440\u0430\u0439\u0442\u0435 \u0432\u043c\u0435\u0441\u0442\u0435"), x + 60, y + 43, w - 172, 21, 11, "#C8E1EE", true);
            Button(f, "online-friends-add118", "friends-open-search118", L("Add", "A\u00f1adir", "Ajouter", "Hinzuf\u00fcgen", "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c"), x + w - 105, y + 16, 96, 48, enabled, "Green", 12);
            y += 104;
            var friends = v.friends?.friends;
#if UNITY_EDITOR
            if (v.editorVisualFixture118 && friends == null) friends = FixtureProfiles();
#endif
            if (friends != null)
            {
                foreach (var p in friends)
                {
                    FriendRow(f, p, x, y, w, enabled, false, null, FixturePortrait(v, p), FixtureTeam(v, p));
                    y += 80;
                }
                if (friends.Length == 0)
                {
                    Text(f, "online-friends-empty", T("EmptyFriends"), x + 8, y + 10, w - 16, 60, 15, "#E7F6FC");
                    y += 72;
                }
                if (v.friends?.hasMore == true)
                {
                    Button(f, "online-friends-more", "more-friends", T("More"), x, y, w, 48, enabled);
                    y += 58;
                }
                string count = L("Friends: ", "Amigos: ", "Amis : ", "Freunde: ", "\u0414\u0440\u0443\u0437\u044c\u044f: ") + friends.Length + (v.friends?.hasMore == true ? "+" : "");
                Text(f, "online-friends-count118", count, x, y + 3, w, 25, 11, "#BDDFFF");
                y += 39;
            }
            else
            {
                Text(f, "online-friends-unavailable118", v.busy || !string.IsNullOrEmpty(v.status) ? "" : T("EmptyFriends"), x + 8, y + 8, w - 16, 64, 15, "#E7F6FC");
                y += 78;
            }
            return y;
        }

        static float Search(HomeFrame f, OnlinePlayersView82 v, float x, float w, float y, bool enabled)
        {
            float inputW = Math.Max(140, w - 108);
            Art(f, "online-player-code-art118", "TA_Field", x, y, inputW, 48);
            Art(f, "online-find-icon118", "LB2_Find", x + 8, y + 14, 20, 20, false);
            var input = Add(f, "online-player-code-input", "input", x + 34, y + 4, inputW - 47, 40);
            input.label = L("Name or player code", "Nombre o c\u00f3digo", "Nom ou code", "Name oder Code", "\u0418\u043c\u044f \u0438\u043b\u0438 \u043a\u043e\u0434 \u0438\u0433\u0440\u043e\u043a\u0430");
            input.fontSize = 12; input.color = "#073354";
            Button(f, "online-player-find", "find", L("Find", "Buscar", "Chercher", "Suchen", "\u041d\u0430\u0439\u0442\u0438"), x + w - 100, y, 100, 48, enabled, "Green", 12);
            y += 59;
            Text(f, "online-find-heading118", L("Find friends", "Buscar amigos", "Trouver des amis", "Freunde finden", "\u041d\u0430\u0439\u0442\u0438 \u0434\u0440\u0443\u0437\u0435\u0439"), x + 2, y, w - 4, 25, 15, "#FFFFFF", true);
            // The selected Friends tab in the fixed header returns to the
            // list. R3 has no close disc beside this heading; its former 48 px
            // button overlapped the first result by 17 px.
            y += 25;
            var page = v.searchResults115;
            bool matches = v.searchReady115 && page?.players != null && page.requestQuery == v.searchQuery115 && page.requestCursor == v.searchCursor115;
#if UNITY_EDITOR
            if (v.editorVisualFixture118 && !matches)
            {
                var fixtures = FixtureProfiles();
                page = new SocialPlayerSearch115 { players = fixtures, relationships = fixtures.Select((p, i) => new SocialRelationship82 { playerId = p.playerId, state = i == 1 ? "Outgoing" : "None" }).ToArray(), requestQuery = v.searchQuery115, requestCursor = v.searchCursor115 };
                matches = true;
            }
#endif
            if (matches)
            {
                foreach (var p in page.players)
                {
                    var relation = page.relationships?.FirstOrDefault(q => q.playerId == p.playerId);
                    FriendRow(f, p, x, y, w, enabled && relation != null, true, relation, FixturePortrait(v, p), FixtureTeam(v, p));
                    y += 81;
                }
                if (page.players.Length == 0 && !page.hasMore)
                {
                    Text(f, "online-search-empty115", L("No players found.", "No se encontraron jugadores.", "Aucun joueur trouv\u00e9.", "Keine Spieler gefunden.", "\u0418\u0433\u0440\u043e\u043a\u0438 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b."), x + 8, y + 10, w - 16, 55, 15, "#E7F6FC");
                    y += 70;
                }
                if (page.hasMore)
                {
                    Button(f, "online-search-more115", "search-more115", T("More"), x, y, w, 48, enabled);
                    y += 58;
                }
            }
            else
            {
                string hint = v.busy || !string.IsNullOrEmpty(v.status) ? "" : string.IsNullOrEmpty(v.searchQuery115) ? L("Enter at least two letters to search.", "Escribe al menos dos letras.", "Saisissez au moins deux lettres.", "Mindestens zwei Zeichen eingeben.", "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043c\u0438\u043d\u0438\u043c\u0443\u043c \u0434\u0432\u0435 \u0431\u0443\u043a\u0432\u044b.") : T("Unavailable");
                Text(f, "online-search-prompt118", hint, x + 8, y + 10, w - 16, 60, 14, "#E7F6FC"); y += 72;
            }
            return y;
        }

        static float SecondaryMenu(HomeFrame f, float x, float w, float y, bool enabled)
        {
            y += 18;
            Text(f, "online-friends-manage-title118", L("Friends options", "Opciones de amigos", "Options d'amis", "Freundesoptionen", "\u0414\u0435\u0439\u0441\u0442\u0432\u0438\u044f \u0441 \u0434\u0440\u0443\u0437\u044c\u044f\u043c\u0438"), x, y, w, 34, 19, "#FFFFFF"); y += 46;
            Button(f, "online-friends-requests118", "friends-show-requests118", T("Requests"), x, y, w, 48, enabled); y += 58;
            Button(f, "online-friends-block118", "friends-show-blocked118", T("Blocked"), x, y, w, 48, enabled); y += 58;
            Button(f, "online-friends-ranking115", "friends-ranking115", L("Friends ranking", "Ranking de amigos", "Classement des amis", "Freundesrangliste", "\u0420\u0435\u0439\u0442\u0438\u043d\u0433 \u0434\u0440\u0443\u0437\u0435\u0439"), x, y, w, 48, enabled); y += 58;
            Button(f, "online-friends-menu-back118", "friends-secondary-back118", T("Back"), x, y, w, 48, enabled); y += 58;
            return y;
        }

        static float SecondaryList(HomeFrame f, OnlinePlayersView82 v, float x, float w, float y, bool enabled)
        {
            y += 14;
            Button(f, "online-friends-secondary-back118", "friends-secondary-back118", T("Back"), x, y, w, 48, enabled); y += 61;
            if (v.tab == 2)
            {
                foreach (var p in v.requests?.requests ?? new SocialFriendRequest82[0])
                {
                    string id = "online-request-" + p.requestId;
                    Art(f, id + "-base", "TA_Panel_Cream", x, y, w, 126);
                    Text(f, id + "-name", p.profile.displayName, x + 12, y + 8, w - 24, 28, 16, "#073354", true);
                    Text(f, id + "-direction", T(p.direction == "incoming" ? "Incoming" : "Outgoing"), x + 12, y + 37, w - 24, 22, 11, "#527487", true);
                    float half = (w - 30) / 2;
                    if (p.direction == "incoming")
                    {
                        Button(f, id + "-accept", "accept:" + p.requestId, T("Accept"), x + 12, y + 70, half, 48, enabled, "Green");
                        Button(f, id + "-decline", "decline:" + p.requestId, T("Decline"), x + 18 + half, y + 70, half, 48, enabled);
                    }
                    else Button(f, id + "-cancel", "cancel-request:" + p.requestId, T("Cancel"), x + 12, y + 70, w - 24, 48, enabled);
                    y += 136;
                }
                if (v.requests?.requests?.Length == 0) { Text(f, "online-requests-empty", T("EmptyRequests"), x + 8, y + 10, w - 16, 65, 15, "#E7F6FC"); y += 80; }
                if (v.requests?.hasMore == true) { Button(f, "online-requests-more", "more-requests", T("More"), x, y, w, 48, enabled); y += 58; }
            }
            else
            {
                foreach (var p in v.blocks?.blocks ?? new SocialBlock82[0])
                {
                    string id = "online-block-" + p.playerId;
                    Art(f, id + "-base", "TA_Panel_Cream", x, y, w, 96);
                    Text(f, id + "-id", p.playerId, x + 12, y + 8, w - 24, 22, 10, "#073354", true);
                    Button(f, id, "unblock:" + p.playerId, T("Unblock"), x + 12, y + 40, w - 24, 48, enabled); y += 106;
                }
                if (v.blocks?.blocks?.Length == 0) { Text(f, "online-blocks-empty", T("EmptyBlocks"), x + 8, y + 10, w - 16, 65, 15, "#E7F6FC"); y += 80; }
                if (v.blocks?.hasMore == true) { Button(f, "online-blocks-more", "more-blocks", T("More"), x, y, w, 48, enabled); y += 58; }
            }
            return y;
        }

        static float Ranking(HomeFrame f, OnlinePlayersView82 v, float x, float w, float y, bool enabled)
        {
            y += 14;
            Button(f, "online-friends-list115", "friends-list115", L("Friends list", "Lista de amigos", "Liste des amis", "Freundesliste", "\u0421\u043f\u0438\u0441\u043e\u043a \u0434\u0440\u0443\u0437\u0435\u0439"), x, y, w, 48, enabled); y += 61;
            var page = v.friendsRanks115;
            bool matches = page?.entries != null && page.scope == "friends" && page.nextOffset - page.entries.Length == v.friendsRankOffset115;
            if (v.friendsRankOffset115 > 0) { Button(f, "online-friends-rank-first115", "friends-rank-first115", T("Back"), x, y, w, 48, enabled); y += 58; }
            if (!matches) return y;
            foreach (var p in page.entries)
            {
                string id = "online-rank-" + p.playerId;
                Art(f, id + "-base", "TA_Panel_Cream", x, y, w, 72);
                if (p.rank >= 1 && p.rank <= 3) Art(f, id + "-medal", p.rank == 1 ? "TA_Rank_Gold" : p.rank == 2 ? "TA_Rank_Silver" : "TA_Rank_Bronze", x + 7, y + 20, 30, 30, false);
                Text(f, id + "-rank", Num(p.rank), x + 8, y + 22, 30, 24, 13);
                Avatar(f, id + "-avatar", x + 44, y + 8, 54);
                Text(f, id + "-name", p.displayName, x + 110, y + 8, w - 120, 27, 15, "#073354", true);
                Text(f, id + "-score", OnlinePlayersText82.F("Cleared", p.score), x + 110, y + 36, w - 120, 24, 11, "#527487", true);
                Hit(f, id, "player:" + p.playerId, p.displayName, x, y, w, 72, enabled);
                y += 82;
            }
            if (page.entries.Length == 0) { Text(f, "online-friends-ranks-empty115", T("EmptyRanks"), x + 8, y + 10, w - 16, 70, 15, "#E7F6FC"); y += 90; }
            if (page.hasMore) { Button(f, "online-friends-rank-more115", "friends-rank-more115", T("More"), x, y, w, 48, enabled); y += 58; }
            return y;
        }

#if UNITY_EDITOR
        static readonly string[] FixtureIds = { "11111111111111111111111111111111", "22222222222222222222222222222222", "33333333333333333333333333333333" };
        static SocialProfile82[] FixtureProfiles() => new[]
        {
            new SocialProfile82 { playerId = FixtureIds[0], displayName = "Aurora", completedLevels = 50, leaderboardOptIn = true },
            new SocialProfile82 { playerId = FixtureIds[1], displayName = "Old Oak", completedLevels = 49, leaderboardOptIn = true },
            new SocialProfile82 { playerId = FixtureIds[2], displayName = "Riverlight", completedLevels = 47, leaderboardOptIn = true }
        };
#endif
        static string FixturePortrait(OnlinePlayersView82 v, SocialProfile82 p)
        {
#if UNITY_EDITOR
            if (v.editorVisualFixture118)
            {
                if (p.playerId == FixtureIds[0]) return "Portrait_Weaver_R2";
                if (p.playerId == FixtureIds[1]) return "Portrait_Scholar_R2";
                if (p.playerId == FixtureIds[2]) return "Portrait_Ivan_R2";
            }
#endif
            return null;
        }
        static string FixtureTeam(OnlinePlayersView82 v, SocialProfile82 p)
        {
#if UNITY_EDITOR
            if (v.editorVisualFixture118)
            {
                if (p.playerId == FixtureIds[0]) return "Rainkeepers";
                if (p.playerId == FixtureIds[1]) return "Lantern Guild";
                if (p.playerId == FixtureIds[2]) return "Silver Wells";
            }
#endif
            return null;
        }
    }
}
