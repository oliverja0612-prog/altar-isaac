using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Effects;
using Altar.Core;

namespace Altar;

public enum CrashChoice { Close, Continue, Restart }

/// <summary>Shown when Altar hits an unhandled error: what happened, the report, and what to do next.</summary>
public static class CrashWindow
{
    static Brush Res(string key) => (Brush)Application.Current.Resources[key];
    static Style S(string key) => (Style)Application.Current.Resources[key];

    public static CrashChoice Show(Exception ex, string where, bool canContinue)
    {
        var report = Diagnostics.Describe(ex, where);
        var path = Diagnostics.WriteCrash(ex, where);
        var choice = CrashChoice.Close;

        var win = new Window
        {
            Title = "Altar crashed",
            WindowStyle = WindowStyle.None,
            AllowsTransparency = true,
            Background = Brushes.Transparent,
            ResizeMode = ResizeMode.NoResize,
            SizeToContent = SizeToContent.WidthAndHeight,
            WindowStartupLocation = WindowStartupLocation.CenterScreen,
            Topmost = true,
            FontFamily = (FontFamily)Application.Current.Resources["F.Ui"],
        };

        var icon = new Border
        {
            Width = 44, Height = 44, CornerRadius = new CornerRadius(22),
            Background = new SolidColorBrush(Color.FromArgb(0x33, 0xff, 0x5a, 0x66)),
            Child = new TextBlock
            {
                Text = "", FontFamily = (FontFamily)Application.Current.Resources["F.Icon"], FontSize = 20,
                Foreground = Res("B.Red"), HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center,
            },
        };
        var head = new StackPanel { Margin = new Thickness(14, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center };
        head.Children.Add(new TextBlock { Text = "Altar ran into a problem", FontSize = 20, FontWeight = FontWeights.SemiBold, Foreground = Res("B.Text") });
        head.Children.Add(new TextBlock
        {
            Text = canContinue ? "You can keep going, but something may not work until you restart."
                               : "Altar has to close. Your mods and settings are safe.",
            FontSize = 13, Foreground = Res("B.Sub"),
        });
        var top = new StackPanel { Orientation = Orientation.Horizontal };
        top.Children.Add(icon);
        top.Children.Add(head);

        var details = new TextBox
        {
            Text = report, IsReadOnly = true, TextWrapping = TextWrapping.NoWrap, FontFamily = new FontFamily("Cascadia Mono, Consolas"),
            FontSize = 11.5, Foreground = Res("B.Sub"), Background = Res("B.Bg"), BorderThickness = new Thickness(0),
            Padding = new Thickness(10), Height = 220, Width = 600,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto, HorizontalScrollBarVisibility = ScrollBarVisibility.Auto,
        };
        var detailsBox = new Border { CornerRadius = new CornerRadius(8), ClipToBounds = true, Margin = new Thickness(0, 16, 0, 0), Child = details };
        var saved = new TextBlock
        {
            Text = path != null ? "Report saved: " + path : "The report couldn't be saved.",
            FontSize = 11.5, Foreground = Res("B.Dim"), Margin = new Thickness(0, 8, 0, 0), TextTrimming = TextTrimming.CharacterEllipsis, MaxWidth = 600,
        };

        Button B(string text, string style, Action onClick, string? glyph = null)
        {
            var b = new Button { Content = text, Style = S(style), Margin = new Thickness(8, 0, 0, 0), Tag = glyph };
            b.Click += (_, _) => onClick();
            return b;
        }
        var copy = B("Copy details", "Btn", () => { }, "");
        copy.Click += (_, _) =>
        {
            try { Clipboard.SetText(report); copy.Content = "Copied"; } catch (Exception) { }
        };
        var left = new StackPanel { Orientation = Orientation.Horizontal };
        left.Children.Add(copy);
        left.Children.Add(B("Crash folder", "Btn", () =>
        {
            Directory.CreateDirectory(Diagnostics.CrashDir);
            Process.Start(new ProcessStartInfo("explorer.exe", $"\"{Diagnostics.CrashDir}\"") { UseShellExecute = true });
        }, ""));
        ((Button)left.Children[0]).Margin = new Thickness(0);

        var right = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        if (canContinue) right.Children.Add(B("Keep going", "Btn", () => { choice = CrashChoice.Continue; win.Close(); }));
        else right.Children.Add(B("Close", "Btn", () => { choice = CrashChoice.Close; win.Close(); }));
        right.Children.Add(B("Restart Altar", "Btn.Accent", () => { choice = CrashChoice.Restart; win.Close(); }, ""));

        var buttons = new Grid { Margin = new Thickness(0, 18, 0, 0) };
        buttons.Children.Add(left);
        buttons.Children.Add(right);

        var body = new StackPanel();
        body.Children.Add(top);
        body.Children.Add(detailsBox);
        body.Children.Add(saved);
        body.Children.Add(buttons);

        var card = new Border
        {
            Background = Res("B.Panel"), BorderBrush = Res("B.Border"), BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(12), Padding = new Thickness(24, 22, 24, 20), Margin = new Thickness(24),
            Child = body, Effect = new DropShadowEffect { BlurRadius = 30, ShadowDepth = 6, Opacity = 0.6, Color = Colors.Black },
        };
        card.MouseLeftButtonDown += (_, e) => { if (e.ButtonState == MouseButtonState.Pressed) win.DragMove(); };
        win.Content = card;
        win.KeyDown += (_, e) => { if (e.Key == Key.Escape) win.Close(); };
        win.ShowDialog();

        if (choice == CrashChoice.Restart)
        {
            try
            {
                var args = string.Join(" ", Environment.GetCommandLineArgs().Skip(1).Select(a => a.Contains(' ') ? $"\"{a}\"" : a));
                Process.Start(new ProcessStartInfo(Environment.ProcessPath!, args) { UseShellExecute = true });
            }
            catch (Exception) { }
        }
        return choice;
    }
}
