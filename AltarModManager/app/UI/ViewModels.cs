using System.ComponentModel;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Altar.Core;

namespace Altar;

public abstract class Observable : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;
    protected void Notify([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
    protected void NotifyAll() => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(null));
}

/// <summary>A mod card. Setting Enabled writes/removes disable.it and tells the window.</summary>
public class ModVM : Observable
{
    readonly Action<ModVM, bool, Exception?> onToggled;
    bool selected, conflicted;
    (int files, long bytes)? stats;

    public ModVM(Mod mod, bool conflicted, Action<ModVM, bool, Exception?> onToggled)
    {
        Mod = mod;
        this.conflicted = conflicted;
        this.onToggled = onToggled;
        Thumb = Images.FromFile(mod.Thumb);
    }

    public Mod Mod { get; }
    public string Name => Mod.Name;
    public string Version => "v" + Mod.Version;
    public string Description => Mod.Description != "" ? Mod.Description : Mod.Folder;
    public string FullDescription => Mod.Description != "" ? Mod.Description : "No description.";
    public bool IsCore => Mod.IsCore;
    public ImageSource? Thumb { get; }
    public string Initial => Name.FirstOrDefault(char.IsLetterOrDigit).ToString().ToUpperInvariant();
    public Brush TileBrush => Images.TileBrush(Mod.Folder);

    public bool Enabled
    {
        get => Mod.Enabled;
        set
        {
            if (value == Mod.Enabled) return;
            Exception? error = null;
            try { Mod.Enabled = value; }
            catch (Exception e) { error = e; }
            NotifyAll();
            onToggled(this, value, error);
        }
    }

    public bool IsSelected { get => selected; set { selected = value; Notify(); } }
    public bool Conflicted { get => conflicted; set { conflicted = value; Notify(); } }

    (int files, long bytes) Stats => stats ??= Mod.Stats();
    public string FilesText => Stats.files.ToString();
    public string SizeText => ModStore.HumanSize(Stats.bytes);
    public string Kind => Mod.Kind;
    public string Folder => Mod.Folder;
    public string WorkshopId => Mod.WorkshopId;
}

/// <summary>A card on the Browse page (a mod from the Altar library).</summary>
public class LibraryModVM : Observable
{
    string state;
    double progress;

    public LibraryModVM(RegistryMod mod, string state)
    {
        Mod = mod;
        this.state = state;
    }

    public RegistryMod Mod { get; }
    public string Name => Mod.Name;
    public string Byline => $"v{Mod.Version}  ·  by {Mod.Author}  ·  {ModStore.HumanSize(Mod.Size)}";
    public string Description => Mod.Description != "" ? Mod.Description : "No description.";
    public string Initial => Name.FirstOrDefault(char.IsLetterOrDigit).ToString().ToUpperInvariant();
    public Brush TileBrush => Images.TileBrush(Mod.Folder);
    public bool HasNotes => Mod.Warnings > 0;
    public string NotesText => Mod.Warnings == 1 ? "1 admin note" : $"{Mod.Warnings} admin notes";

    /// <summary>install, update, installed or busy</summary>
    public string State { get => state; set { state = value; NotifyAll(); } }
    public double Progress { get => progress; set { progress = value; Notify(); } }
    public bool Busy => state == "busy";
    public bool IsInstalled => state is "installed" or "update";
    public string ButtonText => state switch
    {
        "update" => "Update", "installed" => "Installed", "busy" => "Installing...", _ => "Install",
    };
    public string ButtonIcon => state switch
    {
        "update" => "", "installed" => "", "busy" => "", _ => "",
    };
}

public record ProfileVM(string Name, int Count)
{
    public string CountText => Count == 1 ? "1 mod" : $"{Count} mods";
}

public record ConflictVM(string File, string Owners);

public record ItemVM(string Name, ImageSource? Image);

public static class Images
{
    static readonly Assembly Asm = typeof(Images).Assembly;

    /// <summary>Loads fully into memory so mod folders never stay locked (uninstall moves them).</summary>
    public static ImageSource? FromFile(string? path)
    {
        if (path == null) return null;
        try
        {
            var bmp = new BitmapImage();
            bmp.BeginInit();
            bmp.CacheOption = BitmapCacheOption.OnLoad;
            bmp.UriSource = new Uri(path);
            bmp.DecodePixelWidth = 192;
            bmp.EndInit();
            bmp.Freeze();
            return bmp;
        }
        catch (Exception) { return null; }
    }

    public static ImageSource? Embedded(string file)
    {
        using var s = Asm.GetManifestResourceStream("Altar.assets." + file);
        if (s == null) return null;
        var bmp = new BitmapImage();
        bmp.BeginInit();
        bmp.CacheOption = BitmapCacheOption.OnLoad;
        bmp.StreamSource = s;
        bmp.EndInit();
        bmp.Freeze();
        return bmp;
    }

    public static IEnumerable<string> EmbeddedItems() =>
        Asm.GetManifestResourceNames()
           .Where(n => n.StartsWith("Altar.assets.item_") && n.EndsWith(".png"))
           .Select(n => n["Altar.assets.".Length..])
           .Order();

    /// <summary>Stable two-colour gradient per mod, for mods without a thumbnail.</summary>
    public static Brush TileBrush(string seed)
    {
        int h = 17;
        foreach (var c in seed) h = h * 31 + c;
        double hue = Math.Abs(h % 360);
        var b = new LinearGradientBrush(Hsv(hue, 0.55, 0.85), Hsv((hue + 40) % 360, 0.65, 0.55), 45);
        b.Freeze();
        return b;
    }

    static Color Hsv(double h, double s, double v)
    {
        double c = v * s, x = c * (1 - Math.Abs(h / 60 % 2 - 1)), m = v - c;
        var (r, g, b) = h switch
        {
            < 60 => (c, x, 0.0), < 120 => (x, c, 0.0), < 180 => (0.0, c, x),
            < 240 => (0.0, x, c), < 300 => (x, 0.0, c), _ => (c, 0.0, x),
        };
        return Color.FromRgb((byte)((r + m) * 255), (byte)((g + m) * 255), (byte)((b + m) * 255));
    }
}
