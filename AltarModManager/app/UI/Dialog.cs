using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;

namespace Altar;

/// <summary>Themed replacement for MessageBox: rounded card, pop-in animation.</summary>
public static class Dialog
{
    static Brush Res(string key) => (Brush)Application.Current.Resources[key];

    public static void Info(Window? owner, string title, string message) =>
        Show(owner, title, message, "OK", null);

    public static bool Ask(Window? owner, string title, string message, string yes = "Yes", string no = "Cancel", bool danger = false) =>
        Show(owner, title, message, yes, no, danger);

    static bool Show(Window? owner, string title, string message, string yes, string? no, bool danger = false)
    {
        var win = new Window
        {
            WindowStyle = WindowStyle.None,
            AllowsTransparency = true,
            Background = Brushes.Transparent,
            ResizeMode = ResizeMode.NoResize,
            SizeToContent = SizeToContent.WidthAndHeight,
            ShowInTaskbar = owner == null,
            Title = title,
            WindowStartupLocation = owner != null ? WindowStartupLocation.CenterOwner : WindowStartupLocation.CenterScreen,
            FontFamily = (FontFamily)Application.Current.Resources["F.Ui"],
        };
        if (owner != null && owner.IsVisible) win.Owner = owner;
        bool result = false;

        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 22, 0, 0) };
        if (no != null)
        {
            var b = new Button { Content = no, Style = (Style)Application.Current.Resources["Btn"], MinWidth = 96, Margin = new Thickness(0, 0, 8, 0) };
            b.Click += (_, _) => win.Close();
            buttons.Children.Add(b);
        }
        var ok = new Button { Content = yes, Style = (Style)Application.Current.Resources[danger ? "Btn.Danger" : "Btn.Accent"], MinWidth = 96 };
        ok.Click += (_, _) => { result = true; win.Close(); };
        buttons.Children.Add(ok);

        var body = new StackPanel { Width = 420 };
        body.Children.Add(new TextBlock { Text = title, FontSize = 20, FontWeight = FontWeights.SemiBold, Foreground = Res("B.Text"), Margin = new Thickness(0, 0, 0, 10) });
        body.Children.Add(new TextBlock { Text = message, FontSize = 13.5, Foreground = Res("B.Sub"), TextWrapping = TextWrapping.Wrap, LineHeight = 20 });
        body.Children.Add(buttons);

        var card = new Border
        {
            Background = Res("B.Panel"),
            BorderBrush = Res("B.Border"),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(12),
            Padding = new Thickness(24, 22, 24, 20),
            Margin = new Thickness(24),
            Child = body,
            Effect = new DropShadowEffect { BlurRadius = 30, ShadowDepth = 6, Opacity = 0.6, Color = Colors.Black },
            RenderTransformOrigin = new Point(0.5, 0.5),
            RenderTransform = new ScaleTransform(0.94, 0.94),
            Opacity = 0,
        };
        card.MouseLeftButtonDown += (_, e) => { if (e.ButtonState == MouseButtonState.Pressed) win.DragMove(); };
        win.Content = card;
        win.KeyDown += (_, e) =>
        {
            if (e.Key == Key.Escape) win.Close();
            else if (e.Key == Key.Enter) { result = true; win.Close(); }
        };
        win.Loaded += (_, _) =>
        {
            var d = TimeSpan.FromMilliseconds(180);
            var ease = new CubicEase { EasingMode = EasingMode.EaseOut };
            card.BeginAnimation(UIElement.OpacityProperty, new DoubleAnimation(1, d));
            card.RenderTransform.BeginAnimation(ScaleTransform.ScaleXProperty, new DoubleAnimation(1, d) { EasingFunction = ease });
            card.RenderTransform.BeginAnimation(ScaleTransform.ScaleYProperty, new DoubleAnimation(1, d) { EasingFunction = ease });
        };
        win.ShowDialog();
        return result;
    }
}
