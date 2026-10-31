using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Threading;
using Altar.Core;
using Microsoft.Win32;

namespace Altar;

public partial class MainWindow : Window
{
    ModStore store;
    List<ModVM> mods = new();
    readonly ObservableCollection<ModVM> visible = new();
    ModVM? selected;
    string filter = "all";
    string page = "";

    bool clipLink;
    string? lastClip;
    bool clipPrimed;
    readonly DispatcherTimer clipTimer = new() { Interval = TimeSpan.FromMilliseconds(700) };
    readonly DispatcherTimer toastTimer = new() { Interval = TimeSpan.FromMilliseconds(2600) };

    bool safeMode;
    bool sawGame; // Isaac was seen running since the snapshot, so its exit means "session over"
    bool snapshotFailed;
    readonly DispatcherTimer guardTimer = new() { Interval = TimeSpan.FromSeconds(2) };

    /// <param name="startPage">--page: installed, profiles, conflicts, items or settings</param>
    public MainWindow(string gameDir, string? startPage = null)
    {
        InitializeComponent();
        store = new ModStore(gameDir);
        ModList.ItemsSource = visible;
        Logo.Source = Images.Embedded("logo.png");
        SubtitleText.Text = $"Mod Manager  ·  v{Config.Version}";
        VersionText.Text = $"Altar v{Config.Version}  ·  github.com/{Config.GitHubRepo}";
        AutoUpdateText.Text = $"Check GitHub for new Altar releases when the app starts (you have v{Config.Version}).";
        ItemGrid.ItemsSource = Images.EmbeddedItems()
            .Select(f => new ItemVM(TitleCase(f[5..^4]), Images.Embedded(f))).ToList();
        HotkeyList.ItemsSource = new[]
        {
            ("F2", "Open the Altar menu (or click the gem button)"),
            ("F3", "Live stat overlay"),
            ("F4", "Command console - try: boss monstro, combo all, tp devil, give overclock 3"),
            ("~", "The game's console works too: altar <command>"),
        };

        clipLink = Config.GetBool("clipboard_link", true);
        ClipSwitch.IsChecked = clipLink;
        AutoSwitch.IsChecked = Config.GetBool("auto_update", true);

        toastTimer.Tick += (_, _) => { toastTimer.Stop(); HideToast(); };
        clipTimer.Tick += (_, _) => PollClipboard();
        clipTimer.Start();

        safeMode = Config.GetBool("safe_mode", false);
        SafeSwitch.IsChecked = safeMode;
        guardTimer.Tick += (_, _) => GuardTick();
        guardTimer.Start();
        Closing += Window_Closing;

        SourceInitialized += (_, _) => ApplyWindowStyle();
        StateChanged += (_, _) =>
        {
            // a maximised chrome-less window overhangs the screen by the resize border
            Root.Margin = WindowState == WindowState.Maximized ? new Thickness(7) : new Thickness(0);
            MaxButton.Content = WindowState == WindowState.Maximized ? "" : "";
        };
        Loaded += async (_, _) =>
        {
            ResumeSafeMode();
            if (!Config.GetBool("auto_update", true)) return;
            await Task.Delay(1500);
            await CheckForUpdate(false);
        };

        Refresh();
        if (mods.Count > 0) Select(mods.FirstOrDefault(m => m.IsCore) ?? mods[0]);
        (startPage switch
        {
            "profiles" => NavProfiles, "conflicts" => NavConflicts, "items" => NavItems,
            "settings" => NavSettings, _ => NavInstalled,
        }).IsChecked = true;
    }

    // ------------------------------------------------------------ window chrome

    [DllImport("dwmapi.dll")]
    static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

    void ApplyWindowStyle()
    {
        var hwnd = new WindowInteropHelper(this).Handle;
        int dark = 1, round = 2, caption = 0x00291A1A; // COLORREF is 0x00BBGGRR (#1a1329)
        DwmSetWindowAttribute(hwnd, 20, ref dark, sizeof(int));     // DWMWA_USE_IMMERSIVE_DARK_MODE
        DwmSetWindowAttribute(hwnd, 33, ref round, sizeof(int));    // DWMWA_WINDOW_CORNER_PREFERENCE
        DwmSetWindowAttribute(hwnd, 35, ref caption, sizeof(int));  // DWMWA_BORDER_COLOR
    }

    void Min_Click(object s, RoutedEventArgs e) => WindowState = WindowState.Minimized;
    void Max_Click(object s, RoutedEventArgs e) =>
        WindowState = WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;
    void Close_Click(object s, RoutedEventArgs e) => Close();

    // ------------------------------------------------------------ navigation

    void Nav_Checked(object sender, RoutedEventArgs e)
    {
        var key = sender == NavProfiles ? "profiles" : sender == NavConflicts ? "conflicts"
                : sender == NavItems ? "items" : sender == NavSettings ? "settings" : "installed";
        ShowPage(key);
    }

    void ShowPage(string key)
    {
        if (page == key) return;
        page = key;
        var pages = new Dictionary<string, FrameworkElement>
        {
            ["installed"] = PageInstalled, ["profiles"] = PageProfiles, ["conflicts"] = PageConflicts,
            ["items"] = PageItems, ["settings"] = PageSettings,
        };
        foreach (var (k, el) in pages) el.Visibility = k == key ? Visibility.Visible : Visibility.Collapsed;
        bool details = key == "installed";
        DetailsColumn.Width = new GridLength(details ? 320 : 0);
        DetailsPane.Visibility = details ? Visibility.Visible : Visibility.Collapsed;
        if (key == "settings") RenderSettings();
        SlideIn(pages[key]);
    }

    static void SlideIn(FrameworkElement el)
    {
        var d = TimeSpan.FromMilliseconds(260);
        var ease = new CubicEase { EasingMode = EasingMode.EaseOut };
        var tt = new TranslateTransform(0, 14);
        el.RenderTransform = tt;
        el.BeginAnimation(OpacityProperty, new DoubleAnimation(0, 1, d));
        tt.BeginAnimation(TranslateTransform.YProperty, new DoubleAnimation(14, 0, d) { EasingFunction = ease });
    }

    // ------------------------------------------------------------ toast

    void Toast(string message, string brush = "B.Green")
    {
        ToastText.Text = message;
        ToastDot.Fill = (Brush)FindResource(brush);
        var d = TimeSpan.FromMilliseconds(220);
        ToastCard.BeginAnimation(OpacityProperty, new DoubleAnimation(1, d));
        ToastCard.RenderTransform.BeginAnimation(TranslateTransform.YProperty,
            new DoubleAnimation(18, 0, d) { EasingFunction = new BackEase { EasingMode = EasingMode.EaseOut, Amplitude = 0.4 } });
        toastTimer.Stop();
        toastTimer.Start();
    }

    void HideToast()
    {
        var d = TimeSpan.FromMilliseconds(300);
        ToastCard.BeginAnimation(OpacityProperty, new DoubleAnimation(0, d));
        ToastCard.RenderTransform.BeginAnimation(TranslateTransform.YProperty, new DoubleAnimation(10, d));
    }

    // ------------------------------------------------------------ mods

    void Refresh()
    {
        var list = store.Scan();
        var conflicted = ModStore.Conflicts(list).Values.SelectMany(x => x).ToHashSet();
        mods = list.Select(m => new ModVM(m, conflicted.Contains(m.Name), OnToggled)).ToList();
        selected = selected == null ? null : mods.FirstOrDefault(v => v.Mod.Folder == selected.Mod.Folder);
        if (selected != null) selected.IsSelected = true;
        WriteModList();
        GameLabel.Text = store.GameDir;
        GameDot.Fill = (Brush)FindResource(File.Exists(store.GameExe) ? "B.Green" : "B.Red");
        UpdateCount();
        RenderList();
        RenderDetails();
        RenderProfiles();
        RenderConflicts();
    }

    void WriteModList()
    {
        try { store.WriteModList(mods.Select(v => v.Mod)); }
        catch (Exception) { /* game may hold the file; next change retries */ }
    }

    void UpdateCount() => CountText.Text = $"{mods.Count(m => m.Enabled)} / {mods.Count} mods enabled";

    void RenderList()
    {
        var q = SearchBox.Text.Trim();
        visible.Clear();
        foreach (var m in mods)
        {
            if (q != "" && !(m.Name.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                             m.Mod.Folder.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                             m.Mod.Description.Contains(q, StringComparison.OrdinalIgnoreCase))) continue;
            if (filter == "on" && !m.Enabled || filter == "off" && m.Enabled) continue;
            visible.Add(m);
        }
        EmptyMods.Visibility = visible.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
    }

    void RenderDetails()
    {
        bool has = selected != null && Directory.Exists(selected.Mod.Path);
        DetailsBody.DataContext = has ? selected : null;
        DetailsBody.Visibility = has ? Visibility.Visible : Visibility.Collapsed;
        DetailsEmpty.Visibility = has ? Visibility.Collapsed : Visibility.Visible;
        if (has)
        {
            WorkshopRow.Visibility = selected!.WorkshopId != "" ? Visibility.Visible : Visibility.Collapsed;
            SlideIn(DetailsBody);
        }
    }

    void OnToggled(ModVM vm, bool on, Exception? error)
    {
        if (error != null)
        {
            Dialog.Info(this, "Couldn't change mod", $"Could not change {vm.Name}:\n{error.Message}");
            return;
        }
        WriteModList();
        UpdateCount();
        var conflicted = ModStore.Conflicts(mods.Select(v => v.Mod)).Values.SelectMany(x => x).ToHashSet();
        foreach (var m in mods) m.Conflicted = conflicted.Contains(m.Name);
        RenderConflicts();
        if (filter != "all") RenderList();
        Toast((on ? "Enabled " : "Disabled ") + vm.Name, on ? "B.Green" : "B.Red");
    }

    void Select(ModVM vm)
    {
        if (selected != null) selected.IsSelected = false;
        selected = vm;
        vm.IsSelected = true;
        RenderDetails();
    }

    void Card_MouseDown(object sender, MouseButtonEventArgs e)
    {
        if ((sender as FrameworkElement)?.Tag is not ModVM vm) return;
        if (e.ClickCount == 2) vm.Enabled = !vm.Enabled;
        else Select(vm);
    }

    void Search_Changed(object s, TextChangedEventArgs e) => RenderList();

    void Search_Focus(object s, RoutedEventArgs e) =>
        SearchBorder.BorderBrush = (Brush)FindResource(SearchBox.IsKeyboardFocused ? "B.Accent" : "B.Border");

    void Filter_Checked(object sender, RoutedEventArgs e)
    {
        filter = (string)((FrameworkElement)sender).Tag;
        if (IsLoaded) RenderList();
    }

    void SetAll(bool on)
    {
        foreach (var m in mods)
        {
            try { m.Mod.Enabled = on; } catch (Exception) { }
        }
        Refresh();
        Toast("All mods " + (on ? "enabled" : "disabled"), on ? "B.Green" : "B.Red");
    }

    void EnableAll_Click(object s, RoutedEventArgs e) => SetAll(true);
    void DisableAll_Click(object s, RoutedEventArgs e) => SetAll(false);
    void Refresh_Click(object s, RoutedEventArgs e) { Refresh(); Toast("Mod list refreshed", "B.Accent"); }
    void OpenMods_Click(object s, RoutedEventArgs e) => OpenFolder(store.ModsDir);

    static void OpenFolder(string path)
    {
        Directory.CreateDirectory(path);
        Process.Start(new ProcessStartInfo("explorer.exe", $"\"{path}\"") { UseShellExecute = true });
    }

    void InstallZip_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog { Title = "Install mod", Filter = "Mod archive (*.zip)|*.zip", Multiselect = true };
        if (dlg.ShowDialog(this) == true) InstallZips(dlg.FileNames);
    }

    void InstallZips(IEnumerable<string> paths)
    {
        var installed = new List<string>();
        foreach (var path in paths)
        {
            try
            {
                var folder = store.InstallZip(path, f =>
                    Dialog.Ask(this, "Replace mod?", $"'{f}' is already installed. Replace it?", "Replace"));
                if (folder != null) installed.Add(folder);
            }
            catch (Exception ex)
            {
                Dialog.Info(this, "Install failed", $"Could not install {Path.GetFileName(path)}:\n{ex.Message}");
            }
        }
        if (installed.Count == 0) return;
        Refresh();
        Toast("Installed " + string.Join(", ", installed));
    }

    void Window_DragEnter(object sender, DragEventArgs e)
    {
        if (DroppedZips(e).Any()) DropOverlay.Visibility = Visibility.Visible;
    }

    void Window_DragLeave(object sender, DragEventArgs e) => DropOverlay.Visibility = Visibility.Collapsed;

    void Window_Drop(object sender, DragEventArgs e)
    {
        DropOverlay.Visibility = Visibility.Collapsed;
        var zips = DroppedZips(e).ToList();
        if (zips.Count > 0) InstallZips(zips);
    }

    static IEnumerable<string> DroppedZips(DragEventArgs e) =>
        e.Data.GetData(DataFormats.FileDrop) is string[] files
            ? files.Where(f => f.EndsWith(".zip", StringComparison.OrdinalIgnoreCase))
            : Enumerable.Empty<string>();

    void DetailToggle_Click(object s, RoutedEventArgs e) { if (selected != null) selected.Enabled = !selected.Enabled; }
    void DetailFolder_Click(object s, RoutedEventArgs e) { if (selected != null) OpenFolder(selected.Mod.Path); }

    void DetailUninstall_Click(object s, RoutedEventArgs e)
    {
        if (selected is not { } m) return;
        if (!Dialog.Ask(this, "Uninstall mod", $"Remove '{m.Name}'?\n\nIt is moved to {Config.RemovedModsDir} so you can restore it later.",
                        "Uninstall", danger: true)) return;
        try { store.Uninstall(m.Mod); }
        catch (Exception ex)
        {
            Dialog.Info(this, "Uninstall failed", $"Could not remove {m.Name}:\n{ex.Message}\n\nClose Isaac and try again.");
            return;
        }
        selected = null;
        Refresh();
        Toast("Removed " + m.Name, "B.Red");
    }

    void Play_Click(object s, RoutedEventArgs e)
    {
        if (!File.Exists(store.GameExe))
        {
            Dialog.Info(this, "Game not found", store.GameExe);
            return;
        }
        WriteModList();
        if (!TakeSnapshot()) return;
        Process.Start(new ProcessStartInfo(store.GameExe) { WorkingDirectory = store.GameDir, UseShellExecute = true });
        Toast(SaveGuard.Active ? "Launching Isaac - safe mode: this session won't count" : "Launching Isaac...", "B.Gold");
    }

    // ------------------------------------------------------------ safe mode

    /// <summary>Snapshots the saves if safe mode wants one now. False if it failed and the user backed out.</summary>
    bool TakeSnapshot()
    {
        if (!safeMode || SaveGuard.Active || !mods.Any(m => m.Enabled)) return true;
        try
        {
            SaveGuard.Snapshot();
            sawGame = false;
        }
        catch (Exception ex)
        {
            return Dialog.Ask(this, "Safe mode", $"Couldn't copy your save files:\n{ex.Message}\n\nPlay anyway? This session will count.", "Play anyway");
        }
        finally { UpdateSafeStatus(); }
        return true;
    }

    /// <summary>Every 2 s: snapshot when Isaac starts outside the PLAY button, restore when it closes.</summary>
    void GuardTick()
    {
        bool running = SaveGuard.GameRunning;
        if (running && !SaveGuard.Active && safeMode && mods.Any(m => m.Enabled) && !snapshotFailed)
        {
            try
            {
                SaveGuard.Snapshot();
                Toast("Safe mode: this session won't count", "B.Green");
            }
            catch (Exception ex)
            {
                snapshotFailed = true; // warn once, not every tick
                Toast("Safe mode couldn't copy your saves: " + ex.Message, "B.Red");
            }
            UpdateSafeStatus();
        }
        if (!running) snapshotFailed = false;
        if (running && SaveGuard.Active) sawGame = true;
        else if (!running && SaveGuard.Active && sawGame) RestoreSaves();
    }

    void RestoreSaves()
    {
        sawGame = false;
        try
        {
            int n = SaveGuard.Restore();
            Toast($"Safe mode: modded session undone ({n} save files restored)", "B.Green");
        }
        catch (Exception ex)
        {
            Dialog.Info(this, "Safe mode", $"Couldn't put your save files back:\n{ex.Message}\n\nThey are still in {SaveGuard.FolderToOpen}. " +
                                           "Altar will try again next time Isaac closes.");
        }
        UpdateSafeStatus();
    }

    /// <summary>A snapshot left over from a session Altar didn't see end.</summary>
    void ResumeSafeMode()
    {
        if (!SaveGuard.Active) { UpdateSafeStatus(); return; }
        if (SaveGuard.GameRunning) { sawGame = true; UpdateSafeStatus(); return; }
        var when = SaveGuard.SnapshotTime?.ToString("ddd d MMM, HH:mm") ?? "earlier";
        if (Dialog.Ask(this, "Undo modded session?",
                $"Altar was closed while Isaac was running with mods ({when}), so that session wasn't undone.\n\n" +
                "Put your save files back to how they were before it?", "Undo it", "Keep progress"))
            RestoreSaves();
        else
        {
            SaveGuard.Clear();
            Toast("Kept the progress from that session", "B.Gold");
        }
        UpdateSafeStatus();
    }

    void UpdateSafeStatus()
    {
        SafePill.Visibility = safeMode || SaveGuard.Active ? Visibility.Visible : Visibility.Collapsed;
        SafePillText.Text = SaveGuard.Active ? "SAFE MODE · PROTECTING" : "SAFE MODE";
        var dirs = SaveGuard.SaveDirs();
        SafeStatus.Text = SaveGuard.Active
            ? $"Protecting a session since {SaveGuard.SnapshotTime:HH:mm} - your saves go back when Isaac closes."
            : dirs.Count > 0 ? "Save files: " + string.Join("; ", dirs) : "No Isaac save files found yet.";
    }

    void SafeSwitch_Click(object s, RoutedEventArgs e)
    {
        safeMode = SafeSwitch.IsChecked == true;
        Config.Set("safe_mode", safeMode);
        if (safeMode && SaveGuard.GameRunning && !SaveGuard.Active)
            Toast("Safe mode starts with your next Isaac session", "B.Gold");
        else
            Toast(safeMode ? "Safe mode on: modded runs won't count" : "Safe mode off", safeMode ? "B.Green" : "B.Red");
        UpdateSafeStatus();
    }

    void OpenSafe_Click(object s, RoutedEventArgs e) => OpenFolder(SaveGuard.FolderToOpen);

    // ------------------------------------------------------------ crash reports

    void UpdateCrashStatus()
    {
        int crashes = Diagnostics.CrashCount, errors = Diagnostics.GameErrors().Count;
        CrashStatus.Text = $"{crashes} app crash report{(crashes == 1 ? "" : "s")}  ·  " +
                           $"{errors} error line{(errors == 1 ? "" : "s")} in Isaac's last log";
    }

    void GameErrors_Click(object s, RoutedEventArgs e)
    {
        var errors = Diagnostics.GameErrors();
        if (errors.Count == 0)
        {
            Toast("No mod errors in Isaac's last log", "B.Green");
            return;
        }
        Dialog.Text(this, "Game errors", "Lua errors from the last Isaac session (newest last). Lines from Altar's crash guard " +
                                         "start with [Altar Core] ERROR; the game kept running through them.", string.Join("\n", errors));
    }

    void OpenCrashes_Click(object s, RoutedEventArgs e) => OpenFolder(Diagnostics.CrashDir);

    void Window_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        if (!SaveGuard.Active || !SaveGuard.GameRunning) return;
        if (!Dialog.Ask(this, "Isaac is still running",
                "Safe mode can only undo this session if Altar stays open until Isaac closes. " +
                "(If you close it anyway, Altar will offer to undo it next time it starts.)", "Close anyway", "Keep open"))
            e.Cancel = true;
    }

    // ------------------------------------------------------------ profiles

    void RenderProfiles()
    {
        var list = Config.Profiles().OrderBy(p => p.Key, StringComparer.OrdinalIgnoreCase)
                         .Select(p => new ProfileVM(p.Key, p.Value.Count)).ToList();
        ProfileList.ItemsSource = list;
        EmptyProfiles.Visibility = list.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
    }

    void SaveProfile_Click(object s, RoutedEventArgs e) => SaveProfile();

    void ProfileName_KeyDown(object s, KeyEventArgs e) { if (e.Key == Key.Enter) SaveProfile(); }

    void SaveProfile()
    {
        var name = ProfileName.Text.Trim();
        if (name == "")
        {
            Toast("Type a profile name first", "B.Gold");
            ProfileName.Focus();
            return;
        }
        var profiles = Config.Profiles();
        profiles[name] = mods.Where(m => m.Enabled).Select(m => m.Mod.Folder).ToList();
        Config.SaveProfiles(profiles);
        ProfileName.Text = "";
        RenderProfiles();
        Toast("Saved profile " + name);
    }

    void ApplyProfile_Click(object sender, RoutedEventArgs e)
    {
        var name = (string)((Button)sender).CommandParameter;
        if (!Config.Profiles().TryGetValue(name, out var enabled)) return;
        var on = enabled.ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var m in mods)
        {
            try { m.Mod.Enabled = on.Contains(m.Mod.Folder); } catch (Exception) { }
        }
        Refresh();
        Toast($"Profile '{name}' applied - restart Isaac if it's running", "B.Gold");
    }

    void DeleteProfile_Click(object sender, RoutedEventArgs e)
    {
        var name = (string)((Button)sender).CommandParameter;
        if (!Dialog.Ask(this, "Delete profile", $"Delete the profile '{name}'?", "Delete", danger: true)) return;
        var profiles = Config.Profiles();
        profiles.Remove(name);
        Config.SaveProfiles(profiles);
        RenderProfiles();
        Toast("Deleted profile " + name, "B.Red");
    }

    // ------------------------------------------------------------ conflicts

    void RenderConflicts()
    {
        var list = ModStore.Conflicts(mods.Select(v => v.Mod)).OrderBy(kv => kv.Key).Take(300)
                           .Select(kv => new ConflictVM(kv.Key, string.Join("   •   ", kv.Value))).ToList();
        ConflictList.ItemsSource = list;
        NoConflicts.Visibility = list.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        NavConflicts.Content = list.Count > 0 ? $"Conflicts ({list.Count})" : "Conflicts";
    }

    // ------------------------------------------------------------ settings

    void RenderSettings()
    {
        GamePathText.Text = store.GameDir;
        UpdateCrashStatus();
        var others = GameLocator.FindAll()
            .Where(d => !string.Equals(d, store.GameDir, StringComparison.OrdinalIgnoreCase)).ToList();
        OtherInstalls.ItemsSource = others;
        OtherInstallsTitle.Visibility = others.Count > 0 ? Visibility.Visible : Visibility.Collapsed;
    }

    void ChangeGame_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFolderDialog { Title = "Select your Isaac folder (contains isaac-ng.exe)" };
        if (dlg.ShowDialog(this) != true) return;
        if (GameLocator.IsGameDir(dlg.FolderName)) SetGame(dlg.FolderName);
        else Dialog.Info(this, "Wrong folder", "That folder has no isaac-ng.exe.");
    }

    void UseInstall_Click(object sender, RoutedEventArgs e) => SetGame((string)((Button)sender).CommandParameter);

    void SetGame(string path)
    {
        path = Path.GetFullPath(path);
        Config.Set("game_dir", path);
        store = new ModStore(path);
        selected = null;
        Refresh();
        RenderSettings();
        Toast("Game folder updated");
    }

    void OpenGame_Click(object s, RoutedEventArgs e) => OpenFolder(store.GameDir);
    void OpenData_Click(object s, RoutedEventArgs e) => OpenFolder(Config.Dir);

    void ClipSwitch_Click(object s, RoutedEventArgs e)
    {
        clipLink = ClipSwitch.IsChecked == true;
        Config.Set("clipboard_link", clipLink);
    }

    void AutoSwitch_Click(object s, RoutedEventArgs e) => Config.Set("auto_update", AutoSwitch.IsChecked == true);

    async void CheckNow_Click(object s, RoutedEventArgs e)
    {
        CheckNowButton.IsEnabled = false;
        try { await CheckForUpdate(true); }
        finally { CheckNowButton.IsEnabled = true; }
    }

    // ------------------------------------------------------------ clipboard link

    /// <summary>Forward newly copied text to the game while the clipboard link is on.</summary>
    void PollClipboard()
    {
        if (!clipLink) return;
        string? text;
        try { text = Clipboard.ContainsText() ? Clipboard.GetText() : null; }
        catch (Exception) { return; } // clipboard busy in another app
        if (text == null || text == lastClip || text.Length > 2000) return;
        if (clipPrimed)
        {
            try
            {
                ClipboardBridge.Push(store.GameDir, text);
                Toast("Copied to game - press Ctrl+V in the Altar console", "B.Accent");
            }
            catch (Exception) { }
        }
        lastClip = text;
        clipPrimed = true;
    }

    // ------------------------------------------------------------ auto-update

    async Task CheckForUpdate(bool manual)
    {
        ReleaseInfo? rel;
        try { rel = await Updater.CheckAsync(); }
        catch (Exception ex)
        {
            if (manual) Toast("Couldn't reach GitHub: " + ex.Message, "B.Red");
            return;
        }
        if (rel == null)
        {
            if (manual) Toast($"You're up to date (v{Config.Version})");
            return;
        }
        if (!Dialog.Ask(this, "Update available",
                $"Altar {rel.Tag} is out (you have v{Config.Version}).\n\nDownload it ({rel.Size / 1e6:0} MB) and install now?",
                "Update", "Later"))
        {
            Toast($"Update {rel.Tag} available - Settings > Check now", "B.Gold");
            return;
        }
        UpdateBanner.Visibility = Visibility.Visible;
        UpdateText.Text = $"Downloading Altar {rel.Tag}...";
        string path;
        try
        {
            path = await Updater.DownloadAsync(rel, new Progress<double>(p =>
            {
                UpdateProgress.Value = p;
                UpdateText.Text = $"Downloading Altar {rel.Tag}...  {p * 100:0}%";
            }));
        }
        catch (Exception ex)
        {
            UpdateBanner.Visibility = Visibility.Collapsed;
            Dialog.Info(this, "Update failed", "Update download failed:\n" + ex.Message);
            return;
        }
        UpdateText.Text = "Starting installer...";
        Updater.RunInstaller(path);
        Application.Current.Shutdown();
    }

    static string TitleCase(string snake) =>
        string.Join(" ", snake.Split('_').Select(w => w.Length > 0 ? char.ToUpper(w[0]) + w[1..] : w));
}
