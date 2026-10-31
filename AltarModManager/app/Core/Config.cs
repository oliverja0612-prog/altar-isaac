using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Altar.Core;

/// <summary>
/// %APPDATA%\Altar\config.json, shared with the installer (game_dir, profiles,
/// clipboard_link, auto_update). Unknown keys are preserved.
/// </summary>
public static class Config
{
    public const string Version = "1.0.0";
    public const string GitHubRepo = "oliverja0612-prog/altar-isaac";
    public const string ModFolder = "altar_core";

    public static readonly string Dir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Altar");
    static readonly string FilePath = Path.Combine(Dir, "config.json");
    public static readonly string RemovedModsDir = Path.Combine(Dir, "removed_mods");

    public static JsonObject Load()
    {
        try
        {
            if (File.Exists(FilePath) && JsonNode.Parse(File.ReadAllText(FilePath)) is JsonObject o) return o;
        }
        catch (Exception) { /* a broken config just starts fresh */ }
        return new JsonObject();
    }

    public static void Save(JsonObject cfg)
    {
        Directory.CreateDirectory(Dir);
        File.WriteAllText(FilePath, cfg.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
    }

    public static string? GetString(string key) => Load()[key]?.GetValue<string>();

    public static bool GetBool(string key, bool fallback)
    {
        try { return Load()[key]?.GetValue<bool>() ?? fallback; }
        catch (Exception) { return fallback; }
    }

    public static void Set(string key, JsonNode? value)
    {
        var cfg = Load();
        cfg[key] = value;
        Save(cfg);
    }

    public static Dictionary<string, List<string>> Profiles()
    {
        var result = new Dictionary<string, List<string>>();
        if (Load()["profiles"] is JsonObject p)
            foreach (var (name, list) in p)
                if (list is JsonArray arr)
                    result[name] = arr.Select(x => x?.GetValue<string>() ?? "").Where(x => x != "").ToList();
        return result;
    }

    public static void SaveProfiles(Dictionary<string, List<string>> profiles)
    {
        var obj = new JsonObject();
        foreach (var (name, mods) in profiles)
            obj[name] = new JsonArray(mods.Select(m => (JsonNode)JsonValue.Create(m)!).ToArray());
        Set("profiles", obj);
    }

    /// <summary>"v1.0.0" -> (1,0,0); unparsable sorts lowest.</summary>
    public static Version ParseVersion(string v) =>
        System.Version.TryParse(v.TrimStart('v', 'V'), out var parsed) ? parsed : new Version(0, 0);
}
