using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.Win32;

namespace Altar.Core;

/// <summary>
/// Installs Altar from the payload.zip embedded in this exe (mod/ files, built by
/// tools/build.py). The app itself is this exe: setup copies itself to
/// %LOCALAPPDATA%\Programs\Altar\Altar.exe, which also serves as the uninstaller.
/// </summary>
public static class Installer
{
    public static string AppDir { get; set; } = Path.Combine( // settable for tests
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Altar");
    public static string AppExe => Path.Combine(AppDir, "Altar.exe");
    const string UninstallKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\AltarModManager";
    // voice files only ever installed locally (tools/build.py --public leaves them out)
    static readonly string[] VoicePaths = { Path.Combine("sfx", "altar"), Path.Combine("resources", "sfx", "altar") };

    static Stream? Payload() => typeof(Installer).Assembly.GetManifestResourceStream("payload.zip");
    public static bool HasPayload => typeof(Installer).Assembly.GetManifestResourceInfo("payload.zip") != null;

    public static bool IsInstalledCopy =>
        string.Equals(Environment.ProcessPath, AppExe, StringComparison.OrdinalIgnoreCase);

    /// <summary>Copies everything into place; returns the installed Altar.exe.</summary>
    public static string Install(string gameDir, bool desktop, bool startMenu, bool registry, IProgress<(double, string)> progress)
    {
        using var payload = Payload() ?? throw new InvalidOperationException(
            "This copy of Altar has no installer payload. Download AltarSetup.exe from the GitHub releases page.");
        using var zip = new ZipArchive(payload, ZipArchiveMode.Read);
        var modDir = Path.Combine(gameDir, "mods", Config.ModFolder);
        var entries = zip.Entries.Where(e => e.FullName.StartsWith("mod/") && !e.FullName.EndsWith("/")).ToList();
        long total = Math.Max(1, entries.Sum(e => e.Length)), done = 0;

        // public builds ship without the voice lines: keep any local ones across updates
        string? kept = null;
        if (!entries.Any(e => e.FullName.StartsWith("mod/resources/sfx/altar/")) && Directory.Exists(modDir))
        {
            kept = Path.Combine(Path.GetTempPath(), "altar_keep_" + Guid.NewGuid().ToString("N")[..8]);
            foreach (var rel in VoicePaths)
            {
                var src = Path.Combine(modDir, rel);
                if (!Directory.Exists(src)) continue;
                Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(kept, rel))!);
                Directory.Move(src, Path.Combine(kept, rel));
            }
        }

        progress.Report((0.02, "Removing old Altar Core..."));
        if (Directory.Exists(modDir)) Retry(() => Directory.Delete(modDir, true));
        var modFull = Path.GetFullPath(modDir) + Path.DirectorySeparatorChar;
        foreach (var e in entries)
        {
            var target = Path.GetFullPath(Path.Combine(modDir, e.FullName[4..]));
            if (!target.StartsWith(modFull, StringComparison.OrdinalIgnoreCase)) continue;
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            e.ExtractToFile(target, true);
            done += e.Length;
            progress.Report((0.05 + 0.75 * done / total, e.Name));
        }
        if (kept != null)
        {
            foreach (var rel in VoicePaths)
            {
                string src = Path.Combine(kept, rel), dst = Path.Combine(modDir, rel);
                if (Directory.Exists(src) && !Directory.Exists(dst))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
                    Directory.Move(src, dst);
                }
            }
            try { Directory.Delete(kept, true); } catch (Exception) { }
        }
        WriteSoundsXml(modDir); // register whatever voice lines + SFX are now present

        progress.Report((0.84, "Installing Altar.exe..."));
        Directory.CreateDirectory(AppDir);
        if (!IsInstalledCopy)
            Retry(() => File.Copy(Environment.ProcessPath!, AppExe, true), 40); // the old app may still be closing
        // leftovers from the Python-era installer
        foreach (var old in new[] { "Uninstall Altar.exe" })
        {
            try { File.Delete(Path.Combine(AppDir, old)); } catch (Exception) { }
        }

        progress.Report((0.9, "Saving settings..."));
        Config.Set("game_dir", Path.GetFullPath(gameDir));
        if (desktop || startMenu)
        {
            progress.Report((0.94, "Creating shortcuts..."));
            if (desktop) MakeShortcut(Environment.SpecialFolder.DesktopDirectory);
            if (startMenu) MakeShortcut(Environment.SpecialFolder.Programs);
        }
        if (registry)
        {
            progress.Report((0.98, "Registering in Apps & features..."));
            Register();
        }
        progress.Report((1.0, "Done"));
        return AppExe;
    }

    public static void Uninstall(bool removeMod, IProgress<(double, string)> progress)
    {
        var gameDir = Config.GetString("game_dir");
        progress.Report((0.15, "Putting back any saves safe mode is holding..."));
        if (SaveGuard.Active && !SaveGuard.GameRunning)
        {
            try { SaveGuard.Restore(); } catch (Exception) { }
        }
        progress.Report((0.3, "Removing shortcuts..."));
        foreach (var f in new[] { Environment.SpecialFolder.DesktopDirectory, Environment.SpecialFolder.Programs })
        {
            try { File.Delete(Path.Combine(Environment.GetFolderPath(f), "Altar.lnk")); } catch (Exception) { }
        }
        progress.Report((0.45, "Removing Apps & features entry..."));
        try { Registry.CurrentUser.DeleteSubKeyTree(UninstallKey, false); } catch (Exception) { }
        if (removeMod && gameDir != null)
        {
            progress.Report((0.6, "Removing Altar Core mod..."));
            try { Directory.Delete(Path.Combine(gameDir, "mods", Config.ModFolder), true); } catch (Exception) { }
        }
        progress.Report((0.8, "Removing app files..."));
        if (Directory.Exists(AppDir))
        {
            foreach (var p in Directory.EnumerateFileSystemEntries(AppDir))
            {
                if (string.Equals(p, Environment.ProcessPath, StringComparison.OrdinalIgnoreCase)) continue;
                try
                {
                    if (Directory.Exists(p)) Directory.Delete(p, true);
                    else File.Delete(p);
                }
                catch (Exception) { }
            }
        }
        try { Directory.Delete(Config.Dir, true); } catch (Exception) { }
        progress.Report((1.0, "Done"));
    }

    /// <summary>The running uninstaller can't delete itself, so a hidden cmd does it after exit.</summary>
    public static void ScheduleSelfDelete()
    {
        if (!IsInstalledCopy) return;
        Process.Start(new ProcessStartInfo("cmd.exe", $"/c ping 127.0.0.1 -n 3 > nul & rmdir /s /q \"{AppDir}\"")
        {
            CreateNoWindow = true,
            UseShellExecute = false,
        });
    }

    static void MakeShortcut(Environment.SpecialFolder folder)
    {
        try
        {
            var path = Path.Combine(Environment.GetFolderPath(folder), "Altar.lnk");
            var shellType = Type.GetTypeFromProgID("WScript.Shell")!;
            dynamic shell = Activator.CreateInstance(shellType)!;
            var lnk = shell.CreateShortcut(path);
            lnk.TargetPath = AppExe;
            lnk.IconLocation = AppExe;
            lnk.WorkingDirectory = AppDir;
            lnk.Description = "Altar Mod Manager";
            lnk.Save();
        }
        catch (Exception) { /* a missing shortcut is not worth failing the install */ }
    }

    static void Register()
    {
        using var k = Registry.CurrentUser.CreateSubKey(UninstallKey);
        k.SetValue("DisplayName", "Altar Mod Manager");
        k.SetValue("DisplayVersion", Config.Version);
        k.SetValue("Publisher", "Altar");
        k.SetValue("DisplayIcon", AppExe);
        k.SetValue("InstallLocation", AppDir);
        k.SetValue("UninstallString", $"\"{AppExe}\" --uninstall");
        k.SetValue("EstimatedSize", (int)(new FileInfo(AppExe).Length / 1024), RegistryValueKind.DWord);
        k.SetValue("NoModify", 1, RegistryValueKind.DWord);
        k.SetValue("NoRepair", 1, RegistryValueKind.DWord);
    }

    static void Retry(Action action, int tries = 12)
    {
        for (int i = 1; ; i++)
        {
            try { action(); return; }
            catch (IOException) when (i < tries) { Thread.Sleep(250); }
            catch (UnauthorizedAccessException) when (i < tries) { Thread.Sleep(250); }
        }
    }

    /// <summary>content/sounds.xml from the sound files actually present (same as src/altar_sounds.py).</summary>
    public static void WriteSoundsXml(string modDir)
    {
        var sb = new StringBuilder("<sounds root=\"sfx/\">\n");
        var voice = Path.Combine(modDir, "resources", "sfx", "altar");
        if (Directory.Exists(voice))
        {
            var nums = Directory.GetFiles(voice)
                .Select(f => Regex.Match(Path.GetFileName(f), @"^oblivion_line(\d+)\.wav$"))
                .Where(m => m.Success).Select(m => int.Parse(m.Groups[1].Value)).Order();
            foreach (var n in nums)
                sb.Append($"\t<sound name=\"Altar Oblivion Line {n}\"><sample path=\"altar/oblivion_line{n}.wav\"/></sound>\n");
        }
        var fxDir = Path.Combine(modDir, "resources", "sfx", "altar_fx");
        if (Directory.Exists(fxDir))
        {
            foreach (var f in Directory.GetFiles(fxDir, "*.wav").Select(Path.GetFileName).Order(StringComparer.Ordinal))
                sb.Append($"\t<sound name=\"Altar FX {f![..^4]}\"><sample path=\"altar_fx/{f}\"/></sound>\n");
        }
        sb.Append("</sounds>\n");
        Directory.CreateDirectory(Path.Combine(modDir, "content"));
        File.WriteAllText(Path.Combine(modDir, "content", "sounds.xml"), sb.ToString());
    }
}
