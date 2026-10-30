using System.IO;
using System.IO.Compression;
using System.Text;
using System.Xml.Linq;

namespace Altar.Core;

/// <summary>One mod folder. Enabled = no disable.it file (the game's own rule).</summary>
public class Mod
{
    public string Folder { get; }
    public string Path { get; }
    public string Name { get; private set; }
    public string Version { get; private set; } = "?";
    public string Description { get; private set; } = "";
    public string WorkshopId { get; private set; } = "";
    public bool IsCore => Folder == Config.ModFolder;

    public Mod(string modsDir, string folder)
    {
        Folder = folder;
        Path = System.IO.Path.Combine(modsDir, folder);
        Name = folder;
        ReadMetadata();
    }

    void ReadMetadata()
    {
        var meta = System.IO.Path.Combine(Path, "metadata.xml");
        if (!File.Exists(meta)) return;
        try
        {
            // some workshop files carry stray bytes; decode leniently
            var xml = XDocument.Parse(Encoding.UTF8.GetString(File.ReadAllBytes(meta)).TrimStart('﻿'));
            var root = xml.Root!;
            Name = (root.Element("name")?.Value ?? Folder).Trim();
            Version = (root.Element("version")?.Value ?? "?").Trim();
            Description = string.Join(" ", (root.Element("description")?.Value ?? "")
                .Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
            WorkshopId = (root.Element("id")?.Value ?? "").Trim();
        }
        catch (Exception) { /* keep folder name */ }
    }

    public bool Enabled
    {
        get => !File.Exists(System.IO.Path.Combine(Path, "disable.it"));
        set
        {
            var flag = System.IO.Path.Combine(Path, "disable.it");
            if (value && File.Exists(flag)) File.Delete(flag);
            else if (!value && !File.Exists(flag)) File.WriteAllText(flag, "");
        }
    }

    public string? Thumb => new[] { "thumb.png", "thumbnail.png", "icon.png" }
        .Select(n => System.IO.Path.Combine(Path, n)).FirstOrDefault(File.Exists);

    public IEnumerable<string> Files()
    {
        if (!Directory.Exists(Path)) yield break;
        foreach (var f in Directory.EnumerateFiles(Path, "*", SearchOption.AllDirectories))
            yield return System.IO.Path.GetRelativePath(Path, f).Replace('\\', '/');
    }

    public (int files, long bytes) Stats()
    {
        int n = 0; long size = 0;
        foreach (var f in Directory.EnumerateFiles(Path, "*", SearchOption.AllDirectories))
        {
            n++;
            try { size += new FileInfo(f).Length; } catch (Exception) { }
        }
        return (n, size);
    }

    public string Kind
    {
        get
        {
            var tags = new List<string>();
            if (File.Exists(System.IO.Path.Combine(Path, "main.lua"))) tags.Add("Lua");
            if (Directory.Exists(System.IO.Path.Combine(Path, "resources"))) tags.Add("Resources");
            if (Directory.Exists(System.IO.Path.Combine(Path, "content"))) tags.Add("Content");
            return tags.Count > 0 ? string.Join(", ", tags) : "-";
        }
    }
}

/// <summary>Everything the app does to the mods folder.</summary>
public class ModStore
{
    public string GameDir { get; }
    public string ModsDir => System.IO.Path.Combine(GameDir, "mods");
    public string GameExe => System.IO.Path.Combine(GameDir, GameLocator.GameExe);
    string ModListLua => System.IO.Path.Combine(ModsDir, Config.ModFolder, "altar_modlist.lua");

    public ModStore(string gameDir) => GameDir = gameDir;

    public List<Mod> Scan()
    {
        Directory.CreateDirectory(ModsDir);
        return Directory.GetDirectories(ModsDir)
            .Select(d => new Mod(ModsDir, System.IO.Path.GetFileName(d)))
            .OrderBy(m => m.Name, StringComparer.OrdinalIgnoreCase).ToList();
    }

    /// <summary>Files under resources/ that more than one enabled mod replaces (content/*.xml merges, so it's skipped).</summary>
    public static Dictionary<string, List<string>> Conflicts(IEnumerable<Mod> mods)
    {
        var owners = new Dictionary<string, List<string>>();
        foreach (var m in mods.Where(m => m.Enabled))
            foreach (var f in m.Files())
            {
                if (!(f.StartsWith("resources/") || f.StartsWith("content/"))) continue;
                if (f.StartsWith("content/") && f.EndsWith(".xml")) continue;
                if (!owners.TryGetValue(f, out var list)) owners[f] = list = new List<string>();
                list.Add(m.Name);
            }
        return owners.Where(kv => kv.Value.Count > 1).ToDictionary(kv => kv.Key, kv => kv.Value);
    }

    static string LuaStr(string s) =>
        "\"" + new string(s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "").Replace("\n", "\\n")
            .Select(c => c < 32 ? ' ' : c).ToArray()) + "\"";

    /// <summary>The in-game Altar menu reads this to list your mods.</summary>
    public void WriteModList(IEnumerable<Mod> mods)
    {
        if (!Directory.Exists(System.IO.Path.GetDirectoryName(ModListLua))) return;
        var sb = new StringBuilder("-- Generated by Altar Mod Manager. Do not edit.\nreturn {\n");
        foreach (var m in mods)
            sb.Append($"\t{{ name = {LuaStr(m.Name)}, version = {LuaStr(m.Version)}, folder = {LuaStr(m.Folder)}, " +
                      $"enabled = {(m.Enabled ? "true" : "false")}, description = {LuaStr(m.Description.Length > 160 ? m.Description[..160] : m.Description)} }},\n");
        sb.Append("}\n");
        File.WriteAllText(ModListLua, sb.ToString());
    }

    /// <summary>Installs a mod .zip; returns the folder name, or null if the user declined a replace.</summary>
    public string? InstallZip(string zipPath, Func<string, bool> confirmReplace)
    {
        using var z = ZipFile.OpenRead(zipPath);
        var names = z.Entries.Where(e => !e.FullName.EndsWith("/")).ToList();
        var meta = names.Where(e => e.FullName.EndsWith("metadata.xml", StringComparison.OrdinalIgnoreCase)
                                 || e.FullName.EndsWith("main.lua", StringComparison.OrdinalIgnoreCase)).ToList();
        if (meta.Count == 0) throw new InvalidOperationException("No metadata.xml or main.lua in the archive - not an Isaac mod.");
        var rootEntry = meta.OrderBy(e => e.FullName.Count(c => c == '/')).First().FullName;
        var root = rootEntry.Contains('/') ? rootEntry[..rootEntry.LastIndexOf('/')] : "";
        var folder = root != "" ? root.Split('/').Last() : System.IO.Path.GetFileNameWithoutExtension(zipPath);
        var dest = System.IO.Path.Combine(ModsDir, folder);
        if (Directory.Exists(dest))
        {
            if (!confirmReplace(folder)) return null;
            Directory.Delete(dest, true);
        }
        var destFull = System.IO.Path.GetFullPath(dest) + System.IO.Path.DirectorySeparatorChar;
        foreach (var e in names)
        {
            if (root != "" && !e.FullName.StartsWith(root + "/")) continue;
            var rel = root != "" ? e.FullName[(root.Length + 1)..] : e.FullName;
            var target = System.IO.Path.GetFullPath(System.IO.Path.Combine(dest, rel));
            if (!target.StartsWith(destFull, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException($"Unsafe path in archive: {e.FullName}");
            Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target)!);
            e.ExtractToFile(target, true);
        }
        return folder;
    }

    /// <summary>Moves a mod to %APPDATA%\Altar\removed_mods so it can be restored.</summary>
    public void Uninstall(Mod m)
    {
        Directory.CreateDirectory(Config.RemovedModsDir);
        Directory.Move(m.Path, System.IO.Path.Combine(Config.RemovedModsDir, $"{m.Folder}_{DateTimeOffset.Now.ToUnixTimeSeconds()}"));
    }

    public static string HumanSize(long n)
    {
        string[] units = { "B", "KB", "MB", "GB" };
        double v = n; int u = 0;
        while (v >= 1024 && u < units.Length - 1) { v /= 1024; u++; }
        return u == 0 ? $"{v:0} {units[u]}" : $"{v:0.0} {units[u]}";
    }
}
