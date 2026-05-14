using System.Runtime.InteropServices;
using Microsoft.UI;
using Microsoft.UI.Text;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Media.Imaging;
using QRCoder;
using SurveySentenceGenerator.Models;
using SurveySentenceGenerator.Services;
using Windows.ApplicationModel.DataTransfer;
using Windows.Storage.Streams;
using Windows.UI;

namespace SurveySentenceGenerator;

public sealed partial class MainWindow : Window
{
    private const string AppVersion = "2.0.0";

    // ── Category colour palette: (inactive bg, inactive fg, active bg, active fg) ─
    private static readonly (string LB, string LF, string AB, string AF)[] CatColors =
    {
        ("#3B82F6", "#FFFFFF", "#1D4ED8", "#FFFFFF"),  // Blue
        ("#10B981", "#FFFFFF", "#059669", "#FFFFFF"),  // Green
        ("#D97706", "#FFFFFF", "#92400E", "#FFFFFF"),  // Amber
        ("#EF4444", "#FFFFFF", "#B91C1C", "#FFFFFF"),  // Red
        ("#8B5CF6", "#FFFFFF", "#6D28D9", "#FFFFFF"),  // Purple
        ("#EC4899", "#FFFFFF", "#BE185D", "#FFFFFF"),  // Pink
        ("#14B8A6", "#FFFFFF", "#0F766E", "#FFFFFF"),  // Teal
        ("#F97316", "#FFFFFF", "#C2410C", "#FFFFFF"),  // Orange
    };

    // ── Phrase button colours: light mode (pastel bg, dark fg) ───────────────
    private static readonly (string Bg, string Fg)[] PhraseLightColors =
    {
        ("#BFDBFE", "#1E3A8A"),
        ("#A7F3D0", "#064E3B"),
        ("#FDE68A", "#78350F"),
        ("#FECACA", "#7F1D1D"),
        ("#DDD6FE", "#3B0764"),
        ("#FBCFE8", "#500724"),
        ("#99F6E4", "#0F3D3A"),
        ("#FED7AA", "#431407"),
    };

    // ── Phrase button colours: dark mode (deep bg, light fg) ─────────────────
    private static readonly (string Bg, string Fg)[] PhraseDarkColors =
    {
        ("#1E3A5F", "#BFDBFE"),
        ("#064E3B", "#A7F3D0"),
        ("#78350F", "#FDE68A"),
        ("#7F1D1D", "#FECACA"),
        ("#3B0764", "#DDD6FE"),
        ("#500724", "#FBCFE8"),
        ("#0F3D3A", "#99F6E4"),
        ("#431407", "#FED7AA"),
    };

    // ── App state ────────────────────────────────────────────────────────────
    private PhrasesData  _phrases  = new();
    private AppSettings  _settings = new();
    private UsageData    _usage    = new();
    private int          _activeTab = 0;
    private bool         _editMode  = false;
    private readonly List<string> _history = new();
    private readonly GroqService  _groq    = new();
    private MobileServerService?  _mobile;
    private TunnelService?        _tunnel;

    // ── Named UI controls ────────────────────────────────────────────────────
    private Grid         _appTitleBar   = null!;
    private StackPanel   _btnPanel      = null!;
    private ScrollViewer _phraseScroller = null!;
    private TextBlock  _versionText   = null!;
    private Button     _updateBtn     = null!;
    private Button     _settingsBtn   = null!;
    private Button     _mobileBtn     = null!;
    private Button     _editPhrasesBtn = null!;
    private Button     _fieldModeBtn  = null!;
    private FontIcon   _fieldModeIcon = null!;
    private TextBlock  _fieldModeText = null!;
    private Border     _sentenceBorder = null!;
    private TextBox    _sentenceBox   = null!;
    private ScrollViewer _suggestionsScroll = null!;
    private StackPanel   _suggestionsPanel  = null!;
    private Grid       _tabStripGrid  = null!;
    private Grid       _phraseGrid    = null!;
    private Grid       _actionBar     = null!;
    private Button     _cleanBtn      = null!;
    private TextBlock  _cleanBtnText  = null!;
    private Grid       _statusBar     = null!;
    private FontIcon   _wifiIcon      = null!;
    private TextBlock  _statusText    = null!;

    // ── Win32 SendInput ──────────────────────────────────────────────────────
    [DllImport("user32.dll")] private static extern uint SendInput(uint n, INPUT[] inputs, int sz);
    [StructLayout(LayoutKind.Sequential)]
    private struct INPUT { public uint type; public UNION u; }
    [StructLayout(LayoutKind.Explicit)]
    private struct UNION { [FieldOffset(0)] public KEYBDINPUT ki; }
    [StructLayout(LayoutKind.Sequential)]
    private struct KEYBDINPUT { public ushort wVk, wScan; public uint dwFlags, time; public nuint extra; }
    private const uint  INPUT_KEYBOARD  = 1;
    private const uint  KEYEVENTF_KEYUP = 2;
    private const byte  VK_CONTROL      = 0x11;
    private const byte  VK_V            = 0x56;

    // ────────────────────────────────────────────────────────────────────────
    public MainWindow()
    {
        Title = "Survey Sentence Generator";

        _phrases  = DataService.LoadPhrases();
        _settings = DataService.LoadSettings();
        _usage    = DataService.LoadUsage();

        var ui = (FrameworkElement)BuildUi();
        Content = ui;

        SetupWindow();
        TrySetMicaBackdrop();
        ApplyTheme();

        _statusText.Text = $"Ready  |  v{AppVersion}";
        _versionText.Text = $"v{AppVersion}";
        _ = Task.Run(CheckForUpdateAsync);

        if (!_settings.TosAccepted)
            ui.Loaded += async (_, _) => await RunFirstTimeSetupAsync();
    }

    // ── Root UI ───────────────────────────────────────────────────────────────
    private UIElement BuildUi()
    {
        var root = new Grid();
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        _appTitleBar = BuildHeader();
        Grid.SetRow(_appTitleBar, 0);
        root.Children.Add(_appTitleBar);

        _sentenceBorder = BuildSentenceArea();
        Grid.SetRow(_sentenceBorder, 1);
        root.Children.Add(_sentenceBorder);

        var sugg = BuildSuggestionsStrip();
        Grid.SetRow(sugg, 2);
        root.Children.Add(sugg);

        var tabContent = BuildTabContent();
        Grid.SetRow(tabContent, 3);
        root.Children.Add(tabContent);

        _actionBar = BuildActionBar();
        Grid.SetRow(_actionBar, 4);
        root.Children.Add(_actionBar);

        _statusBar = BuildStatusBar();
        Grid.SetRow(_statusBar, 5);
        root.Children.Add(_statusBar);

        return root;
    }

    // ── Header ────────────────────────────────────────────────────────────────
    private Grid BuildHeader()
    {
        var grid = new Grid
        {
            Background = new SolidColorBrush(ParseColor("#1E3A5F")),
            MinHeight  = 72,
            Padding    = new Thickness(16, 0, 8, 0),
        };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        // Left: title + version + update button
        _versionText = new TextBlock
        {
            Text = "v2.0.0", FontSize = 13,
            Foreground = new SolidColorBrush(ParseColor("#7FA8CC")),
            VerticalAlignment = VerticalAlignment.Center,
        };
        _updateBtn = new Button
        {
            Content = "↑ Update", FontSize = 13, FontWeight = FontWeights.SemiBold,
            Foreground = new SolidColorBrush(ParseColor("#FCD34D")),
            Background = new SolidColorBrush(Colors.Transparent),
            BorderBrush = new SolidColorBrush(ParseColor("#FCD34D")),
            BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(4),
            Padding = new Thickness(8, 4, 8, 4), Visibility = Visibility.Collapsed,
        };
        _updateBtn.Click += UpdateBtn_Click;

        var titlePanel = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            VerticalAlignment = VerticalAlignment.Center,
            Spacing = 12,
        };
        titlePanel.Children.Add(new TextBlock
        {
            Text = "Survey Sentence Generator", FontSize = 22, FontWeight = FontWeights.Bold,
            Foreground = new SolidColorBrush(Colors.White),
            VerticalAlignment = VerticalAlignment.Center,
        });
        titlePanel.Children.Add(_versionText);
        titlePanel.Children.Add(_updateBtn);
        Grid.SetColumn(titlePanel, 0);
        grid.Children.Add(titlePanel);

        // Right: action buttons
        _settingsBtn    = MakeHeaderButton("", "Settings");
        _mobileBtn      = MakeHeaderButton("", "Mobile");
        _editPhrasesBtn = MakeHeaderButton("", "Edit Phrases");

        _fieldModeIcon = new FontIcon { Glyph = "", FontSize = 18, Foreground = new SolidColorBrush(Colors.White) };
        _fieldModeText = new TextBlock { Text = "Field Mode", Foreground = new SolidColorBrush(Colors.White), FontSize = 15, FontWeight = FontWeights.SemiBold };
        var fieldContent = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8 };
        fieldContent.Children.Add(_fieldModeIcon);
        fieldContent.Children.Add(_fieldModeText);
        _fieldModeBtn = MakeHeaderButtonWithContent(fieldContent);

        _settingsBtn.Click    += SettingsBtn_Click;
        _mobileBtn.Click      += MobileBtn_Click;
        _editPhrasesBtn.Click += EditPhrasesBtn_Click;
        _fieldModeBtn.Click   += FieldModeBtn_Click;

        _btnPanel = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            VerticalAlignment = VerticalAlignment.Center,
            Spacing = 6,
        };
        _btnPanel.Children.Add(_settingsBtn);
        _btnPanel.Children.Add(_mobileBtn);
        _btnPanel.Children.Add(_editPhrasesBtn);
        _btnPanel.Children.Add(_fieldModeBtn);
        Grid.SetColumn(_btnPanel, 2);
        grid.Children.Add(_btnPanel);

        return grid;
    }

    private Button MakeHeaderButton(string glyph, string label)
    {
        var content = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8 };
        content.Children.Add(new FontIcon { Glyph = glyph, FontSize = 18, Foreground = new SolidColorBrush(Colors.White) });
        content.Children.Add(new TextBlock { Text = label, Foreground = new SolidColorBrush(Colors.White), FontSize = 15, FontWeight = FontWeights.SemiBold });
        return MakeHeaderButtonWithContent(content);
    }

    private static Button MakeHeaderButtonWithContent(UIElement content) => new()
    {
        Content = content, Height = 48, MinWidth = 140,
        Padding = new Thickness(16, 0, 16, 0),
        Background = new SolidColorBrush(Colors.Transparent),
        BorderBrush = new SolidColorBrush(ParseColor("#3A5A7A")),
        BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(6),
        VerticalAlignment = VerticalAlignment.Center,
    };

    // ── Sentence area ─────────────────────────────────────────────────────────
    private Border BuildSentenceArea()
    {
        _sentenceBox = new TextBox
        {
            MinHeight = 110, AcceptsReturn = true, TextWrapping = TextWrapping.Wrap,
            FontSize = 16, PlaceholderText = "Tap phrases below to build your survey description…",
            BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(4),
            Padding = new Thickness(10, 8, 10, 8),
        };
        var label = new TextBlock
        {
            Text = "GENERATED SENTENCE", FontSize = 11, FontWeight = FontWeights.SemiBold,
            Foreground = new SolidColorBrush(ParseColor("#64748B")),
            Margin = new Thickness(0, 0, 0, 6),
        };
        var inner = new Grid();
        inner.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        inner.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        Grid.SetRow(label, 0);
        Grid.SetRow(_sentenceBox, 1);
        inner.Children.Add(label);
        inner.Children.Add(_sentenceBox);

        return new Border
        {
            Child = inner,
            Background = new SolidColorBrush(Colors.White),
            BorderBrush = new SolidColorBrush(ParseColor("#CBD5E1")),
            BorderThickness = new Thickness(0, 0, 0, 1),
            Padding = new Thickness(14, 12, 14, 10),
        };
    }

    // ── Suggestion strip ──────────────────────────────────────────────────────
    private ScrollViewer BuildSuggestionsStrip()
    {
        _suggestionsPanel = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 6 };
        _suggestionsScroll = new ScrollViewer
        {
            Content = _suggestionsPanel,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Auto,
            VerticalScrollBarVisibility   = ScrollBarVisibility.Disabled,
            Visibility = Visibility.Collapsed,
            Padding = new Thickness(12, 6, 12, 6),
        };
        return _suggestionsScroll;
    }

    // ── Tab strip + phrase area ────────────────────────────────────────────────
    private Grid BuildTabContent()
    {
        _tabStripGrid = new Grid
        {
            Height = 56,
            BorderBrush = new SolidColorBrush(ParseColor("#CBD5E1")),
            BorderThickness = new Thickness(0, 1, 0, 0),
        };

        _phraseGrid = new Grid { Margin = new Thickness(6) };

        _phraseScroller = new ScrollViewer
        {
            Content = _phraseGrid,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
            VerticalScrollBarVisibility   = ScrollBarVisibility.Auto,
        };

        var container = new Grid();
        container.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        container.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        Grid.SetRow(_tabStripGrid, 0);
        Grid.SetRow(_phraseScroller, 1);
        container.Children.Add(_tabStripGrid);
        container.Children.Add(_phraseScroller);
        return container;
    }

    // ── Action bar ────────────────────────────────────────────────────────────
    private Grid BuildActionBar()
    {
        var bar = new Grid
        {
            Background = new SolidColorBrush(ParseColor("#F1F5F9")),
            Padding = new Thickness(12, 10, 12, 10),
            BorderBrush = new SolidColorBrush(ParseColor("#CBD5E1")),
            BorderThickness = new Thickness(0, 1, 0, 0),
        };
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        var clearBtn = MakeActionButton("", "Clear", null, null, isOutline: true);
        clearBtn.Click += ClearBtn_Click;
        clearBtn.Margin = new Thickness(0, 0, 8, 0);

        var undoBtn = MakeActionButton("", "Undo", null, null, isOutline: true);
        undoBtn.Click += UndoBtn_Click;

        _cleanBtnText = new TextBlock { Text = "Clean", Foreground = new SolidColorBrush(Colors.White), FontSize = 18, FontWeight = FontWeights.Bold };
        var cleanContent = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8 };
        cleanContent.Children.Add(new FontIcon { Glyph = "", FontSize = 18, Foreground = new SolidColorBrush(Colors.White) });
        cleanContent.Children.Add(_cleanBtnText);
        _cleanBtn = new Button
        {
            Content = cleanContent, Height = 60, MinWidth = 160,
            Padding = new Thickness(20, 0, 20, 0), BorderThickness = new Thickness(0),
            CornerRadius = new CornerRadius(6), Margin = new Thickness(0, 0, 8, 0),
            Background = new SolidColorBrush(ParseColor("#2563EB")),
        };
        _cleanBtn.Click += CleanBtn_Click;

        var goContent = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8 };
        goContent.Children.Add(new FontIcon { Glyph = "", FontSize = 20, Foreground = new SolidColorBrush(Colors.White) });
        goContent.Children.Add(new TextBlock { Text = "GO", Foreground = new SolidColorBrush(Colors.White), FontSize = 22, FontWeight = FontWeights.ExtraBold });
        var goBtn = new Button
        {
            Content = goContent, Height = 60, MinWidth = 160,
            Padding = new Thickness(20, 0, 20, 0), BorderThickness = new Thickness(0),
            CornerRadius = new CornerRadius(6),
            Background = new SolidColorBrush(ParseColor("#059669")),
        };
        goBtn.Click += GoBtn_Click;

        Grid.SetColumn(clearBtn, 0);
        Grid.SetColumn(undoBtn,  1);
        Grid.SetColumn(_cleanBtn, 3);
        Grid.SetColumn(goBtn,    4);

        bar.Children.Add(clearBtn);
        bar.Children.Add(undoBtn);
        bar.Children.Add(_cleanBtn);
        bar.Children.Add(goBtn);
        return bar;
    }

    private static Button MakeActionButton(string glyph, string label, string? bgHex, string? fgHex, bool isOutline)
    {
        var content = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8 };
        var iconFg = isOutline ? ParseColor("#0F172A") : Colors.White;
        content.Children.Add(new FontIcon { Glyph = glyph, FontSize = 18, Foreground = new SolidColorBrush(iconFg) });
        content.Children.Add(new TextBlock
        {
            Text = label,
            Foreground = new SolidColorBrush(isOutline ? ParseColor("#0F172A") : Colors.White),
            FontSize = 18, FontWeight = FontWeights.Bold,
        });
        return new Button
        {
            Content = content, Height = 60, MinWidth = 140,
            Padding = new Thickness(18, 0, 18, 0),
            Background = isOutline ? new SolidColorBrush(Colors.White) : new SolidColorBrush(ParseColor(bgHex ?? "#000000")),
            BorderBrush = isOutline ? new SolidColorBrush(ParseColor("#94A3B8")) : null,
            BorderThickness = isOutline ? new Thickness(2) : new Thickness(0),
            CornerRadius = new CornerRadius(6),
        };
    }

    // ── Status bar ────────────────────────────────────────────────────────────
    private Grid BuildStatusBar()
    {
        _wifiIcon = new FontIcon { Glyph = "", FontSize = 13, Foreground = new SolidColorBrush(ParseColor("#059669")) };
        _statusText = new TextBlock { FontSize = 12, Foreground = new SolidColorBrush(ParseColor("#475569")), VerticalAlignment = VerticalAlignment.Center };

        var left = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center, Spacing = 8 };
        left.Children.Add(_wifiIcon);
        left.Children.Add(_statusText);

        var copyright = new TextBlock
        {
            Text = "© 2026 Survey Sentence Generator",
            FontSize = 12,
            Foreground = new SolidColorBrush(ParseColor("#94A3B8")),
            VerticalAlignment = VerticalAlignment.Center,
            HorizontalAlignment = HorizontalAlignment.Right,
        };

        var bar = new Grid
        {
            Background = new SolidColorBrush(ParseColor("#E2E8F0")),
            Height = 30,
            Padding = new Thickness(12, 0, 12, 0),
        };
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetColumn(left, 0);
        Grid.SetColumn(copyright, 1);
        bar.Children.Add(left);
        bar.Children.Add(copyright);
        return bar;
    }

    // ── Window setup ──────────────────────────────────────────────────────────
    private void SetupWindow()
    {
        ExtendsContentIntoTitleBar = true;
        SetTitleBar(_appTitleBar);

        // Style caption buttons to blend with the dark-blue header
        var tb = AppWindow.TitleBar;
        tb.ButtonBackgroundColor         = ParseColor("#1E3A5F");
        tb.ButtonForegroundColor         = Colors.White;
        tb.ButtonHoverBackgroundColor    = ParseColor("#2A4A6F");
        tb.ButtonHoverForegroundColor    = Colors.White;
        tb.ButtonPressedBackgroundColor  = ParseColor("#0E2A4F");
        tb.ButtonPressedForegroundColor  = Colors.White;
        tb.ButtonInactiveBackgroundColor = ParseColor("#1E3A5F");
        tb.ButtonInactiveForegroundColor = ParseColor("#7FA8CC");

        // Keep button panel clear of the caption button zone
        AppWindow.Changed += (_, _) =>
        {
            if (_btnPanel is null) return;
            double scale = _appTitleBar.XamlRoot?.RasterizationScale ?? 1.0;
            _btnPanel.Margin = new Thickness(0, 0, AppWindow.TitleBar.RightInset / scale, 0);
        };

        if (AppWindow.Presenter is OverlappedPresenter overlapped)
            overlapped.Maximize();

        AppWindow.Closing += (_, _) =>
        {
            _settings.WindowWidth  = AppWindow.Size.Width;
            _settings.WindowHeight = AppWindow.Size.Height;
            DataService.SaveSettings(_settings);
            DataService.SaveUsage(_usage);
            _tunnel?.Dispose();
            _mobile?.Dispose();
        };
    }

    private void TrySetMicaBackdrop()
    {
        if (Environment.OSVersion.Version.Build >= 22000)
        {
            try { SystemBackdrop = new Microsoft.UI.Xaml.Media.MicaBackdrop(); }
            catch { }
        }
    }

    // ── Theme ─────────────────────────────────────────────────────────────────
    private void ApplyTheme()
    {
        bool dark = _settings.DarkMode;
        if (dark)
        {
            _sentenceBorder.Background = new SolidColorBrush(ParseColor("#0D1117"));
            _sentenceBox.Background    = new SolidColorBrush(ParseColor("#161B22"));
            _sentenceBox.Foreground    = new SolidColorBrush(Colors.White);
            _sentenceBox.BorderBrush   = new SolidColorBrush(ParseColor("#30363D"));
            _actionBar.Background      = new SolidColorBrush(ParseColor("#0D1117"));
            _actionBar.BorderBrush     = new SolidColorBrush(ParseColor("#30363D"));
            _phraseScroller.Background = new SolidColorBrush(ParseColor("#0D1117"));
            _tabStripGrid.Background   = new SolidColorBrush(ParseColor("#161B22"));
            _statusBar.Background      = new SolidColorBrush(ParseColor("#010409"));
            _statusText.Foreground     = new SolidColorBrush(ParseColor("#E6EDF3"));
        }
        else
        {
            _sentenceBorder.Background = new SolidColorBrush(Colors.White);
            _sentenceBox.Background    = new SolidColorBrush(Colors.White);
            _sentenceBox.Foreground    = new SolidColorBrush(ParseColor("#0F172A"));
            _sentenceBox.BorderBrush   = new SolidColorBrush(ParseColor("#CBD5E1"));
            _actionBar.Background      = new SolidColorBrush(ParseColor("#F1F5F9"));
            _actionBar.BorderBrush     = new SolidColorBrush(ParseColor("#CBD5E1"));
            _phraseScroller.Background = new SolidColorBrush(ParseColor("#F8FAFC"));
            _tabStripGrid.Background   = new SolidColorBrush(Colors.White);
            _statusBar.Background      = new SolidColorBrush(ParseColor("#E2E8F0"));
            _statusText.Foreground     = new SolidColorBrush(ParseColor("#475569"));
        }
        _fieldModeText.Text  = dark ? "Light Mode" : "Field Mode";
        _fieldModeIcon.Glyph = dark ? "" : "";

        BuildTabStrip();
        BuildPhraseGrid(_activeTab);
    }

    // ── Tab strip (full-width equal columns) ──────────────────────────────────
    private void BuildTabStrip()
    {
        _tabStripGrid.ColumnDefinitions.Clear();
        _tabStripGrid.Children.Clear();

        var cats = _phrases.Categories;
        for (int i = 0; i < cats.Count; i++)
        {
            _tabStripGrid.ColumnDefinitions.Add(
                new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            int idx = i;
            bool isActive = (i == _activeTab);
            var (lb, lf, ab, af) = GetCatColor(i);

            var btn = new Button
            {
                Content  = cats[i].Name,
                FontSize = 17, FontWeight = FontWeights.Bold,
                HorizontalAlignment = HorizontalAlignment.Stretch,
                VerticalAlignment   = VerticalAlignment.Stretch,
                HorizontalContentAlignment = HorizontalAlignment.Center,
                BorderThickness = new Thickness(0, 0, i < cats.Count - 1 ? 1 : 0, isActive ? 3 : 0),
                BorderBrush     = new SolidColorBrush(ParseColor(isActive ? ab : "#CBD5E1")),
                CornerRadius    = new CornerRadius(0),
                Padding         = new Thickness(0),
                Background      = new SolidColorBrush(ParseColor(isActive ? ab : lb)),
                Foreground      = new SolidColorBrush(ParseColor(isActive ? af : lf)),
            };
            btn.Click += (_, _) => SelectTab(idx);
            Grid.SetColumn(btn, i);
            _tabStripGrid.Children.Add(btn);
        }
    }

    private void SelectTab(int idx)
    {
        _activeTab = idx;
        BuildTabStrip();
        BuildPhraseGrid(idx);
    }

    // ── Phrase grid ───────────────────────────────────────────────────────────
    private void BuildPhraseGrid(int catIdx)
    {
        _phraseGrid.ColumnDefinitions.Clear();
        _phraseGrid.RowDefinitions.Clear();
        _phraseGrid.Children.Clear();

        var cat  = _phrases.Categories[catIdx];
        int cols = cat.Cols > 0 ? cat.Cols : 3;
        var (_, _, bgHex, fgHex) = GetCatColor(catIdx);

        int pi = catIdx % PhraseLightColors.Length;
        string pbBg = _settings.DarkMode ? PhraseDarkColors[pi].Bg : PhraseLightColors[pi].Bg;
        string pbFg = _settings.DarkMode ? PhraseDarkColors[pi].Fg : PhraseLightColors[pi].Fg;

        for (int c = 0; c < cols; c++)
            _phraseGrid.ColumnDefinitions.Add(
                new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

        for (int i = 0; i < cat.Phrases.Count; i++)
        {
            int row = i / cols, col = i % cols;
            while (_phraseGrid.RowDefinitions.Count <= row)
                _phraseGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(120) });

            var phrase = cat.Phrases[i];

            FrameworkElement cell = _editMode
                ? (FrameworkElement)BuildEditCell(catIdx, i, phrase, pbBg, pbFg)
                : BuildPhraseButton(phrase, catIdx, pbBg, pbFg);

            Grid.SetRow(cell, row);
            Grid.SetColumn(cell, col);
            _phraseGrid.Children.Add(cell);
        }

        // "Add phrase" button in edit mode
        if (_editMode)
        {
            int ai = cat.Phrases.Count;
            int ar = ai / cols, ac = ai % cols;
            while (_phraseGrid.RowDefinitions.Count <= ar)
                _phraseGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(120) });

            var addBtn = new Button
            {
                Content = "+ Add Phrase", FontSize = 16, FontWeight = FontWeights.SemiBold,
                HorizontalAlignment = HorizontalAlignment.Stretch,
                VerticalAlignment   = VerticalAlignment.Stretch,
                HorizontalContentAlignment = HorizontalAlignment.Center,
                Background = new SolidColorBrush(ParseColor("#F8FAFC")),
                BorderBrush = new SolidColorBrush(ParseColor("#CBD5E1")),
                BorderThickness = new Thickness(2), CornerRadius = new CornerRadius(4),
                Margin = new Thickness(3),
            };
            addBtn.Click += (_, _) => _ = AddNewPhraseAsync(catIdx);
            Grid.SetRow(addBtn, ar);
            Grid.SetColumn(addBtn, ac);
            _phraseGrid.Children.Add(addBtn);
        }
    }

    private Button BuildPhraseButton(string phrase, int catIdx, string bgHex, string fgHex)
    {
        var text = new TextBlock
        {
            Text = phrase,
            FontSize = _settings.FontSize,
            FontWeight = FontWeights.Bold,
            TextWrapping = TextWrapping.Wrap,
            TextAlignment = TextAlignment.Center,
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            Foreground = new SolidColorBrush(ParseColor(fgHex)),
        };
        var btn = new Button
        {
            Content = text,
            HorizontalAlignment = HorizontalAlignment.Stretch,
            VerticalAlignment   = VerticalAlignment.Stretch,
            HorizontalContentAlignment = HorizontalAlignment.Center,
            VerticalContentAlignment   = VerticalAlignment.Center,
            Background  = new SolidColorBrush(ParseColor(bgHex)),
            BorderThickness = new Thickness(1),
            BorderBrush = new SolidColorBrush(ParseColor("#00000030")),
            CornerRadius = new CornerRadius(6),
            Margin = new Thickness(4), Padding = new Thickness(10),
        };
        btn.Click += (_, _) => AddPhrase(phrase, catIdx);
        return btn;
    }

    private Grid BuildEditCell(int catIdx, int phraseIdx, string phrase, string bgHex, string fgHex)
    {
        var grid = new Grid
        {
            Background = new SolidColorBrush(ParseColor(bgHex)),
            CornerRadius = new CornerRadius(4), Margin = new Thickness(3),
        };
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });

        var toolbar = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Spacing = 4, Padding = new Thickness(4, 4, 4, 0) };

        var renameBtn = new Button
        {
            Content = "✎", FontSize = 14,
            Background = new SolidColorBrush(ParseColor("#00000040")),
            Foreground = new SolidColorBrush(ParseColor(fgHex)),
            BorderThickness = new Thickness(0), CornerRadius = new CornerRadius(3), Padding = new Thickness(6, 2, 6, 2),
        };
        renameBtn.Click += async (_, _) => await RenamePhraseAsync(catIdx, phraseIdx);

        var delBtn = new Button
        {
            Content = "✕", FontSize = 14,
            Background = new SolidColorBrush(ParseColor("#DC2626")),
            Foreground = new SolidColorBrush(Colors.White),
            BorderThickness = new Thickness(0), CornerRadius = new CornerRadius(3), Padding = new Thickness(6, 2, 6, 2),
        };
        delBtn.Click += (_, _) => DeletePhrase(catIdx, phraseIdx);
        toolbar.Children.Add(renameBtn);
        toolbar.Children.Add(delBtn);

        var label = new TextBlock
        {
            Text = phrase, FontSize = 17, FontWeight = FontWeights.Bold,
            Foreground = new SolidColorBrush(ParseColor(fgHex)),
            TextWrapping = TextWrapping.Wrap,
            VerticalAlignment = VerticalAlignment.Center,
            HorizontalAlignment = HorizontalAlignment.Center,
            TextAlignment = TextAlignment.Center, Padding = new Thickness(8),
        };

        Grid.SetRow(toolbar, 0);
        Grid.SetRow(label, 1);
        grid.Children.Add(toolbar);
        grid.Children.Add(label);
        return grid;
    }

    // ── Phrase actions ────────────────────────────────────────────────────────
    private void AddPhrase(string phrase, int catIdx)
    {
        _history.Add(_sentenceBox.Text);
        if (_history.Count > 200) _history.RemoveAt(0);

        var cur = _sentenceBox.Text;
        _sentenceBox.Text = cur.Length > 0 && !cur.EndsWith(' ')
            ? cur + " " + phrase
            : cur + phrase;
        _sentenceBox.SelectionStart = _sentenceBox.Text.Length;

        var key = DataService.UsageKey(_phrases.Categories[catIdx].Name, phrase);
        _usage.Counts.TryGetValue(key, out int c);
        _usage.Counts[key] = c + 1;

        UpdateSuggestions(catIdx);
        _mobile?.UpdateText(_sentenceBox.Text);
    }

    private void UpdateSuggestions(int activeCatIdx)
    {
        _suggestionsPanel.Children.Clear();
        var list = new List<(string phrase, int catIdx, int count)>();

        for (int ci = 0; ci < _phrases.Categories.Count; ci++)
        {
            if (ci == activeCatIdx) continue;
            var cat = _phrases.Categories[ci];
            foreach (var p in cat.Phrases)
            {
                var key = DataService.UsageKey(cat.Name, p);
                if (_usage.Counts.TryGetValue(key, out int cnt) && cnt > 0)
                    list.Add((p, ci, cnt));
            }
        }
        list.Sort((a, b) => b.count.CompareTo(a.count));

        foreach (var (phrase, ci, _) in list.Take(8))
        {
            var btn = new Button
            {
                Content = phrase, FontSize = 13,
                Background = new SolidColorBrush(ParseColor("#DBEAFE")),
                Foreground = new SolidColorBrush(ParseColor("#1E40AF")),
                BorderBrush = new SolidColorBrush(ParseColor("#93C5FD")),
                BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(20),
                Padding = new Thickness(14, 6, 14, 6),
            };
            var p2 = phrase; var ci2 = ci;
            btn.Click += (_, _) => AddPhrase(p2, ci2);
            _suggestionsPanel.Children.Add(btn);
        }
        _suggestionsScroll.Visibility = _suggestionsPanel.Children.Count > 0
            ? Visibility.Visible : Visibility.Collapsed;
    }

    // ── Edit mode ─────────────────────────────────────────────────────────────
    private void EditPhrasesBtn_Click(object s, RoutedEventArgs e)
    {
        _editMode = !_editMode;
        _editPhrasesBtn.Background = _editMode
            ? new SolidColorBrush(ParseColor("#1D4ED8"))
            : new SolidColorBrush(Colors.Transparent);
        BuildPhraseGrid(_activeTab);
        _statusText.Text = _editMode ? "Edit mode — ✎ to rename, ✕ to delete" : "Ready";
    }

    private async Task RenamePhraseAsync(int catIdx, int phraseIdx)
    {
        var cur = _phrases.Categories[catIdx].Phrases[phraseIdx];
        var tb  = new TextBox { Text = cur, SelectionStart = cur.Length };
        var dlg = new ContentDialog
        {
            Title = "Rename Phrase", Content = tb,
            PrimaryButtonText = "Save", CloseButtonText = "Cancel",
            DefaultButton = ContentDialogButton.Primary, XamlRoot = Content.XamlRoot,
        };
        if (await dlg.ShowAsync() == ContentDialogResult.Primary)
        {
            var txt = tb.Text.Trim();
            if (!string.IsNullOrEmpty(txt))
            {
                _phrases.Categories[catIdx].Phrases[phraseIdx] = txt;
                DataService.SavePhrases(_phrases);
                BuildPhraseGrid(catIdx);
            }
        }
    }

    private void DeletePhrase(int catIdx, int phraseIdx)
    {
        _phrases.Categories[catIdx].Phrases.RemoveAt(phraseIdx);
        DataService.SavePhrases(_phrases);
        BuildPhraseGrid(catIdx);
    }

    private async Task AddNewPhraseAsync(int catIdx)
    {
        var tb = new TextBox { PlaceholderText = "Enter phrase text…" };
        var dlg = new ContentDialog
        {
            Title = "New Phrase", Content = tb,
            PrimaryButtonText = "Add", CloseButtonText = "Cancel",
            DefaultButton = ContentDialogButton.Primary, XamlRoot = Content.XamlRoot,
        };
        if (await dlg.ShowAsync() == ContentDialogResult.Primary)
        {
            var txt = tb.Text.Trim();
            if (!string.IsNullOrEmpty(txt))
            {
                _phrases.Categories[catIdx].Phrases.Add(txt);
                DataService.SavePhrases(_phrases);
                BuildPhraseGrid(catIdx);
            }
        }
    }

    // ── Action bar handlers ───────────────────────────────────────────────────
    private void ClearBtn_Click(object s, RoutedEventArgs e)
    {
        _history.Add(_sentenceBox.Text);
        _sentenceBox.Text = "";
        _mobile?.UpdateText("");
    }

    private void UndoBtn_Click(object s, RoutedEventArgs e)
    {
        if (_history.Count == 0) return;
        _sentenceBox.Text = _history[^1];
        _history.RemoveAt(_history.Count - 1);
        _mobile?.UpdateText(_sentenceBox.Text);
    }

    private async void CleanBtn_Click(object s, RoutedEventArgs e)
    {
        var text = _sentenceBox.Text.Trim();
        if (string.IsNullOrEmpty(text)) return;

        if (string.IsNullOrEmpty(_settings.GroqApiKey))
        {
            await ShowApiKeyDialogAsync();
            if (string.IsNullOrEmpty(_settings.GroqApiKey)) return;
        }

        _cleanBtn.IsEnabled = false;
        _cleanBtnText.Text  = "Cleaning…";
        _statusText.Text    = "Sending to Groq AI…";

        try
        {
            var improved = await _groq.CleanAsync(text, _settings.GroqApiKey);
            _history.Clear();
            _sentenceBox.Text = improved;
            _mobile?.UpdateText(improved);
            _statusText.Text = "Sentence cleaned by Groq AI";
        }
        catch (Exception ex)
        {
            _statusText.Text = $"Clean failed — {ex.Message[..Math.Min(80, ex.Message.Length)]}";
        }
        finally
        {
            _cleanBtn.IsEnabled = true;
            _cleanBtnText.Text  = "Clean";
        }
    }

    private async void GoBtn_Click(object s, RoutedEventArgs e)
    {
        var text = _sentenceBox.Text;
        if (string.IsNullOrEmpty(text)) return;

        var dp = new DataPackage();
        dp.SetText(text);
        Clipboard.SetContent(dp);

        if (AppWindow.Presenter is OverlappedPresenter pres) pres.Minimize();

        await Task.Delay((int)(_settings.Delay * 1000));

        SendKey(VK_CONTROL, false); SendKey(VK_V, false);
        SendKey(VK_V, true);        SendKey(VK_CONTROL, true);

        if (_settings.ClearAfterGo)
        {
            _sentenceBox.Text = "";
            _mobile?.UpdateText("");
        }
        _statusText.Text = $"Pasted: {text[..Math.Min(60, text.Length)]}{(text.Length > 60 ? "…" : "")}";
    }

    private static void SendKey(byte vk, bool keyUp)
    {
        var inp = new INPUT
        {
            type = INPUT_KEYBOARD,
            u = new UNION { ki = new KEYBDINPUT { wVk = vk, dwFlags = keyUp ? KEYEVENTF_KEYUP : 0 } }
        };
        SendInput(1, new[] { inp }, Marshal.SizeOf<INPUT>());
    }

    // ── Settings ──────────────────────────────────────────────────────────────
    private async void SettingsBtn_Click(object s, RoutedEventArgs e)
    {
        var panel = new StackPanel { Spacing = 12, Width = 380 };

        panel.Children.Add(Bold("Paste Delay (seconds)"));
        var delayBox = new NumberBox { Value = _settings.Delay, Minimum = 0, Maximum = 10, SmallChange = 0.5 };
        panel.Children.Add(delayBox);

        panel.Children.Add(Bold("Phrase Font Size"));
        var fontBox = new NumberBox { Value = _settings.FontSize, Minimum = 12, Maximum = 36, SmallChange = 1 };
        panel.Children.Add(fontBox);

        var clearCheck = new CheckBox { Content = "Clear sentence after GO", IsChecked = _settings.ClearAfterGo };
        panel.Children.Add(clearCheck);

        panel.Children.Add(Bold("Groq API Key"));
        var apiBox = new PasswordBox { Password = _settings.GroqApiKey, PlaceholderText = "gsk_…" };
        panel.Children.Add(apiBox);

        var dlg = new ContentDialog
        {
            Title = "Settings", Content = panel,
            PrimaryButtonText = "Save", CloseButtonText = "Cancel",
            DefaultButton = ContentDialogButton.Primary, XamlRoot = Content.XamlRoot,
        };
        if (await dlg.ShowAsync() == ContentDialogResult.Primary)
        {
            _settings.Delay        = delayBox.Value;
            _settings.FontSize     = (int)fontBox.Value;
            _settings.ClearAfterGo = clearCheck.IsChecked == true;
            _settings.GroqApiKey   = apiBox.Password;
            DataService.SaveSettings(_settings);
            BuildPhraseGrid(_activeTab);
        }
    }

    private async Task ShowApiKeyDialogAsync()
    {
        var box = new PasswordBox { PlaceholderText = "gsk_…", Width = 340 };
        var dlg = new ContentDialog
        {
            Title = "Groq API Key Required",
            Content = new StackPanel { Spacing = 8, Children =
            {
                new TextBlock { Text = "Enter your Groq API key to use the Clean feature.", TextWrapping = TextWrapping.Wrap },
                box,
            }},
            PrimaryButtonText = "Save", CloseButtonText = "Cancel",
            DefaultButton = ContentDialogButton.Primary, XamlRoot = Content.XamlRoot,
        };
        if (await dlg.ShowAsync() == ContentDialogResult.Primary)
        {
            _settings.GroqApiKey = box.Password;
            DataService.SaveSettings(_settings);
        }
    }

    private void FieldModeBtn_Click(object s, RoutedEventArgs e)
    {
        _settings.DarkMode = !_settings.DarkMode;
        ApplyTheme(); // rebuilds tab strip + phrase grid, updates backgrounds
        DataService.SaveSettings(_settings);
    }

    // ── Mobile server ─────────────────────────────────────────────────────────
    private async void MobileBtn_Click(object s, RoutedEventArgs e)
    {
        if (_mobile is null)
        {
            try
            {
                _mobile = new MobileServerService();
                _mobile.TextChanged += text => DispatcherQueue.TryEnqueue(() => _sentenceBox.Text = text);
                _mobile.GoTriggered += () => DispatcherQueue.TryEnqueue(() => GoBtn_Click(this, new RoutedEventArgs()));
            }
            catch (Exception ex) { await ShowSimpleDialog("Mobile Server Error", ex.Message); return; }
        }

        var localUrl = $"http://{GetLocalIp()}:{_mobile.Port}/";
        var root = new StackPanel { Spacing = 14, Width = 340 };

        // ── Local WiFi ────────────────────────────────────────────────────────
        root.Children.Add(MobileLabel("LOCAL WIFI"));
        root.Children.Add(new TextBlock { Text = localUrl, FontSize = 14, IsTextSelectionEnabled = true, TextWrapping = TextWrapping.Wrap });
        root.Children.Add(new TextBlock { Text = "Same network as the Toughbook.", FontSize = 12, Foreground = new SolidColorBrush(ParseColor("#64748B")) });

        var localQrSlot = new Border { HorizontalAlignment = HorizontalAlignment.Center };
        root.Children.Add(localQrSlot);
        _ = GenerateQrImageAsync(localUrl).ContinueWith(
            t => DispatcherQueue.TryEnqueue(() => localQrSlot.Child = t.Result),
            TaskScheduler.Default);

        // ── Divider ───────────────────────────────────────────────────────────
        root.Children.Add(new Border { Height = 1, Background = new SolidColorBrush(ParseColor("#CBD5E1")), Margin = new Thickness(0, 4, 0, 4) });

        // ── Cloudflare Tunnel ─────────────────────────────────────────────────
        root.Children.Add(MobileLabel("CLOUDFLARE TUNNEL"));
        root.Children.Add(new TextBlock { Text = "Access from any network — no WiFi required.", FontSize = 12, Foreground = new SolidColorBrush(ParseColor("#64748B")), TextWrapping = TextWrapping.Wrap });

        var tunnelContainer = new StackPanel { Spacing = 10 };
        root.Children.Add(tunnelContainer);

        if (_tunnel?.TunnelUrl is string existingUrl)
            ShowTunnelActive(tunnelContainer, existingUrl);
        else
            ShowTunnelStopped(tunnelContainer);

        await new ContentDialog
        {
            Title = "Mobile Input",
            Content = new ScrollViewer { Content = root, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, MaxHeight = 600 },
            CloseButtonText = "Close",
            XamlRoot = Content.XamlRoot,
        }.ShowAsync();
    }

    private void ShowTunnelStopped(StackPanel container)
    {
        container.Children.Clear();
        var btn = new Button
        {
            Content = "Start Cloudflare Tunnel",
            Height = 44, HorizontalAlignment = HorizontalAlignment.Stretch,
            Background = new SolidColorBrush(ParseColor("#F97316")),
            Foreground = new SolidColorBrush(Colors.White),
            BorderThickness = new Thickness(0), CornerRadius = new CornerRadius(6),
            FontWeight = FontWeights.SemiBold, FontSize = 15,
        };
        btn.Click += async (_, _) => await StartTunnelAsync(container);
        container.Children.Add(btn);
    }

    private void ShowTunnelActive(StackPanel container, string url)
    {
        container.Children.Clear();
        container.Children.Add(new TextBlock
        {
            Text = url, FontSize = 13, IsTextSelectionEnabled = true,
            TextWrapping = TextWrapping.Wrap,
            Foreground = new SolidColorBrush(ParseColor("#059669")),
        });

        var qrSlot = new Border { HorizontalAlignment = HorizontalAlignment.Center };
        container.Children.Add(qrSlot);
        _ = GenerateQrImageAsync(url).ContinueWith(
            t => DispatcherQueue.TryEnqueue(() => qrSlot.Child = t.Result),
            TaskScheduler.Default);

        var stopBtn = new Button
        {
            Content = "Stop Tunnel", Height = 40,
            HorizontalAlignment = HorizontalAlignment.Stretch,
            CornerRadius = new CornerRadius(6), FontWeight = FontWeights.SemiBold,
        };
        stopBtn.Click += (_, _) =>
        {
            _tunnel?.Dispose();
            _tunnel = null;
            ShowTunnelStopped(container);
        };
        container.Children.Add(stopBtn);
    }

    private async Task StartTunnelAsync(StackPanel container)
    {
        container.Children.Clear();
        var status = new TextBlock { FontSize = 13, Foreground = new SolidColorBrush(ParseColor("#64748B")), TextWrapping = TextWrapping.Wrap };
        container.Children.Add(status);

        try
        {
            _tunnel ??= new TunnelService(_mobile!.Port);

            status.Text = File.Exists(TunnelService.ExePath)
                ? "Starting tunnel…"
                : "Downloading cloudflared (one-time, ~30 MB)…";

            await _tunnel.EnsureDownloadedAsync();
            status.Text = "Waiting for tunnel URL…";

            var tcs = new TaskCompletionSource<string>();
            _tunnel.UrlReady += url => tcs.TrySetResult(url);
            _tunnel.Start();

            var tunnelUrl = await tcs.Task.WaitAsync(TimeSpan.FromSeconds(30));
            ShowTunnelActive(container, tunnelUrl);
        }
        catch (TimeoutException)
        {
            status.Text = "Timed out waiting for tunnel URL.";
            var retry = new Button { Content = "Retry", Margin = new Thickness(0, 6, 0, 0) };
            retry.Click += async (_, _) => await StartTunnelAsync(container);
            container.Children.Add(retry);
        }
        catch (Exception ex)
        {
            status.Text = $"Error: {ex.Message[..Math.Min(80, ex.Message.Length)]}";
        }
    }

    private static TextBlock MobileLabel(string text) => new()
    {
        Text = text, FontSize = 11, FontWeight = FontWeights.SemiBold,
        Foreground = new SolidColorBrush(ParseColor("#64748B")),
        CharacterSpacing = 80,
    };

    private static async Task<Image> GenerateQrImageAsync(string url)
    {
        var pngBytes = await Task.Run(() =>
        {
            using var gen = new QRCodeGenerator();
            var data = gen.CreateQrCode(url, QRCodeGenerator.ECCLevel.M);
            return new PngByteQRCode(data).GetGraphic(8);
        });

        var stream = new InMemoryRandomAccessStream();
        var writer = new DataWriter(stream);
        writer.WriteBytes(pngBytes);
        await writer.StoreAsync();
        stream.Seek(0);

        var bitmap = new BitmapImage();
        await bitmap.SetSourceAsync(stream);
        return new Image { Source = bitmap, Width = 200, Height = 200 };
    }

    // ── Auto-update ────────────────────────────────────────────────────────────
    private async Task CheckForUpdateAsync()
    {
        var release = await UpdateService.CheckAsync(AppVersion);
        if (release is null) return;
        DispatcherQueue.TryEnqueue(() =>
        {
            _updateBtn.Content    = $"↑ Update to v{release.TagName}";
            _updateBtn.Tag        = release;
            _updateBtn.Visibility = Visibility.Visible;
        });
    }

    private async void UpdateBtn_Click(object s, RoutedEventArgs e)
    {
        if (_updateBtn.Tag is not ReleaseInfo release) return;
        var dlg = new ContentDialog
        {
            Title = $"Update to v{release.TagName}?",
            Content = "The app will download and restart. Unsaved changes will be lost.",
            PrimaryButtonText = "Update Now", CloseButtonText = "Later",
            XamlRoot = Content.XamlRoot,
        };
        if (await dlg.ShowAsync() == ContentDialogResult.Primary)
        {
            _statusText.Text = "Downloading update…";
            var exe = System.Diagnostics.Process.GetCurrentProcess().MainModule?.FileName ?? "";
            await UpdateService.DownloadAndReplaceAsync(release.ExeUrl, exe);
            Application.Current.Exit();
        }
    }

    // ── First-run setup ───────────────────────────────────────────────────────
    private async Task RunFirstTimeSetupAsync()
    {
        if (!await ShowTosAsync())
        {
            Application.Current.Exit();
            return;
        }
        _settings.TosAccepted = true;
        DataService.SaveSettings(_settings);

        await ShowCloudflaredSetupAsync();
    }

    private async Task<bool> ShowTosAsync()
    {
        var text = new TextBlock
        {
            Text = TosText, TextWrapping = TextWrapping.Wrap,
            FontSize = 13, LineHeight = 22,
        };
        var scroll = new ScrollViewer
        {
            Content = text, MaxHeight = 420, MaxWidth = 480,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
        };
        var dlg = new ContentDialog
        {
            Title = "Terms of Use — Please Read",
            Content = scroll,
            PrimaryButtonText = "I Agree",
            CloseButtonText = "Decline",
            DefaultButton = ContentDialogButton.Primary,
            XamlRoot = Content.XamlRoot,
        };
        return await dlg.ShowAsync() == ContentDialogResult.Primary;
    }

    private async Task ShowCloudflaredSetupAsync()
    {
        if (File.Exists(TunnelService.ExePath)) return;

        var choiceDlg = new ContentDialog
        {
            Title = "Mobile Feature Setup",
            Content = new TextBlock
            {
                Text = "The Mobile Input feature uses Cloudflare Tunnel (cloudflared) to let " +
                       "your phone connect from any network — not just the Toughbook's WiFi.\n\n" +
                       "Would you like to download cloudflared now? (~30 MB, one-time only)",
                TextWrapping = TextWrapping.Wrap, FontSize = 14, LineHeight = 22, MaxWidth = 400,
            },
            PrimaryButtonText = "Download Now",
            CloseButtonText = "Skip for Now",
            DefaultButton = ContentDialogButton.Primary,
            XamlRoot = Content.XamlRoot,
        };

        if (await choiceDlg.ShowAsync() != ContentDialogResult.Primary) return;

        var status = new TextBlock { Text = "Downloading cloudflared…", FontSize = 14, TextWrapping = TextWrapping.Wrap };
        var bar    = new ProgressBar { IsIndeterminate = true, Margin = new Thickness(0, 10, 0, 0) };
        var inner  = new StackPanel { Width = 400, Children = { status, bar } };

        var dlg = new ContentDialog
        {
            Title = "Setting Up Mobile Feature",
            Content = inner,
            CloseButtonText = "Cancel",
            XamlRoot = Content.XamlRoot,
        };

        _ = Task.Run(async () =>
        {
            try
            {
                await new TunnelService(0).EnsureDownloadedAsync();
                DispatcherQueue.TryEnqueue(() =>
                {
                    status.Text = "Cloudflared is ready. Mobile tunnels will work instantly.";
                    bar.IsIndeterminate = false;
                    bar.Value = 100;
                });
                await Task.Delay(1500);
                DispatcherQueue.TryEnqueue(dlg.Hide);
            }
            catch (Exception ex)
            {
                DispatcherQueue.TryEnqueue(() =>
                {
                    status.Text = $"Download failed: {ex.Message[..Math.Min(70, ex.Message.Length)]}\n\nYou can retry via the Mobile button later.";
                    bar.Visibility = Visibility.Collapsed;
                });
            }
        });

        await dlg.ShowAsync();
    }

    private const string TosText =
        "SURVEY SENTENCE GENERATOR — TERMS OF USE\n\n" +

        "1. ACCEPTABLE USE\n" +
        "This application is provided for professional survey and field data collection. " +
        "You agree to use it only for lawful purposes and in accordance with your organisation's policies.\n\n" +

        "2. LOCAL DATA\n" +
        "All phrase data and settings are stored locally on this device. No data is sent to external " +
        "servers except when using the optional Groq AI or Cloudflare Tunnel features, which require " +
        "an internet connection.\n\n" +

        "3. CLOUDFLARE TUNNEL (OPTIONAL)\n" +
        "The Mobile Input feature optionally downloads and runs cloudflared, a third-party binary " +
        "published by Cloudflare, Inc. Use is subject to Cloudflare's Terms of Service " +
        "(cloudflare.com/terms). The binary is sourced from Cloudflare's official GitHub releases.\n\n" +

        "4. GROQ AI (OPTIONAL)\n" +
        "The Clean feature sends your sentence to the Groq API for rephrasing. You must supply " +
        "your own API key. Use is subject to Groq's Terms of Service. Your key is stored only on " +
        "this device.\n\n" +

        "5. AUTO-UPDATE\n" +
        "Updates are downloaded from the official GitHub releases page. By accepting an update you " +
        "acknowledge that application files will be replaced.\n\n" +

        "6. NO WARRANTY\n" +
        "This application is provided \"as is\" without warranty of any kind. The developers accept " +
        "no liability for loss of data or damages arising from its use.\n\n" +

        "© 2026 Survey Sentence Generator. All rights reserved.";

    // ── Helpers ───────────────────────────────────────────────────────────────
    private (string LB, string LF, string AB, string AF) GetCatColor(int catIdx)
    {
        var cat = _phrases.Categories[catIdx];
        int idx = cat.ColorIdx >= 0 ? cat.ColorIdx % CatColors.Length : catIdx % CatColors.Length;
        return CatColors[idx];
    }

    private static Color ParseColor(string hex)
    {
        hex = hex.TrimStart('#');
        return hex.Length switch
        {
            6 => Color.FromArgb(255,
                     Convert.ToByte(hex[..2], 16),
                     Convert.ToByte(hex[2..4], 16),
                     Convert.ToByte(hex[4..6], 16)),
            8 => Color.FromArgb(
                     Convert.ToByte(hex[..2], 16),
                     Convert.ToByte(hex[2..4], 16),
                     Convert.ToByte(hex[4..6], 16),
                     Convert.ToByte(hex[6..8], 16)),
            _ => Colors.Black,
        };
    }

    private static string GetLocalIp()
    {
        try
        {
            using var sock = new System.Net.Sockets.Socket(
                System.Net.Sockets.AddressFamily.InterNetwork,
                System.Net.Sockets.SocketType.Dgram, 0);
            sock.Connect("8.8.8.8", 80);
            return ((System.Net.IPEndPoint)sock.LocalEndPoint!).Address.ToString();
        }
        catch { return "127.0.0.1"; }
    }

    private static TextBlock Bold(string text) => new()
    {
        Text = text, FontWeight = FontWeights.SemiBold,
    };

    private async Task ShowSimpleDialog(string title, string msg) =>
        await new ContentDialog { Title = title, Content = msg, CloseButtonText = "OK", XamlRoot = Content.XamlRoot }.ShowAsync();
}
