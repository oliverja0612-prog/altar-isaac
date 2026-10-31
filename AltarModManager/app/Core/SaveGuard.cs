using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Win32;

namespace Altar.Core;

/// <summary>
/// Safe mode: runs played with mods don't count. The save files (unlocks, stats,
/// streaks, saved runs) are copied when Isaac starts with mods enabled and put back
/// when it closes. The modded versions are kept in safe_mode\discarded, never deleted.
/// </summary>
public static class SaveGuard
{
    static readonly string Dir = Path.Combine(Config.Dir, "safe_mode");
    static readonly string FilesDir = Path.Combine(Dir, "snapshot");
    static readonly string DiscardDir = Path.Combine(Dir, "discarded");
    static readonly string ManifestPath = Path.Combine(Dir, "snapshot.json");
    static readonly string[] Patterns = { "*persistentgamedata*.dat", "*gamestate*.dat" };
    const int KeepDiscarded = 5;

    /// <summary>A snapshot is waiting to be restored.</summary>
    public static bool Active => File.Exists(ManifestPath);

    public static bool GameRunning => Process.GetProcessesByName("isaac-ng").Length > 0;

    public static DateTime? SnapshotTime
    {
        get
        {
            try { return DateTime.Parse(Manifest()?["created"]?.GetValue<string>() ?? ""); }
            catch (Exception) { return null; }
        }
    }

    /// <summary>Where Repentance(+) keeps saves: My Games when cloud saves are off, Steam userdata when on.</summary>
    public static Func<List<string>> SaveDirs = FindSaveDirs;

    static List<string> FindSaveDirs()
    {
        var dirs = new List<string>();
        // Documents may be redirected to OneDrive while Isaac still writes to the profile's own Documents
        var docs = new[]
        {
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Documents"),
        };
        foreach (var doc in docs.Distinct(StringComparer.OrdinalIgnoreCase))
            foreach (var name in new[] { "Binding of Isaac Repentance+", "Binding of Isaac Repentance" })
                dirs.Add(Path.Combine(doc, "My Games", name));
        foreach (var steam in SteamRoots())
        {
            var userdata = Path.Combine(steam, "userdata");
            if (!Directory.Exists(userdata)) continue;
            foreach (var user in Directory.GetDirectories(userdata))
                dirs.Add(Path.Combine(user, "250900", "remote"));
        }
        return dirs.Where(d => Directory.Exists(d) && SaveFiles(d).Any()).ToList();
    }

    static IEnumerable<string> SteamRoots()
    {
        var roots = new List<string> { @"C:\Program Files (x86)\Steam" };
        try
        {
            using var k = Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam");
            if (k?.GetValue("SteamPath") is string s) roots.Insert(0, s.Replace('/', '\\'));
        }
        catch (Exception) { }
        return roots.Distinct(StringComparer.OrdinalIgnoreCase);
    }

    static IEnumerable<string> SaveFiles(string dir) =>
        Patterns.SelectMany(p => Directory.EnumerateFiles(dir, p, SearchOption.TopDirectoryOnly))
                .Distinct(StringComparer.OrdinalIgnoreCase);

    static JsonObject? Manifest()
    {
        try { return JsonNode.Parse(File.ReadAllText(ManifestPath)) as JsonObject; }
        catch (Exception) { return null; }
    }

    /// <summary>Copies every save file aside. Returns how many were saved (0 if one is already held).</summary>
    public static int Snapshot()
    {
        if (Active) return 0;
        if (Directory.Exists(FilesDir)) Directory.Delete(FilesDir, true);
        Directory.CreateDirectory(FilesDir);
        var dirs = SaveDirs();
        var files = new JsonArray();
        int i = 0;
        foreach (var file in dirs.SelectMany(SaveFiles))
        {
            var copy = Path.Combine(FilesDir, $"{i++}.dat");
            File.Copy(file, copy, true);
            files.Add(new JsonObject { ["orig"] = file, ["copy"] = copy });
        }
        var manifest = new JsonObject
        {
            ["created"] = DateTime.Now.ToString("o"),
            ["dirs"] = new JsonArray(dirs.Select(d => (JsonNode)JsonValue.Create(d)!).ToArray()),
            ["files"] = files,
        };
        // written last: the snapshot only counts once every copy is on disk
        File.WriteAllText(ManifestPath, manifest.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
        return i;
    }

    /// <summary>Puts the snapshot back. Saves the modded session wrote are moved to discarded\, not deleted.</summary>
    public static int Restore()
    {
        var manifest = Manifest();
        if (manifest == null) { Clear(); return 0; }
        var stamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
        var discard = Path.Combine(DiscardDir, stamp);
        var originals = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        int restored = 0;

        void Discard(string file)
        {
            var target = Path.Combine(discard, Path.GetFileName(Path.GetDirectoryName(file)!) + "_" + Path.GetFileName(file));
            Directory.CreateDirectory(discard);
            File.Copy(file, target, true);
        }

        foreach (var entry in (manifest["files"] as JsonArray ?? new JsonArray()).OfType<JsonObject>())
        {
            var orig = entry["orig"]!.GetValue<string>();
            var copy = entry["copy"]!.GetValue<string>();
            originals.Add(orig);
            if (!File.Exists(copy)) continue;
            if (File.Exists(orig)) Discard(orig);
            File.Copy(copy, orig, true);
            restored++;
        }
        // a run saved during the modded session didn't exist before it: take it out too
        foreach (var dir in (manifest["dirs"] as JsonArray ?? new JsonArray()).Select(d => d!.GetValue<string>()))
        {
            if (!Directory.Exists(dir)) continue;
            foreach (var file in SaveFiles(dir).Where(f => !originals.Contains(f)).ToList())
            {
                Discard(file);
                File.Delete(file);
            }
        }
        Clear();
        PruneDiscarded();
        return restored;
    }

    /// <summary>Drops the snapshot without restoring (the modded progress is kept).</summary>
    public static void Clear()
    {
        if (File.Exists(ManifestPath)) File.Delete(ManifestPath);
        if (Directory.Exists(FilesDir)) Directory.Delete(FilesDir, true);
    }

    static void PruneDiscarded()
    {
        if (!Directory.Exists(DiscardDir)) return;
        foreach (var old in Directory.GetDirectories(DiscardDir).OrderByDescending(d => d).Skip(KeepDiscarded))
        {
            try { Directory.Delete(old, true); } catch (Exception) { }
        }
    }

    public static string FolderToOpen => Directory.Exists(Dir) ? Dir : Config.Dir;
}
