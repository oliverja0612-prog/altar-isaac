using System.IO;
using System.Text.RegularExpressions;
using Microsoft.Win32;

namespace Altar.Core;

/// <summary>Finds Isaac installs: --game, config, next to this exe, Steam libraries, Downloads.</summary>
public static class GameLocator
{
    public const string GameExe = "isaac-ng.exe";

    public static bool IsGameDir(string? path) =>
        !string.IsNullOrWhiteSpace(path) && File.Exists(Path.Combine(path, GameExe));

    public static List<string> FindAll(string? extra = null)
    {
        var found = new List<string>();
        void Add(string? p)
        {
            if (!IsGameDir(p)) return;
            var full = Path.GetFullPath(p!);
            if (!found.Any(f => string.Equals(f, full, StringComparison.OrdinalIgnoreCase))) found.Add(full);
        }

        Add(extra);
        Add(Config.GetString("game_dir"));
        var exeDir = AppContext.BaseDirectory.TrimEnd('\\');
        Add(Path.GetDirectoryName(exeDir));   // running from <game>\AltarModManager\
        Add(exeDir);
        foreach (var lib in SteamLibraries())
            Add(Path.Combine(lib, "steamapps", "common", "The Binding of Isaac Rebirth"));
        foreach (var drive in "CDEFG")
        {
            Add($@"{drive}:\Games\The Binding of Isaac Rebirth");
            Add($@"{drive}:\SteamLibrary\steamapps\common\The Binding of Isaac Rebirth");
        }
        var downloads = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
        try
        {
            foreach (var dir in Directory.GetDirectories(downloads).Where(d => d.Contains("isaac", StringComparison.OrdinalIgnoreCase)))
            {
                Add(dir);
                foreach (var sub in Directory.GetDirectories(dir)) Add(sub);
            }
        }
        catch (Exception) { /* no Downloads folder */ }
        return found;
    }

    static IEnumerable<string> SteamLibraries()
    {
        var roots = new List<string>();
        foreach (var (hive, key) in new[] { (Registry.CurrentUser, @"Software\Valve\Steam"),
                                             (Registry.LocalMachine, @"SOFTWARE\WOW6432Node\Valve\Steam") })
        {
            try
            {
                using var k = hive.OpenSubKey(key);
                foreach (var name in new[] { "SteamPath", "InstallPath" })
                    if (k?.GetValue(name) is string s) roots.Add(s);
            }
            catch (Exception) { }
        }
        roots.Add(@"C:\Program Files (x86)\Steam");
        var libs = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var root in roots)
        {
            var r = root.Replace('/', '\\');
            if (Directory.Exists(r)) libs.Add(r);
            var vdf = Path.Combine(r, "steamapps", "libraryfolders.vdf");
            if (!File.Exists(vdf)) continue;
            foreach (Match m in Regex.Matches(File.ReadAllText(vdf), "\"path\"\\s+\"([^\"]+)\""))
                libs.Add(m.Groups[1].Value.Replace(@"\\", @"\"));
        }
        return libs;
    }
}
