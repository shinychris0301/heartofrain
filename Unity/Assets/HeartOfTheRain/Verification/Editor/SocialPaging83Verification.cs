#if UNITY_EDITOR
using System;
using System.Collections;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;

namespace HeartOfTheRain.Verification
{
    public static partial class Social82Verification
    {
        static void PagingParserChecks(SocialBackendClient82 client)
        {
            var read = typeof(SocialBackendClient82).GetMethod("ReadBoundedMessages", BindingFlags.Instance | BindingFlags.NonPublic);
            string name = string.Concat(Enumerable.Repeat("😀", 20)) + new string('\u0301', 236);
            string text = string.Concat(Enumerable.Repeat("😀", 999)) + "Я";
            var items = Enumerable.Range(1, 8).Select(n => new SocialMessage82 {
                messageId = n.ToString("x32"), authorId = "11111111111111111111111111111111",
                displayName = name, text = text, sequence = n * 3, createdAt = 1
            }).ToArray();
            var page = new SocialMessages82 { messages = items, nextCursor = 24, olderCursor = 3, hasOlder = true, unreadCount = 8 };
            string json = JsonUtility.ToJson(page);
            Check(Encoding.UTF8.GetByteCount(json) < 65536, "Eight maximal Unicode message/name rows fit64KiB");
            var good = (SocialMessages82)read.Invoke(client, new object[] { json, 0L, true, 8 });
            Check(good.messages.Length == 8 && good.olderCursor == 3 && good.nextCursor == 24, "Sparse global sequences retain exact bounded endpoints");
            report.pagingTransportChecks++;
            foreach(string bad in new[] {
                json.Replace("\"olderCursor\":3", "\"olderCursor\":4"),
                json.Replace("\"nextCursor\":24", "\"nextCursor\":25"),
                json.Replace("\"hasNewer\":false", "\"hasNewer\":true"),
                json.Replace("\"sequence\":6", "\"sequence\":3"),
                json.Replace("\"hasOlder\":true", "\"hasOlder\":null")
            }) {
                bool rejected = false;
                try { read.Invoke(client, new object[] { bad, 0L, true, 8 }); }
                catch(TargetInvocationException error) { rejected = error.InnerException is FormatException; }
                Check(rejected, "Malformed bounded history metadata/order is rejected"); report.pagingTransportChecks++;
            }
            bool exclusive = false;
            try { read.Invoke(client, new object[] { json, 24L, false, 8 }); }
            catch(TargetInvocationException error) { exclusive = error.InnerException is FormatException; }
            Check(exclusive, "Older history excludes its before boundary"); report.pagingTransportChecks++;
            page.messages = Enumerable.Range(1, 100).Select(n => new SocialMessage82 {
                messageId = n.ToString("x32"), authorId = items[0].authorId, displayName = name, text = text, sequence = n, createdAt = 1
            }).ToArray();
            Check(Encoding.UTF8.GetByteCount(JsonUtility.ToJson(page)) > 65536, "Legacy100 maximal Unicode rows exceed64KiB; UI uses bounded pages");
            Passed("Bounded Unicode byte budget and strict page cursor counterexamples");
        }

        static IEnumerator VisibleReadChecks(OnlinePlayersPage82 page, SocialBackendClient82 receiver, string peer)
        {
            var unread = page.VerificationSession.Snapshot<SocialMessages82>(SocialPane82.DirectChat);
            Check(unread.unreadCount > 0, "Loading/caching a conversation alone does not acknowledge unread messages");
            Check(!page.VerificationSession.ObserveVisibleMessages(unread.nextCursor, false), "Unseen latest message cannot create a read mutation");
            Check(!page.VerificationSession.ObserveVisibleMessages(unread.nextCursor - 1, true), "Noncurrent visible cursor cannot mark the channel read");
            report.visibleReadChecks += 2;
            CapturePage(page, "DirectUnread_Russian");
            Check(page.VerificationObserveRead(), "Actual rendered latest message end authorizes a durable read command");
            while(page.VerificationSession.Busy) yield return null;
            report.visibleReadChecks++;
            Check(page.VerificationSession.Snapshot<SocialMessages82>(SocialPane82.DirectChat).unreadCount == 0 && !page.VerificationObserveRead(),
                "Confirmed current read receipt clears unread cache without repeated writes"); report.visibleReadChecks++;
            yield return Call<SocialMessages82>(done => receiver.GetMessagesTail("Direct", peer, 8, done), value => Check(value.unreadCount == 0, "Separate HTTP confirms visible read acknowledgement"));
        }

        static IEnumerator BlockedPageChecks(OnlinePlayersPage82 page, string blocked)
        {
            page.Show(); Click(page, "online-primary-friends"); yield return PageReady(page); Click(page, "online-friends-blocked"); yield return PageReady(page);
            CapturePage(page, "BlockedPlayers_Russian");
            Check(page.VerificationSession.Snapshot<SocialBlocks82>(SocialPane82.Blocks).blocks.Any(row => row.playerId == blocked), "Actual owner blocked list contains the server identifier");
            report.blockedPageChecks++;
            Click(page, "online-block-" + blocked); CapturePage(page, "UnblockPlayer_Russian");
            Click(page, "online-player-confirm"); yield return PageReady(page);
            Check(page.VerificationSession.Snapshot<SocialBlocks82>(SocialPane82.Blocks).blocks.All(row => row.playerId != blocked), "Actual Unblock confirmation refreshes the list without refriending");
            report.blockedPageChecks++; page.Hide(false);
        }

        static IEnumerator BoundedHistoryChecks(string origin, ManagedIdentitySession82 owner, EditorEphemeralIdentity82 vault,
            SocialBackendClient82 client, string team, string body)
        {
            // Existing fixture sends2 messages with this author;7 more remain
            // below the unchanged10/minute production limit.
            for(int n = 0; n < 7; n++) yield return Call<SocialMutation82>(done => client.SendMessage(Id(), "Team", team, body, done), null);
            long oldest = 0, newest = 0;
            yield return Call<SocialMessages82>(done => client.GetMessagesTail("Team", team, 8, done), value => {
                Check(value.messages.Length == 8 && value.hasOlder && !value.hasNewer && !value.hasMore && value.messages.All(row => row.text == body),
                    "Actual latest-eight HTTP accepts maximal Unicode history and exposes older rows");
                oldest = value.olderCursor; newest = value.nextCursor; report.pagingTransportChecks++;
            });
            yield return Call<SocialMessages82>(done => client.GetMessagesBefore("Team", team, oldest, 8, done), value => {
                Check(value.messages.Length > 0 && value.messages.All(row => row.sequence < oldest) && value.hasNewer && !value.hasOlder,
                    "Actual older page is exclusive, ascending and exposes newer history"); report.pagingTransportChecks++;
            });
            var session = new SocialPageSession82(Client(origin, owner, vault, System.IO.Path.Combine(temporary, "bounded-team.sealed")));
            cleanup.Add(session);
            Check(session.SelectTeam(team), "Bounded controller selects actual team membership"); while(session.Busy) yield return null;
            session.Show(SocialPane82.TeamChat); Check(session.RefreshTeamMessages(), "Bounded controller opens latest messages"); while(session.Busy) yield return null;
            Check(session.Snapshot<SocialMessages82>(SocialPane82.TeamChat).nextCursor == newest, "Opening does not scan channel from sequence0");
            Check(session.LoadOlderMessages(), "Explicit controller older-page request"); while(session.Busy) yield return null;
            var older = session.Snapshot<SocialMessages82>(SocialPane82.TeamChat);
            Check(older.nextCursor < oldest && older.hasNewer && !session.ObserveVisibleMessages(older.nextCursor, true), "Older-page viewing cannot acknowledge unseen latest messages");
            report.visibleReadChecks++;
            Check(session.LatestMessages(), "Explicit latest-page return"); while(session.Busy) yield return null;
            Check(session.Snapshot<SocialMessages82>(SocialPane82.TeamChat).nextCursor == newest, "Latest return restores only the newest bounded page");
            report.pagingTransportChecks++;
            // The transport boundary above includes non-BMP maximal data. The
            // actual camera capture below uses the established Russian public
            // name and the older ordinary messages, without claiming emoji
            // coverage in the approved UI font.
            yield return Call<SocialMutation82>(done => client.UpdateName(Id(), "Друг дождя", done), null);
            var art = UnityEditor.AssetDatabase.LoadAssetAtPath<HeartOfTheRain.App.Teams.TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");
            var go = new GameObject("Actual bounded team history83"); var page = go.AddComponent<OnlineTeamsPage82>();
            cleanup.Add(new CleanupAction(() => { if(go) UnityEngine.Object.DestroyImmediate(go); }));
            var uiSession = new SocialPageSession82(Client(origin, owner, vault, System.IO.Path.Combine(temporary, "bounded-ui.sealed")));
            cleanup.Add(uiSession); page.ConfigureForVerification(art, uiSession, Dispatch); page.Show(); yield return PageReady(page);
            Click(page, "online-team-older"); yield return PageReady(page); CapturePage(page, "OlderMessages_Russian");
            Check(uiSession.Snapshot<SocialMessages82>(SocialPane82.TeamChat).hasNewer, "Actual older button displays the older bounded page");
            Click(page, "online-team-latest"); yield return PageReady(page);
            Check(uiSession.Snapshot<SocialMessages82>(SocialPane82.TeamChat).nextCursor == newest, "Actual latest button returns to the server tail");
            page.Hide(false); Passed("Actual bounded Unicode tail/older/controller and UGUI history");
        }
    }
}
#endif

#if UNITY_EDITOR
namespace HeartOfTheRain.Verification
{
    using System;
    using System.Collections.Generic;
    using System.IO;
    using System.Linq;
    using System.Reflection;
    using System.Text;
    using UnityEditor;
    using UnityEditor.SceneManagement;
    using UnityEngine;
    using HeartOfTheRain.App.Home;
    using HeartOfTheRain.App.PreLevel;
    using HeartOfTheRain.App.Profile;
    using HeartOfTheRain.App.ServerGameplay;
    using HeartOfTheRain.App.ServerRewards;
    using HeartOfTheRain.App.OnlineIdentity;
    using HeartOfTheRain.App.OnlineSocial;
    using HeartOfTheRain.App.Teams;
    using HeartOfTheRain.App.Leaderboard;

    [InitializeOnLoad] public static class SocialExpiry83Verification
    {
        const string Key = "HOTR.SocialExpiry83.Http";
        const BindingFlags Hidden = BindingFlags.Instance | BindingFlags.NonPublic;
        [Serializable] sealed class Report
        {
            public string status, utc, unity, scope, playerIdHash, balancesBefore, balancesAfter, ordinaryProfilesBefore, ordinaryProfilesAfter;
            public int checks, localExpiryInjections, signedRefreshRequests, initialSignedRequests, finalSignedRequests, homeRenewalsBefore, homeRenewalsAfter, homeBatchesBefore, homeBatchesAfter;
            public bool playersRenewed, teamsRenewed, pendingPreserved, noAutomaticPendingWrite, samePlayerAndWallet, selectedPeerPreserved, homeBadgesRenewed;
            public bool actualHttp = true, actualOrdinaryGateway = true, injectedMonotonicAccessAge = true, android = false, productionEnabled = false;
            public List<string> passed = new List<string>(), errors = new List<string>();
        }
        static Report report;
        static HomePage home; static ServerGameSession server; static OnlinePlayersPage82 players; static OnlineTeamsPage82 teams;
        static ServerRewardsSession rewards; static ManagedIdentitySession82 identity; static IdentityHttpTransport82 transport;
        static bool launched, finished; static int phase; static long generation; static string owner, pendingId, output; static double deadline;
        static SocialBackendClient82 expiredClient;
        static SocialPendingCommand82 pending;
        static SocialExpiry83Verification() { if(SessionState.GetBool(Key, false)) EditorApplication.update += Tick; }
        static T Field<T>(object value, string name) => (T)value.GetType().GetField(name, Hidden).GetValue(value);
        static void Check(bool valid, string label) { report.checks++; if(!valid) throw new InvalidOperationException(label); }
        static string ProfilesHash()
        {
            string root = Path.Combine(Application.persistentDataPath, "Profiles");
            if(!Directory.Exists(root)) return IdentityProtocol82.Sha("absent");
            return IdentityProtocol82.Sha(string.Join("\n", Directory.GetFiles(root, "*", SearchOption.AllDirectories).OrderBy(path => path, StringComparer.Ordinal)
                .Select(path => path.Substring(root.Length).Replace('\\', '/') + ":" + IdentityProtocol82.Sha(File.ReadAllBytes(path)))));
        }
        static string BalanceHash()
        {
            var wallet = server.Wallet;
            return IdentityProtocol82.Sha(wallet.playerId + "|" + wallet.revision + "|" + wallet.coins + "|" + wallet.stars + "|" + wallet.lives + "|" + wallet.completed
                + "|" + string.Join(",", wallet.starting) + "|" + string.Join(",", wallet.tools) + "|" + wallet.refundReviewRequired);
        }
        static void Expire()
        {
            Check(identity.HasAccess, "Control begins with a valid managed access token");
            typeof(ManagedIdentitySession82).GetField("accessAt", Hidden).SetValue(identity,
                System.Diagnostics.Stopwatch.GetTimestamp() - System.Diagnostics.Stopwatch.Frequency * 901L);
            Check(!identity.HasAccess, "Actual monotonic HasAccess predicate rejects901s injected age");
            generation = server.SessionGeneration; requestsAtExpiry = transport.VerificationRequestCount; report.localExpiryInjections++;
        }
        static int requestsAtExpiry;
        // A same-player renewal keeps the session generation (pages keep their views), so renewal is
        // proven by the signed identity requests it makes.
        static bool Renewed() => identity.HasAccess && transport.VerificationRequestCount > requestsAtExpiry;
        static bool SameActor() => server.Ready && server.PlayerId == owner && BalanceHash() == report.balancesBefore;
        public static void Run()
        {
            string origin = Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_HTTP_ORIGIN");
            if(Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_HTTP_ALLOWED") != "1" || !HeartOfTheRain.App.RuStore.RuStoreBackendClient.IsAllowedOrigin(origin, true) || !new Uri(origin).IsLoopback)
                throw new InvalidOperationException("ExplicitSocialExpiryFixtureRequired");
            string directory = Path.GetFullPath("../.verification-cache/ServerGameplay83/SocialExpiry/" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(directory); string configuration = Path.Combine(directory, "configuration.json");
            File.WriteAllText(configuration, JsonUtility.ToJson(new ServerGameplayConfiguration {
                version = 1, mode = "ManagedGuestServer", origin = origin, identityScope = "review-social-expiry-83", allowDevelopmentLoopback = true, socialEnabled = true
            }), new UTF8Encoding(false));
            SessionState.SetString(Key + ".previousConfig", Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG") ?? "");
            Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG", configuration); SessionState.SetBool(Key, true);
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            EditorApplication.update -= Tick; EditorApplication.update += Tick; EditorApplication.isPlaying = true;
        }
        static void Launch()
        {
            launched = true; deadline = EditorApplication.timeSinceStartup + 180;
            output = Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_OUTPUT") ?? "../Verification/Evidence/ServerGameplay83");
            report = new Report {
                utc = DateTime.UtcNow.ToString("O"), unity = Application.unityVersion, ordinaryProfilesBefore = ProfilesHash(),
                scope = "Actual pinned Editor PlayMode ordinary Home/ProfileHost/server factory and real signed loopback managed session refresh. Three local accessAt901s clock injections exercise visible Players polling, Teams manual Retry and idle Home reward metadata renewal. Same server player/wallet, exact protected rejected pending intent, no automatic write retry and selected peer retention are checked. This is deterministic expiry-path proof, not a15minute wall-clock soak, Android/Keystore restart, UI visual approval, production hosting or payment proof."
            };
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab");
            var node = UnityEngine.Object.Instantiate(prefab); home = node.GetComponent<HomePage>();
            var flow = node.GetComponent<HomeLevelFlow>(); if(!flow) flow = node.AddComponent<HomeLevelFlow>();
            flow.home = home; flow.assets = AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");
            var ranks = node.GetComponent<LeaderboardPage>(); if(!ranks) ranks = node.AddComponent<LeaderboardPage>();
            ranks.home = home; ranks.assets = AssetDatabase.LoadAssetAtPath<LeaderboardAssets>("Assets/HeartOfTheRain/App/Leaderboard/LeaderboardAssets.asset");
            var guild = node.GetComponent<TeamsPage>(); if(!guild) guild = node.AddComponent<TeamsPage>();
            guild.home = home; guild.assets = AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");
        }
        static void Tick()
        {
            if(finished || !EditorApplication.isPlaying || EditorApplication.isCompiling || EditorApplication.isUpdating) return;
            try {
                if(!launched) { Launch(); return; }
                if(EditorApplication.timeSinceStartup > deadline) throw new TimeoutException("Social expiry stage" + phase);
                switch(phase) {
                    case 0:
                        var host = home.GetComponent<PlayerProfileHost>();
                        if(!host || !host.Ready || !host.ServerSession || host.ServerSession.Busy) return;
                        server = host.ServerSession; owner = server.PlayerId; identity = Field<ManagedIdentitySession82>(server, "identity");
                        transport = Field<IdentityHttpTransport82>(server, "identityTransport"); rewards = home.GetComponent<ServerRewardsSession>();
                        Check(server.Ready && !host.IsTransient && rewards, "Ordinary profile host selected managed server and reward session");
                        report.playerIdHash = IdentityProtocol82.Sha(owner); report.balancesBefore = BalanceHash(); report.initialSignedRequests = transport.VerificationRequestCount;
                        home.GetComponent<LeaderboardPage>().ShowServerPlayer(owner); players = home.GetComponent<OnlinePlayersPage82>(); phase = 1; return;
                    case 1:
                        if(players.VerificationPending) return;
                        Check(players.IsVisible && players.VerificationSession.PlayerId == owner, "Actual connected player page is visible before expiry");
                        expiredClient = Field<SocialBackendClient82>(players.VerificationSession, "client");
                        pendingId = Guid.NewGuid().ToString("N"); players.VerificationSession.RequestFriend(pendingId, owner); phase = 2; return;
                    case 2:
                        if(players.VerificationSession.Busy) return;
                        // Review 136: a real 422 is final, so no retry intent remains. A lost reply is planted instead,
                        // which is the case credential rotation must preserve exactly.
                        Check(players.VerificationSession.PendingCommand == null && expiredClient.VerificationStatuses.Contains(422), "A real rejected self-request is final and leaves no retry intent (review 136)");
                        Field<ProtectedSocialCommandJournal82>(expiredClient, "journal").Prepare(new SocialPendingCommand82 { operation = "friend.send", path = "/v1/friends/request", body = "{\"commandId\":\"" + pendingId + "\",\"playerId\":\"" + owner + "\"}", commandId = pendingId });
                        pending = players.VerificationSession.PendingCommand;
                        Check(pending != null && pending.commandId == pendingId, "A planted unresolved intent stands in for a lost reply");
                        Expire(); phase = 3; return; // Players Update/poll must renew without an unrelated wallet action.
                    case 3:
                        if(server.Busy || players.VerificationPending || !identity.HasAccess) return;
                        Check(SameActor() && Renewed(), "Visible Players guard renews the real signed session without changing player/wallet");
                        var restored = players.VerificationSession.PendingCommand;
                        Check(restored != null && JsonUtility.ToJson(restored) == JsonUtility.ToJson(pending), "Credential rotation preserves the exact protected social intent");
                        var renewed = Field<SocialBackendClient82>(players.VerificationSession, "client");
                        Check(!ReferenceEquals(renewed, expiredClient) && renewed.VerificationStatuses.Length > 0 && renewed.VerificationStatuses.All(status => status == 200), "Rebound controller performs successful reads without retrying rejected write");
                        Check(Field<string>(players, "peerId") == owner && Field<string>(players, "modal") == "profile", "Same-player refresh retains the selected peer/modal");
                        report.playersRenewed = report.pendingPreserved = report.noAutomaticPendingWrite = report.selectedPeerPreserved = true;
                        players.Request("cancel"); phase = 31; return;
                    case 31:
                        if(players.VerificationPending || server.Busy) return;
                        Check(players.VerificationSession.Snapshot<SocialRankRefresh115>(SocialPane82.GlobalRanks115) != null, "Closing the retained peer modal reloads the underlying real ranking view");
                        Check(players.VerificationSession.PendingCommand?.commandId == pendingId, "Underlying read refresh still retains the protected intent");
                        Check(players.VerificationSession.AcknowledgeAndDiscardPending(pendingId, true), "Fixture explicitly discards only its known rejected retry intent");
                        players.Hide(false); home.GetComponent<TeamsPage>().Show(); teams = home.GetComponent<OnlineTeamsPage82>(); phase = 4; return;
                    case 4:
                        if(teams.VerificationPending || server.Busy) return;
                        Check(teams.IsVisible && teams.VerificationSession.PlayerId == owner, "Actual connected Teams page is visible before expiry");
                        Expire(); teams.Request("retry"); phase = 5; return;
                    case 5:
                        if(server.Busy || teams.VerificationPending || !identity.HasAccess) return;
                        Check(SameActor() && Renewed() && teams.VerificationSession.Snapshot<SocialTeams82>(SocialPane82.Teams) != null,
                            "Teams Retry renews signed access and recovers the real server view"); report.teamsRenewed = true;
                        teams.Hide(true); phase = 6; return;
                    case 6:
                        if(server.Busy || rewards.HomeMetadataBusy || !rewards.HomeMetadataReady) return;
                        report.homeRenewalsBefore = rewards.HomeAccessRenewals; report.homeBatchesBefore = rewards.HomeMetadataBatches;
                        Expire(); phase = 7; return;
                    case 7:
                        if(server.Busy || rewards.HomeAccessRenewing || rewards.HomeMetadataBusy || !identity.HasAccess || !rewards.HomeMetadataReady
                            || rewards.HomeMetadataBatches <= report.homeBatchesBefore) return;
                        Check(SameActor() && Renewed() && rewards.HomeAccessRenewals == report.homeRenewalsBefore + 1,
                            "Idle Home renews expired access once and reloads authoritative badge metadata");
                        Check(!rewards.Coordinator.HasPending && !server.HasPending && server.Wallet.activeAttempt == null, "Expiry renewals create no claim, attempt or financial operation");
                        report.homeBadgesRenewed = true; report.homeRenewalsAfter = rewards.HomeAccessRenewals; report.homeBatchesAfter = rewards.HomeMetadataBatches;
                        report.balancesAfter = BalanceHash(); report.samePlayerAndWallet = report.balancesBefore == report.balancesAfter;
                        report.finalSignedRequests = transport.VerificationRequestCount; report.signedRefreshRequests = report.finalSignedRequests - report.initialSignedRequests;
                        Check(report.signedRefreshRequests >= 6, "Three expiries exercised actual challenge and session HTTP requests");
                        report.passed.Add("Players polling, protected pending and selection retention"); report.passed.Add("Teams manualRetry renewal"); report.passed.Add("Idle Home badge access renewal");
                        Finish(); return;
                }
            } catch(Exception error) { report.errors.Add("Stage" + phase + ": " + error.GetType().Name + ": " + error.Message); Finish(); }
        }
        static void Finish()
        {
            if(finished) return; finished = true; EditorApplication.update -= Tick;
            report.ordinaryProfilesAfter = ProfilesHash(); if(report.ordinaryProfilesBefore != report.ordinaryProfilesAfter) report.errors.Add("OrdinaryProfileBytesChanged");
            string previous = SessionState.GetString(Key + ".previousConfig", ""); Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG", previous.Length == 0 ? null : previous);
            SessionState.EraseBool(Key); report.status = report.errors.Count == 0 ? "PASS_NATIVE_SOCIAL_EXPIRY83_HTTP" : "FAIL_NATIVE_SOCIAL_EXPIRY83_HTTP";
            Directory.CreateDirectory(Path.Combine(output, "Native"));
            File.WriteAllText(Path.Combine(output, "Native", "SocialExpiry83_HTTP.json"), JsonUtility.ToJson(report, true), new UTF8Encoding(false));
            if(Application.isBatchMode) EditorApplication.Exit(report.errors.Count == 0 ? 0 : 1);
        }
    }
}
#endif
