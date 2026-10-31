using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using Ellipse = System.Windows.Shapes.Ellipse;
using System.Windows.Threading;
using Altar.Core;
using Microsoft.Win32;

namespace Altar;

/// <summary>
/// Geode-style setup wizard. install: welcome > game folder > options > installing > done;
/// update (from the Mod Manager's auto-update): installing > done; uninstall: confirm > working > done.
/// </summary>
public partial class SetupWindow : Window
{
    readonly string mode;
    readonly List<string> pages;
    int index;
    string? error;
    bool working;
    double target, shown;
    string? installedExe;
    readonly DispatcherTimer barTimer = new() { Interval = TimeSpan.FromMilliseconds(16) };

    public SetupWindow(string mode, string? gameArg, string? startPage = null)
    {
        InitializeComponent();
        this.mode = mode;
        Logo.Source = Images.Embedded("logo.png");
        Subtitle.Text = mode switch
        {
            "update" => $"Updating to v{Config.Version}",
            "uninstall" => "Uninstall",
            _ => $"Setup  ·  v{Config.Version}",
        };
        FooterText.Text = $"Altar v{Config.Version}";
        DrawStars();

        var game = gameArg ?? Config.GetString("game_dir");
        if (!GameLocator.IsGameDir(game)) game = GameLocator.FindAll().FirstOrDefault();
        GamePath.Text = game ?? "";
        BuildFoundList();

        pages = mode switch
        {
            // an update with no known game folder falls back to asking for it
            "update" when GameLocator.IsGameDir(game) => new() { "installing", "done" },
            "update" => new() { "location", "installing", "done" },
            "uninstall" => new() { "confirm", "installing", "done" },
            _ => new() { "welcome", "location", "options", "installing", "done" },
        };
        if (startPage != null && pages.Contains(startPage)) index = pages.IndexOf(startPage);
        barTimer.Tick += (_, _) => TickBar();
        SourceInitialized += (_, _) => ApplyWindowStyle();
        Loaded += (_, _) => ShowPage();
    }

    [DllImport("dwmapi.dll")]
    static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

    void ApplyWindowStyle()
    {
        var hwnd = new WindowInteropHelper(this).Handle;
        int dark = 1, round = 2;
        DwmSetWindowAttribute(hwnd, 20, ref dark, sizeof(int));
        DwmSetWindowAttribute(hwnd, 33, ref round, sizeof(int));
    }

    // a still night sky behind the logo, with a few slow twinkles
    void DrawStars()
    {
        var rng = new Random(7);
        for (int i = 0; i < 70; i++)
        {
            double size = rng.NextDouble() < 0.15 ? 2.5 : 1.3;
            var star = new Ellipse
            {
                Width = size, Height = size, Fill = Brushes.White,
                Opacity = 0.2 + rng.NextDouble() * 0.6,
            };
            Canvas.SetLeft(star, rng.NextDouble() * 780);
            Canvas.SetTop(star, rng.NextDouble() * 130);
            Stars.Children.Add(star);
            if (i % 5 == 0)
            {
                star.BeginAnimation(OpacityProperty, new DoubleAnimation(0.1, 1, TimeSpan.FromSeconds(1.2 + rng.NextDouble() * 2))
                {
                    AutoReverse = true, RepeatBehavior = RepeatBehavior.Forever, BeginTime = TimeSpan.FromSeconds(rng.NextDouble() * 2),
                });
            }
        }
    }

    void BuildFoundList()
    {
        FoundList.Children.Clear();
        var found = GameLocator.FindAll().Take(4).ToList();
        if (found.Count == 0)
            FoundList.Children.Add(new TextBlock { Text = "No install found automatically.", Foreground = (Brush)FindResource("B.Dim"), Margin = new Thickness(0, 0, 0, 6) });
        foreach (var path in found)
        {
            var rb = new RadioButton
            {
                Style = (Style)FindResource("RadioCard"), GroupName = "game", Content = path, Margin = new Thickness(0, 0, 10, 6),
                IsChecked = string.Equals(path, GamePath.Text, StringComparison.OrdinalIgnoreCase),
            };
            rb.Checked += (_, _) => GamePath.Text = path;
            FoundList.Children.Add(rb);
        }
    }

    // ------------------------------------------------------------ navigation

    FrameworkElement PageElement(string name) => name switch
    {
        "welcome" => PageWelcome, "location" => PageLocation, "options" => PageOptions,
        "confirm" => PageConfirm, "installing" => PageInstalling, _ => PageDone,
    };

    void ShowPage()
    {
        var name = pages[index];
        foreach (var p in new FrameworkElement[] { PageWelcome, PageLocation, PageOptions, PageConfirm, PageInstalling, PageDone })
            p.Visibility = Visibility.Collapsed;
        var el = PageElement(name);
        el.Visibility = Visibility.Visible;
        SlideIn(el);
        RenderSteps();

        BackButton.Visibility = index > 0 && name is not ("installing" or "done") ? Visibility.Visible : Visibility.Collapsed;
        NextButton.IsEnabled = true;
        CloseButton.IsEnabled = name != "installing";
        NextButton.Content = name switch
        {
            "options" => "Install",
            "confirm" => "Uninstall",
            "location" when mode == "update" => "Update",
            "done" => error == null && mode != "uninstall" && OptLaunch.IsChecked == true ? "Open Altar" : "Finish",
            _ => "Next",
        };
        NextButton.Style = (Style)FindResource(name == "confirm" ? "Btn.Danger" : "Btn.Accent");

        if (name == "location") ValidateLocation();
        if (name == "options")
            PathsInfo.Text = $"Mod  →  {Path.Combine(GamePath.Text, "mods", Config.ModFolder)}\nApp  →  {Installer.AppDir}";
        if (name == "installing") StartWork();
        if (name == "done") ShowDone();
    }

    void RenderSteps()
    {
        Steps.Children.Clear();
        var labels = pages.Select(p => p switch
        {
            "welcome" => "Welcome", "location" => "Game", "options" => "Options", "confirm" => "Confirm",
            "installing" => mode == "uninstall" ? "Remove" : "Install", _ => "Done",
        }).ToList();
        for (int i = 0; i < labels.Count; i++)
        {
            bool current = i == index, past = i < index;
            var pill = new Border
            {
                CornerRadius = new CornerRadius(10), Padding = new Thickness(10, 3, 10, 3), Margin = new Thickness(6, 0, 0, 0),
                Background = current ? (Brush)FindResource("B.AccentGrad") : new SolidColorBrush(Color.FromArgb(past ? (byte)0x44 : (byte)0x22, 255, 255, 255)),
                Child = new TextBlock
                {
                    Text = (past ? "✓ " : "") + labels[i], FontSize = 11.5, FontWeight = current ? FontWeights.Bold : FontWeights.Normal,
                    Foreground = current ? Brushes.White : new SolidColorBrush(Color.FromArgb(past ? (byte)0xdd : (byte)0x99, 255, 255, 255)),
                },
            };
            Steps.Children.Add(pill);
        }
    }

    static void SlideIn(FrameworkElement el)
    {
        var d = TimeSpan.FromMilliseconds(280);
        var tt = new TranslateTransform(24, 0);
        el.RenderTransform = tt;
        el.BeginAnimation(OpacityProperty, new DoubleAnimation(0, 1, d));
        tt.BeginAnimation(TranslateTransform.XProperty, new DoubleAnimation(24, 0, d) { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } });
    }

    void Next_Click(object s, RoutedEventArgs e)
    {
        var name = pages[index];
        if (name == "location" && !ValidateLocation()) return;
        if (name == "done")
        {
            if (error == null && mode != "uninstall" && OptLaunch.IsChecked == true && installedExe != null)
            {
                try { Process.Start(new ProcessStartInfo(installedExe) { UseShellExecute = true, WorkingDirectory = Installer.AppDir }); }
                catch (Exception) { }
            }
            if (mode == "uninstall" && error == null) Installer.ScheduleSelfDelete();
            Close();
            return;
        }
        index++;
        ShowPage();
    }

    void Back_Click(object s, RoutedEventArgs e)
    {
        if (index == 0) return;
        index--;
        ShowPage();
    }

    void Min_Click(object s, RoutedEventArgs e) => WindowState = WindowState.Minimized;
    void Close_Click(object s, RoutedEventArgs e) { if (!working) Close(); }

    // ------------------------------------------------------------ game folder

    void GamePath_Changed(object s, TextChangedEventArgs e)
    {
        if (IsLoaded) ValidateLocation();
        foreach (var rb in FoundList.Children.OfType<RadioButton>())
            rb.IsChecked = string.Equals((string)rb.Content, GamePath.Text, StringComparison.OrdinalIgnoreCase);
    }

    bool ValidateLocation()
    {
        bool ok = GameLocator.IsGameDir(GamePath.Text);
        LocIcon.Text = ok ? "" : "";
        LocIcon.Foreground = (Brush)FindResource(ok ? "B.Green" : "B.Sub");
        LocStatus.Text = ok ? "isaac-ng.exe found" : "Choose the folder that contains isaac-ng.exe";
        LocStatus.Foreground = (Brush)FindResource(ok ? "B.Green" : "B.Sub");
        return ok;
    }

    void Browse_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFolderDialog { Title = "Select your Isaac folder (contains isaac-ng.exe)" };
        if (dlg.ShowDialog(this) == true) GamePath.Text = Path.GetFullPath(dlg.FolderName);
    }

    // ------------------------------------------------------------ work

    async void StartWork()
    {
        working = true;
        error = null;
        target = shown = 0;
        WorkTitle.Text = mode == "uninstall" ? "Uninstalling..." : mode == "update" ? "Updating..." : "Installing...";
        WorkSub.Text = mode == "uninstall" ? "Packing the stars away." : "Putting the stars back where they belong.";
        NextButton.IsEnabled = false;
        barTimer.Start();
        var progress = new Progress<(double f, string msg)>(p =>
        {
            target = Math.Max(target, p.f);
            WorkStatus.Text = p.msg;
        });
        string game = GamePath.Text;
        bool desktop = OptDesktop.IsChecked == true, start = OptStart.IsChecked == true, removeMod = OptRemoveMod.IsChecked == true;
        bool isUpdate = mode == "update";
        try
        {
            await Task.Run(() =>
            {
                if (mode == "uninstall") Installer.Uninstall(removeMod, progress);
                // an update keeps whatever shortcuts the user already has
                else installedExe = Installer.Install(game, !isUpdate && desktop, !isUpdate && start, true, progress);
            });
        }
        catch (Exception ex)
        {
            error = ex.Message;
            Diagnostics.WriteCrash(ex, mode);
        }
        target = 1;
        // let the bar visibly finish before moving on
        while (error == null && shown < 0.985) await Task.Delay(30);
        await Task.Delay(300);
        barTimer.Stop();
        working = false;
        index++;
        ShowPage();
    }

    void TickBar()
    {
        shown += (target - shown) * 0.12;
        var full = Math.Max(0, ((FrameworkElement)BarFill.Parent).ActualWidth);
        BarFill.Width = full * shown;
        Pct.Text = $"{(int)(shown * 100 + 0.5)}%";
        // a shine that sweeps along the filled part
        var t = (Environment.TickCount64 % 1400) / 1400.0;
        BarShine.Margin = new Thickness(Math.Max(0, BarFill.Width - 60) * t, 0, 0, 0);
        BarShine.Visibility = BarFill.Width > 60 ? Visibility.Visible : Visibility.Collapsed;
    }

    void ShowDone()
    {
        bool ok = error == null;
        Badge.Background = (Brush)FindResource(ok ? "B.Green" : "B.Red");
        BadgeGlow.Color = ok ? Color.FromRgb(0x59, 0xff, 0x80) : Color.FromRgb(0xff, 0x5a, 0x66);
        BadgeIcon.Text = ok ? "" : "";
        DoneTitle.Text = !ok ? "Something went wrong"
            : mode == "uninstall" ? "Altar was removed"
            : mode == "update" ? $"Updated to v{Config.Version}" : "Altar is installed!";
        DoneText.Text = !ok ? error + $"\n\nA report was saved in {Diagnostics.CrashDir}."
            : mode == "uninstall" ? "Thanks for playing with Altar."
            : "Start Isaac and press F2 in a run (or click the gem in the corner).\nF4 opens the command console. Floor 14 is waiting.";
        DoneText.Foreground = (Brush)FindResource(ok ? "B.Sub" : "B.Red");
        if (mode == "update") OptLaunch.IsChecked = true;
        NextButton.Content = ok && mode != "uninstall" && OptLaunch.IsChecked == true ? "Open Altar" : "Finish";
        // the badge pops in with a little overshoot
        var pop = new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(520)) { EasingFunction = new BackEase { EasingMode = EasingMode.EaseOut, Amplitude = 0.55 } };
        Badge.RenderTransform.BeginAnimation(ScaleTransform.ScaleXProperty, pop);
        Badge.RenderTransform.BeginAnimation(ScaleTransform.ScaleYProperty, pop);
    }
}
