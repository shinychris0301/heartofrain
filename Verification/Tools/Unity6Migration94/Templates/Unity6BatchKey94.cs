#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using HeartOfTheRain.M47;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace HeartOfTheRain.Verification
{
    // TEMPLATE: imported only into the approved isolated Unity 6 project.
    // The oracle uses a linear list of Texture2D references and requested
    // integer orders. It never calls or duplicates the ported BatchKey/hash.
    public static class Unity6BatchKey94
    {
        struct Input { public Sprite sprite; public int order; }
        sealed class Group { public Texture2D texture; public int order, quads; }
        [Serializable] public sealed class OrderRow { public int requested, nativeReadback, mathematicalClamp; public bool matchesClamp; }
        [Serializable] public sealed class GroupRow { public string texture; public int requestedOrder, expectedRendererOrder, actualRendererOrder, quads, vertices; }
        [Serializable] public sealed class FrameRow { public string name; public bool ordered; public int inputs, expectedGroups, activeMeshes; public List<GroupRow> groups = new List<GroupRow>(); }
        [Serializable] public sealed class Report
        {
            public string status, utc, unity, error;
            public int checks, texturePages, sprites, negativeControls;
            public string scope = "Native Unity 6 Editor execution of the real EffectMeshBatcher with two distinct fixture Texture2D pages and three Sprite objects, using the approved material. Linear object-reference/full-requested-order oracle; direct native MeshRenderer sorting-order readback controls unsupported out-of-range values. No pixels, timing, cross-engine equivalence, production data, Android/device or release certification.";
            public List<string> passed = new List<string>(), failures = new List<string>(), errors = new List<string>();
            public List<OrderRow> orders = new List<OrderRow>();
            public List<FrameRow> frames = new List<FrameRow>();
        }
        static Report report;
        static Texture2D textureA, textureB;
        static readonly Dictionary<int, int> nativeOrders = new Dictionary<int, int>();

        public static void Run()
        {
            string path = SafeOutput();
            report = new Report { status = "FAIL_NATIVE_UNITY6_94_BATCH_KEYS", utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion };
            GameObject root = null;
            Sprite first = null, samePage = null, otherPage = null;
            try
            {
                var assets = AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                Check(assets && assets.boards && assets.boards.effectsMaterial, "Approved gameplay effects material resolves");
                textureA = Texture("Batch94 page A", new Color32(30, 150, 230, 255));
                textureB = Texture("Batch94 page B", new Color32(235, 175, 40, 255));
                first = Sprite.Create(textureA, new Rect(0, 0, 2, 4), new Vector2(.5f, .5f), 4, 0, SpriteMeshType.FullRect);
                samePage = Sprite.Create(textureA, new Rect(2, 0, 2, 4), new Vector2(.5f, .5f), 4, 0, SpriteMeshType.FullRect);
                otherPage = Sprite.Create(textureB, new Rect(0, 0, 4, 4), new Vector2(.5f, .5f), 4, 0, SpriteMeshType.FullRect);
                report.texturePages = 2; report.sprites = 3;
                Check(textureA != textureB && first != samePage && first.texture == samePage.texture && first.texture != otherPage.texture,
                      "Two actual texture pages and distinct same-page Sprite objects establish independent identities");
                int[] orders = { int.MinValue, int.MaxValue, -17, 256 };
                RecordDirectOrderReadbacks(orders);
                var sequence = new List<Input>();
                foreach (int order in orders)
                {
                    sequence.Add(new Input { sprite = first, order = order });
                    sequence.Add(new Input { sprite = otherPage, order = order });
                    sequence.Add(new Input { sprite = samePage, order = order });
                }
                var input = sequence.ToArray();
                var interleaved = input.Concat(input.Reverse()).ToArray();
                var aliases = input.Concat(input.Select(value => new Input { sprite = value.sprite, order = nativeOrders[value.order] })).ToArray();
                RecordDirectOrderReadbacks(aliases.Select(value => value.order).Distinct());
                NegativeControls(interleaved);
                root = new GameObject("Independent Unity6 batch-key fixture");
                var batch = new EffectMeshBatcher(root.transform, assets.boards.effectsMaterial, new Bounds(Vector3.zero, new Vector3(64, 64, 2)));
                VerifyFrame("cold_groups_A_B_A_all_orders", batch, root, assets.boards.effectsMaterial, input, false);
                VerifyFrame("empty_new_Begin", batch, root, assets.boards.effectsMaterial, Array.Empty<Input>(), false);
                VerifyFrame("single_after_empty", batch, root, assets.boards.effectsMaterial, input.Take(1).ToArray(), false);
                VerifyFrame("shrink", batch, root, assets.boards.effectsMaterial, input.Take(5).ToArray(), false);
                VerifyFrame("regrow", batch, root, assets.boards.effectsMaterial, input, false);
                VerifyFrame("reverse_first_appearance", batch, root, assets.boards.effectsMaterial, input.Reverse().ToArray(), false);
                VerifyFrame("ordered_runs", batch, root, assets.boards.effectsMaterial, input, true);
                VerifyFrame("ordered_empty", batch, root, assets.boards.effectsMaterial, Array.Empty<Input>(), true);
                VerifyFrame("ordered_single", batch, root, assets.boards.effectsMaterial, input.Take(1).ToArray(), true);
                VerifyFrame("ordered_interleaved_regrow", batch, root, assets.boards.effectsMaterial, interleaved, true);
                VerifyFrame("full_orders_remain_distinct_when_native_readbacks_alias", batch, root, assets.boards.effectsMaterial, aliases, false);
                VerifyFrame("grouped_after_ordered_Begin_reset", batch, root, assets.boards.effectsMaterial, interleaved, false);
                Check(report.frames.Count == 12 && report.negativeControls == 4, "All twelve independent frame states and four wrong-oracle controls complete");
                report.status = "PASS_NATIVE_UNITY6_94_BATCH_KEYS";
            }
            catch (Exception error)
            {
                report.error = error.ToString();
                if (report.failures.Count == 0) report.errors.Add(error.GetType().Name + ": " + error.Message);
            }
            finally
            {
                // These Editor fixture objects are owned locally. Immediate
                // cleanup avoids making a claim about runtime deferred Dispose.
                if (root)
                {
                    foreach (var filter in root.GetComponentsInChildren<MeshFilter>(true))
                        if (filter.sharedMesh) Object.DestroyImmediate(filter.sharedMesh);
                    Object.DestroyImmediate(root);
                }
                if (first) Object.DestroyImmediate(first);
                if (samePage) Object.DestroyImmediate(samePage);
                if (otherPage) Object.DestroyImmediate(otherPage);
                if (textureA) Object.DestroyImmediate(textureA);
                if (textureB) Object.DestroyImmediate(textureB);
                nativeOrders.Clear();
                using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
                using (var writer = new StreamWriter(stream, new UTF8Encoding(false))) writer.Write(JsonUtility.ToJson(report, true));
            }
            EditorApplication.Exit(report.status == "PASS_NATIVE_UNITY6_94_BATCH_KEYS" ? 0 : 1);
        }

        static string SafeOutput()
        {
            var project = new DirectoryInfo(Path.GetFullPath(Path.Combine(Application.dataPath, "..")));
            if (project.Name != "Project" || project.Parent == null || project.Parent.Name != "Unity6Migration94" || project.Parent.Parent == null || project.Parent.Parent.Name != ".verification-cache")
                throw new InvalidOperationException("Only the explicitly approved isolated project is accepted.");
            string version = Environment.GetEnvironmentVariable("HOTR_UNITY6_94_VERSION");
            if (string.IsNullOrWhiteSpace(version) || !version.StartsWith("6000.", StringComparison.Ordinal) || Application.unityVersion != version)
                throw new InvalidOperationException("Exact pinned Unity 6 version required.");
            string supplied = Environment.GetEnvironmentVariable("HOTR_UNITY6_94_OUT");
            if (string.IsNullOrWhiteSpace(supplied) || !Path.IsPathRooted(supplied)) throw new InvalidOperationException("Explicit absolute evidence output required.");
            string directory = Path.GetFullPath(supplied);
            string evidence = Path.Combine(project.Parent.Parent.Parent.FullName, "Verification", "Evidence") + Path.DirectorySeparatorChar;
            if (!directory.StartsWith(evidence, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Evidence output must stay inside the workspace.");
            foreach (string value in new[] { project.FullName, directory })
                for (var node = new DirectoryInfo(value); node != null; node = node.Parent)
                    if (node.Exists && (node.Attributes & FileAttributes.ReparsePoint) != 0) throw new InvalidOperationException("Reparse point refused.");
            Directory.CreateDirectory(directory);
            string result = Path.Combine(directory, "BatchKeys.json");
            if (File.Exists(result)) throw new InvalidOperationException("Existing native report is preserved.");
            return result;
        }

        static void Check(bool condition, string message)
        {
            report.checks++;
            if (!condition) { report.failures.Add(message); throw new InvalidOperationException(message); }
            report.passed.Add(message);
        }

        static Texture2D Texture(string name, Color32 color)
        {
            var result = new Texture2D(4, 4, TextureFormat.RGBA32, false) { name = name };
            result.SetPixels32(Enumerable.Repeat(color, 16).ToArray());
            result.Apply(false, false);
            return result;
        }

        static void RecordDirectOrderReadbacks(IEnumerable<int> requested)
        {
            foreach (int order in requested)
            {
                if (nativeOrders.ContainsKey(order)) continue;
                var control = new GameObject("Direct native sorting-order control");
                try
                {
                    var renderer = control.AddComponent<MeshRenderer>();
                    renderer.sortingOrder = order;
                    int actual = renderer.sortingOrder, clamp = Mathf.Clamp(order, short.MinValue, short.MaxValue);
                    nativeOrders.Add(order, actual);
                    report.orders.Add(new OrderRow { requested = order, nativeReadback = actual, mathematicalClamp = clamp, matchesClamp = actual == clamp });
                }
                finally { Object.DestroyImmediate(control); }
            }
        }

        static List<Group> Expected(Input[] input, bool ordered, int wrongMode = 0)
        {
            var groups = new List<Group>();
            foreach (var value in input)
            {
                Texture2D texture = value.sprite.texture;
                Group found = null;
                if (ordered || wrongMode == 3)
                {
                    if (groups.Count > 0)
                    {
                        var last = groups[groups.Count - 1];
                        if (last.texture == texture && last.order == value.order) found = last;
                    }
                }
                else
                    foreach (var group in groups)
                        if ((wrongMode == 2 || group.texture == texture) && (wrongMode == 1 || group.order == value.order)) { found = group; break; }
                if (found == null) { found = new Group { texture = texture, order = value.order }; groups.Add(found); }
                found.quads++;
            }
            return groups;
        }

        static void NegativeControls(Input[] input)
        {
            var correct = Expected(input, false);
            Check(correct.Count == 8, "Reference pages times four full requested orders produce exactly eight unique groups");
            foreach (int wrong in new[] { 1, 2, 3 })
            {
                Check(Expected(input, false, wrong).Count != correct.Count, "Independent oracle rejects deliberately wrong grouping mode " + wrong);
                report.negativeControls++;
            }
            Check(Expected(input, true).Count != correct.Count, "Ordered A/B/A runs reject deliberately wrong unique-group oracle");
            report.negativeControls++;
        }

        static void VerifyFrame(string name, EffectMeshBatcher batch, GameObject root, Material material, Input[] input, bool ordered)
        {
            var expected = Expected(input, ordered);
            var row = new FrameRow { name = name, ordered = ordered, inputs = input.Length, expectedGroups = expected.Count };
            report.frames.Add(row);
            batch.KeepDrawOrder = ordered;
            batch.Begin();
            for (int index = 0; index < input.Length; index++)
                batch.Add(input[index].sprite, input[index].order, new Vector3(index * .1f, 0, 0), 0, 1, 1, Color.white);
            batch.End();
            var filters = root.GetComponentsInChildren<MeshFilter>(true).Where(filter => filter.GetComponent<MeshRenderer>().enabled).ToArray();
            row.activeMeshes = filters.Length;
            Check(batch.Quads == input.Length && batch.Meshes == expected.Count && filters.Length == expected.Count, name + ": full requested texture/order groups and active mesh counts match the independent oracle");
            for (int index = 0; index < expected.Count; index++)
            {
                var group = expected[index];
                var renderer = filters[index].GetComponent<MeshRenderer>();
                var mesh = filters[index].sharedMesh;
                var block = new MaterialPropertyBlock(); renderer.GetPropertyBlock(block);
                row.groups.Add(new GroupRow { texture = group.texture.name, requestedOrder = group.order,
                    expectedRendererOrder = nativeOrders[group.order], actualRendererOrder = renderer.sortingOrder, quads = group.quads, vertices = mesh.vertexCount });
                Check(renderer.sharedMaterial == material && block.GetTexture(Shader.PropertyToID("_MainTex")) == group.texture, name + ": group " + index + " retains the exact material and native texture reference");
                Check(renderer.sortingOrder == nativeOrders[group.order], name + ": group " + index + " retains direct native sorting-order readback for requested " + group.order);
                Check(mesh.vertexCount == group.quads * 4 && mesh.triangles.Length == group.quads * 6, name + ": group " + index + " uploads exactly its active quad prefix");
            }
        }
    }
}
#endif
