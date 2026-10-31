using System.IO;
using System.Windows;
using System.Windows.Threading;
using Altar.Core;
using Microsoft.Win32;

namespace Altar;

/// <summary>
/// One exe, two jobs. Named AltarSetup.exe (or run with --install / --update /
/// --uninstall) it is the installer; installed as Altar.exe it is the Mod Manager.
///
///   --game DIR       game folder           --page NAME     open the manager on a page
///   --sync           rewrite the in-game mod list and exit
///   --silent         install without UI (with --game DIR, --no-shortcuts, --no-registry)
///   --crash-test     throw once the window is up, to check the crash handler
/// </summary>
public partial class App : Application
{
    bool crashing;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        HookCrashHandlers();
        var args = e.Args.ToList();
        string? Arg(string name) => args.IndexOf(name) is var i and >= 0 && i + 1 < args.Count ? args[i + 1] : null;

        var mode = SetupMode(args);
        if (mode != null)
        {
            RunSetup(mode, args, Arg("--game"), Arg("--page"));
            return;
        }

        var gameDir = ResolveGame(Arg("--game"));
        if (gameDir == null) { Shutdown(); return; }

        if (args.Contains("--sync")) // headless: just regenerate the in-game mod list
        {
            var store = new ModStore(gameDir);
            store.WriteModList(store.Scan());
            Shutdown();
            return;
        }
        if (Config.GetString("game_dir") != gameDir) Config.Set("game_dir", gameDir);

        var win = new MainWindow(gameDir, Arg("--page"));
        MainWindow = win;
        ShutdownMode = ShutdownMode.OnMainWindowClose;
        win.Show();
        if (args.Contains("--crash-test"))
            Dispatcher.BeginInvoke(DispatcherPriority.ApplicationIdle,
                new Action(() => throw new InvalidOperationException("Crash handler test (--crash-test)")));
    }

    static string? SetupMode(List<string> args)
    {
        if (args.Contains("--uninstall")) return "uninstall";
        if (args.Contains("--update")) return "update";
        if (args.Contains("--install")) return "install";
        var name = Path.GetFileNameWithoutExtension(Environment.ProcessPath ?? "");
        return name.Contains("setup", StringComparison.OrdinalIgnoreCase) && Installer.HasPayload ? "install" : null;
    }

    void RunSetup(string mode, List<string> args, string? gameArg, string? page)
    {
        if (args.Contains("--silent") && mode != "uninstall")
        {
            var game = gameArg ?? GameLocator.FindAll().FirstOrDefault();
            if (!GameLocator.IsGameDir(game)) { Shutdown(2); return; }
            try
            {
                bool shortcuts = !args.Contains("--no-shortcuts");
                Installer.Install(game!, shortcuts, shortcuts, !args.Contains("--no-registry"), new Progress<(double, string)>());
                Shutdown(0);
            }
            catch (Exception ex)
            {
                Diagnostics.WriteCrash(ex, "silent install");
                Shutdown(1);
            }
            return;
        }
        var win = new SetupWindow(mode, gameArg, page);
        MainWindow = win;
        ShutdownMode = ShutdownMode.OnMainWindowClose;
        win.Show();
    }

    // ------------------------------------------------------------ crash handler

    void HookCrashHandlers()
    {
        DispatcherUnhandledException += (_, ev) =>
        {
            ev.Handled = true;
            if (crashing) { Shutdown(1); return; } // the crash window itself failed
            crashing = true;
            var canContinue = MainWindow is { IsVisible: true };
            var choice = CrashWindow.Show(ev.Exception, "UI", canContinue);
            crashing = false;
            if (choice != CrashChoice.Continue) Shutdown(1);
        };
        // these can't show a window safely (the process may be going down), so they only log
        AppDomain.CurrentDomain.UnhandledException += (_, ev) =>
        {
            if (ev.ExceptionObject is Exception ex) Diagnostics.WriteCrash(ex, "background thread");
        };
        TaskScheduler.UnobservedTaskException += (_, ev) =>
        {
            Diagnostics.WriteCrash(ev.Exception, "background task");
            ev.SetObserved();
        };
    }

    /// <summary>Game folder from --game, config, auto-detect, or a folder picker.</summary>
    static string? ResolveGame(string? arg)
    {
        var found = GameLocator.FindAll(arg);
        if (found.Count > 0) return found[0];
        Dialog.Info(null, "Find Isaac", "Altar couldn't find The Binding of Isaac automatically.\n\n" +
                                        "Pick the folder that contains isaac-ng.exe.");
        while (true)
        {
            var pick = new OpenFolderDialog { Title = "Select your Isaac folder (contains isaac-ng.exe)" };
            if (pick.ShowDialog() != true) return null;
            if (GameLocator.IsGameDir(pick.FolderName)) return Path.GetFullPath(pick.FolderName);
            Dialog.Info(null, "Wrong folder", "That folder has no isaac-ng.exe. Try again.");
        }
    }
}
