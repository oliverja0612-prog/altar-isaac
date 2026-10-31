using System.IO;
using System.IO.Compression;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json.Nodes;

namespace Altar.Core;

/// <summary>A mod from the Altar library (registry/index.json on the site): approved by the admins,
/// passed the safety check, and pinned to one commit + sha256.</summary>
public record RegistryMod(string Id, string Name, string Version, string Author, string Description, string Repo,
                          string Commit, string Folder, string Download, string ZipRoot, string Sha256, long Size, int Warnings)
{
    public static RegistryMod? From(JsonNode? n)
    {
        string S(string k) => n?[k]?.GetValue<string>() ?? "";
        if (n == null || S("id") == "" || S("download") == "" || S("sha256") == "") return null;
        return new RegistryMod(S("id"), S("name"), S("version"), S("author"), S("description"), S("repo"), S("commit"),
                               S("folder"), S("download"), S("zip_root"), S("sha256"),
                               n["size"]?.GetValue<long>() ?? 0, n["warnings"]?.GetValue<int>() ?? 0);
    }
}

/// <summary>Installs and updates library mods. What's installed lives in config "registry_mods":
/// { id: { folder, commit, version } }.</summary>
public static class ModLibrary
{
    public static readonly string IndexUrl = Environment.GetEnvironmentVariable("ALTAR_LIBRARY_URL")
        ?? "https://oliverja0612-prog.github.io/altar-isaac/registry/index.json";
    static readonly HttpClient Http = CreateClient();

    static HttpClient CreateClient()
    {
        var c = new HttpClient { Timeout = TimeSpan.FromMinutes(5) };
        c.DefaultRequestHeaders.UserAgent.ParseAdd("Altar-Mod-Manager");
        return c;
    }

    public static async Task<List<RegistryMod>> FetchAsync()
    {
        var json = JsonNode.Parse(await Http.GetStringAsync(IndexUrl + "?t=" + DateTimeOffset.UtcNow.ToUnixTimeSeconds()));
        return ((json?["mods"] as JsonArray) ?? new JsonArray())
            .Select(RegistryMod.From).OfType<RegistryMod>()
            .Where(m => SafeFolder(m.Folder) && !m.Folder.Equals(Config.ModFolder, StringComparison.OrdinalIgnoreCase))
            .ToList();
    }

    static bool SafeFolder(string f) =>
        f != "" && f != "." && f != ".." && f.IndexOfAny(Path.GetInvalidFileNameChars()) < 0;

    public static Dictionary<string, (string folder, string commit, string version)> Installed()
    {
        var result = new Dictionary<string, (string, string, string)>();
        if (Config.Load()["registry_mods"] is JsonObject o)
            foreach (var (id, v) in o)
                result[id] = (v?["folder"]?.GetValue<string>() ?? "", v?["commit"]?.GetValue<string>() ?? "",
                              v?["version"]?.GetValue<string>() ?? "");
        return result;
    }

    static void Track(RegistryMod m, bool installed)
    {
        var cfg = Config.Load();
        var o = cfg["registry_mods"] as JsonObject ?? new JsonObject();
        if (installed) o[m.Id] = new JsonObject { ["folder"] = m.Folder, ["commit"] = m.Commit, ["version"] = m.Version };
        else o.Remove(m.Id);
        cfg["registry_mods"] = o;
        Config.Save(cfg);
    }

    /// <summary>"install", "update" or "installed" for this library mod in this game folder.</summary>
    public static string StateOf(ModStore store, RegistryMod m)
    {
        if (!Installed().TryGetValue(m.Id, out var mine) || !Directory.Exists(Path.Combine(store.ModsDir, mine.folder)))
            return "install";
        return mine.commit == m.Commit ? "installed" : "update";
    }

    /// <summary>True if the folder holds a mod Altar didn't install from the library (asks before replacing it).</summary>
    public static bool ForeignFolder(ModStore store, RegistryMod m) =>
        Directory.Exists(Path.Combine(store.ModsDir, m.Folder)) &&
        !Installed().Any(kv => kv.Key == m.Id && kv.Value.folder.Equals(m.Folder, StringComparison.OrdinalIgnoreCase));

    /// <summary>Downloads the pinned zip, checks its sha256 against the library, and swaps it into mods/&lt;folder&gt;.
    /// The mod keeps its enabled/disabled state.</summary>
    public static async Task InstallAsync(ModStore store, RegistryMod m, IProgress<double>? progress = null)
    {
        var tmp = Path.Combine(Path.GetTempPath(), $"altar-{m.Id}-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tmp);
        try
        {
            var zip = Path.Combine(tmp, "mod.zip");
            using (var resp = await Http.GetAsync(m.Download, HttpCompletionOption.ResponseHeadersRead))
            {
                resp.EnsureSuccessStatusCode();
                var total = resp.Content.Headers.ContentLength ?? m.Size;
                await using var src = await resp.Content.ReadAsStreamAsync();
                await using var dst = File.Create(zip);
                var buf = new byte[81920];
                long done = 0; int n;
                while ((n = await src.ReadAsync(buf)) > 0)
                {
                    await dst.WriteAsync(buf.AsMemory(0, n));
                    done += n;
                    if (total > 0) progress?.Report(Math.Min(1, (double)done / total) * 0.9);
                }
            }
            string hash;
            await using (var f = File.OpenRead(zip)) hash = Convert.ToHexString(await SHA256.HashDataAsync(f));
            // GitHub re-zips on demand; if it ever recompresses, the archive comment still names the exact commit
            if (!hash.Equals(m.Sha256, StringComparison.OrdinalIgnoreCase) && ZipComment(zip) != m.Commit)
                throw new InvalidOperationException("The download doesn't match what the admins approved (sha256 differs). Nothing was installed.");

            var staged = Path.Combine(tmp, "mod");
            await Task.Run(() => Extract(zip, m.ZipRoot, staged));
            progress?.Report(0.95);

            var dest = Path.Combine(store.ModsDir, m.Folder);
            bool wasDisabled = File.Exists(Path.Combine(dest, "disable.it"));
            if (Directory.Exists(dest))
            {
                Directory.CreateDirectory(Config.RemovedModsDir);
                Directory.Move(dest, Path.Combine(Config.RemovedModsDir, $"{m.Folder}_{DateTimeOffset.Now.ToUnixTimeSeconds()}"));
            }
            Directory.CreateDirectory(store.ModsDir);
            Directory.Move(staged, dest);
            if (wasDisabled) File.WriteAllText(Path.Combine(dest, "disable.it"), "");
            Track(m, true);
            progress?.Report(1);
        }
        finally
        {
            try { Directory.Delete(tmp, true); } catch (Exception) { /* temp; Windows cleans it */ }
        }
    }

    /// <summary>The zip's end-of-archive comment (GitHub puts the commit sha there).</summary>
    static string ZipComment(string zip)
    {
        var bytes = File.ReadAllBytes(zip);
        for (int i = bytes.Length - 22; i >= Math.Max(0, bytes.Length - 22 - 65535); i--)
        {
            if (bytes[i] != 0x50 || bytes[i + 1] != 0x4b || bytes[i + 2] != 0x05 || bytes[i + 3] != 0x06) continue;
            int len = bytes[i + 20] | bytes[i + 21] << 8;
            return i + 22 + len <= bytes.Length ? System.Text.Encoding.ASCII.GetString(bytes, i + 22, len) : "";
        }
        return "";
    }

    static void Extract(string zip, string root, string dest)
    {
        using var z = ZipFile.OpenRead(zip);
        var destFull = Path.GetFullPath(dest) + Path.DirectorySeparatorChar;
        int count = 0;
        foreach (var e in z.Entries)
        {
            if (e.FullName.EndsWith("/") || !e.FullName.StartsWith(root, StringComparison.Ordinal)) continue;
            var target = Path.GetFullPath(Path.Combine(dest, e.FullName[root.Length..]));
            if (!target.StartsWith(destFull, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException($"Unsafe path in the mod: {e.FullName}");
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            e.ExtractToFile(target, true);
            count++;
        }
        if (count == 0) throw new InvalidOperationException("The mod's folder wasn't in the download.");
    }

    /// <summary>Moves the mod to removed_mods (restorable) and forgets it.</summary>
    public static void Uninstall(ModStore store, RegistryMod m)
    {
        var dir = Path.Combine(store.ModsDir, m.Folder);
        if (Directory.Exists(dir)) store.Uninstall(new Mod(store.ModsDir, m.Folder));
        Track(m, false);
    }

    /// <summary>Updates every installed library mod that has a newer approved version. Returns their names.</summary>
    public static async Task<List<string>> UpdateAllAsync(ModStore store, IEnumerable<RegistryMod>? known = null)
    {
        var updated = new List<string>();
        if (Installed().Count == 0 || SaveGuard.GameRunning) return updated;
        foreach (var m in known ?? await FetchAsync())
        {
            if (StateOf(store, m) != "update") continue;
            try { await InstallAsync(store, m); updated.Add(m.Name); }
            catch (Exception) { /* try again next start */ }
        }
        return updated;
    }
}
