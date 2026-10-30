using System.Windows;
using Altar.Core;
using Microsoft.Win32;

namespace Altar;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        var args = e.Args.ToList();
        var gameArg = args.IndexOf("--game") is var i and >= 0 && i + 1 < args.Count ? args[i + 1] : null;

        var gameDir = ResolveGame(gameArg);
        if (gameDir == null) { Shutdown(); return; }

        if (args.Contains("--sync")) // headless: just regenerate the in-game mod list
        {
            var store = new ModStore(gameDir);
            store.WriteModList(store.Scan());
            Shutdown();
            return;
        }
        if (Config.GetString("game_dir") != gameDir) Config.Set("game_dir", gameDir);

        var pageArg = args.IndexOf("--page") is var p and >= 0 && p + 1 < args.Count ? args[p + 1] : null;
        var win = new MainWindow(gameDir, pageArg);
        MainWindow = win;
        ShutdownMode = ShutdownMode.OnMainWindowClose;
        win.Show();
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
            if (GameLocator.IsGameDir(pick.FolderName)) return System.IO.Path.GetFullPath(pick.FolderName);
            Dialog.Info(null, "Wrong folder", "That folder has no isaac-ng.exe. Try again.");
        }
    }
}
