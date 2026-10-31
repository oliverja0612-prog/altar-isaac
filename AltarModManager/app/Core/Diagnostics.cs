using System.IO;
using System.Text;

namespace Altar.Core;

/// <summary>Crash logs for the app, and the Altar errors the mod's crash guard writes to Isaac's log.txt.</summary>
public static class Diagnostics
{
    public static readonly string CrashDir = Path.Combine(Config.Dir, "crashes");
    const int KeepCrashLogs = 20;

    /// <summary>Writes a crash report and returns its path (null if even that failed).</summary>
    public static string? WriteCrash(Exception ex, string where)
    {
        try
        {
            Directory.CreateDirectory(CrashDir);
            var path = Path.Combine(CrashDir, $"crash-{DateTime.Now:yyyyMMdd-HHmmss}.txt");
            File.WriteAllText(path, Describe(ex, where));
            foreach (var old in Directory.GetFiles(CrashDir, "crash-*.txt").OrderDescending().Skip(KeepCrashLogs))
                File.Delete(old);
            return path;
        }
        catch (Exception) { return null; }
    }

    public static string Describe(Exception ex, string where)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"Altar {Config.Version} crash report");
        sb.AppendLine($"Time:    {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
        sb.AppendLine($"Where:   {where}");
        sb.AppendLine($"OS:      {Environment.OSVersion} ({(Environment.Is64BitOperatingSystem ? "64" : "32")}-bit)");
        sb.AppendLine($"Runtime: .NET {Environment.Version}");
        sb.AppendLine($"Exe:     {Environment.ProcessPath}");
        sb.AppendLine($"Args:    {string.Join(" ", Environment.GetCommandLineArgs().Skip(1))}");
        sb.AppendLine();
        sb.AppendLine(ex.ToString());
        return sb.ToString();
    }

    public static int CrashCount => Directory.Exists(CrashDir) ? Directory.GetFiles(CrashDir, "crash-*.txt").Length : 0;

    /// <summary>Isaac's log.txt files (one per save folder that has one).</summary>
    static IEnumerable<string> GameLogs() =>
        SaveGuard.SaveDirs().Select(d => Path.Combine(d, "log.txt")).Where(File.Exists);

    /// <summary>Lua errors from the last game session: Altar's crash guard lines and other mods' errors.</summary>
    public static List<string> GameErrors(int max = 40)
    {
        var found = new List<string>();
        foreach (var log in GameLogs())
        {
            try
            {
                using var fs = new FileStream(log, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                using var reader = new StreamReader(fs);
                string? line;
                while ((line = reader.ReadLine()) != null)
                {
                    if (line.Contains("[Altar Core] ERROR") || line.Contains("Error in \"") || line.Contains(".lua:") && line.Contains("error", StringComparison.OrdinalIgnoreCase))
                        found.Add(line.Trim());
                }
            }
            catch (Exception) { }
        }
        return found.Distinct().TakeLast(max).ToList();
    }
}
