using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace Altar.Core;

/// <summary>
/// Forwards copied text into Altar Core's save data so Ctrl+V works in the game's
/// console (the Lua sandbox can't read the clipboard). Only the "clip" key is touched.
/// </summary>
public static class ClipboardBridge
{
    public static void Push(string gameDir, string text)
    {
        var dataDir = Path.Combine(gameDir, "data", Config.ModFolder);
        Directory.CreateDirectory(dataDir);
        var files = Directory.GetFiles(dataDir).Where(f => Regex.IsMatch(Path.GetFileName(f), @"^save\d\.dat$")).ToList();
        if (files.Count == 0) files = new[] { 1, 2, 3 }.Select(i => Path.Combine(dataDir, $"save{i}.dat")).ToList();
        foreach (var path in files)
        {
            JsonObject data;
            try
            {
                data = File.Exists(path) ? (JsonNode.Parse(File.ReadAllText(path)) as JsonObject ?? new JsonObject())
                                         : new JsonObject();
            }
            catch (Exception) { continue; } // never clobber a file we can't read
            data["clip"] = text.Length > 400 ? text[..400] : text;
            File.WriteAllText(path, data.ToJsonString());
        }
    }
}

public record ReleaseInfo(string Tag, string DownloadUrl, long Size);

/// <summary>Checks GitHub releases and runs the installer in --update mode.</summary>
public static class Updater
{
    static readonly HttpClient Http = CreateClient();

    static HttpClient CreateClient()
    {
        var c = new HttpClient { Timeout = TimeSpan.FromMinutes(3) };
        c.DefaultRequestHeaders.UserAgent.ParseAdd("Altar-Mod-Manager");
        return c;
    }

    public static async Task<ReleaseInfo?> CheckAsync()
    {
        var json = await Http.GetStringAsync($"https://api.github.com/repos/{Config.GitHubRepo}/releases/latest");
        var rel = JsonNode.Parse(json)!;
        var tag = rel["tag_name"]?.GetValue<string>() ?? "";
        var asset = (rel["assets"] as JsonArray)?.FirstOrDefault(a =>
            a?["name"]?.GetValue<string>().EndsWith(".exe", StringComparison.OrdinalIgnoreCase) == true);
        if (asset == null || Config.ParseVersion(tag) <= Config.ParseVersion(Config.Version)) return null;
        return new ReleaseInfo(tag, asset["browser_download_url"]!.GetValue<string>(), asset["size"]?.GetValue<long>() ?? 0);
    }

    public static async Task<string> DownloadAsync(ReleaseInfo rel, IProgress<double> progress)
    {
        var path = Path.Combine(Path.GetTempPath(), $"AltarSetup-{rel.Tag}.exe");
        using var resp = await Http.GetAsync(rel.DownloadUrl, HttpCompletionOption.ResponseHeadersRead);
        resp.EnsureSuccessStatusCode();
        var total = resp.Content.Headers.ContentLength ?? rel.Size;
        await using var src = await resp.Content.ReadAsStreamAsync();
        await using var dst = File.Create(path);
        var buf = new byte[81920];
        long done = 0; int n;
        while ((n = await src.ReadAsync(buf)) > 0)
        {
            await dst.WriteAsync(buf.AsMemory(0, n));
            done += n;
            if (total > 0) progress.Report((double)done / total);
        }
        return path;
    }

    /// <summary>The installer replaces Altar.exe, so the app exits right after starting it.</summary>
    public static void RunInstaller(string path) =>
        Process.Start(new ProcessStartInfo(path, "--update") { UseShellExecute = true });
}
