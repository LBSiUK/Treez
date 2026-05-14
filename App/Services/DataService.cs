using System.Text.Json;
using SurveySentenceGenerator.Models;

namespace SurveySentenceGenerator.Services;

public static class DataService
{
    public static readonly string AppDataDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "SurveySentenceGenerator");

    private static readonly string PhrasesFile  = Path.Combine(AppDataDir, "phrases.json");
    private static readonly string SettingsFile = Path.Combine(AppDataDir, "settings.json");
    private static readonly string UsageFile    = Path.Combine(AppDataDir, "usage.json");

    private static readonly JsonSerializerOptions JsonOpts = new() { WriteIndented = true };

    static DataService() => Directory.CreateDirectory(AppDataDir);

    // ── Phrases ────────────────────────────────────────────────────────────────

    public static PhrasesData LoadPhrases()
    {
        if (!File.Exists(PhrasesFile)) return DefaultPhrases();
        try
        {
            var json = File.ReadAllText(PhrasesFile);
            return JsonSerializer.Deserialize<PhrasesData>(json) ?? DefaultPhrases();
        }
        catch { return DefaultPhrases(); }
    }

    public static void SavePhrases(PhrasesData data)
    {
        File.WriteAllText(PhrasesFile, JsonSerializer.Serialize(data, JsonOpts));
    }

    // ── Settings ───────────────────────────────────────────────────────────────

    public static AppSettings LoadSettings()
    {
        if (!File.Exists(SettingsFile)) return new AppSettings();
        try
        {
            var json = File.ReadAllText(SettingsFile);
            return JsonSerializer.Deserialize<AppSettings>(json) ?? new AppSettings();
        }
        catch { return new AppSettings(); }
    }

    public static void SaveSettings(AppSettings s)
    {
        File.WriteAllText(SettingsFile, JsonSerializer.Serialize(s, JsonOpts));
    }

    // ── Usage ──────────────────────────────────────────────────────────────────

    public static UsageData LoadUsage()
    {
        if (!File.Exists(UsageFile)) return new UsageData();
        try
        {
            var json = File.ReadAllText(UsageFile);
            return JsonSerializer.Deserialize<UsageData>(json) ?? new UsageData();
        }
        catch { return new UsageData(); }
    }

    public static void SaveUsage(UsageData u)
    {
        File.WriteAllText(UsageFile, JsonSerializer.Serialize(u, JsonOpts));
    }

    public static string UsageKey(string category, string phrase) => $"{category}|{phrase}";

    // ── Defaults ───────────────────────────────────────────────────────────────

    public static PhrasesData DefaultPhrases() => new()
    {
        Categories = new List<Category>
        {
            new() { Name = "Numbers", Cols = 5,
                Phrases = new() { "0","1","2","3","4","5","6","7","8","9" } },
            new() { Name = "Observations", Cols = 3,
                Phrases = new()
                {
                    "No significant features have been observed.",
                    "Vegetation obscuring observations of the stem and base.",
                    "Vegetation obscuring observations of the stems and bases.",
                    "Dimensions recorded are the largest represented within the group.",
                    "Ivy concealing observations of the stem and base.",
                    "Further investigation required to confirm structural integrity.",
                    "Observations of the base limited by dense ground vegetation.",
                } },
            new() { Name = "Crown", Cols = 3,
                Phrases = new()
                {
                    "Crown height has been raised to its current dimensions.",
                    "Crown height has been pruned to its current dimensions.",
                    "Historically pruned to raise the crown height to its current dimensions.",
                    "Pruned to raise the crown height to its current dimensions.",
                    "Dead wood in the crown up to 100mm diameter x 5m length.",
                    "Dead wood in the crown up to 150mm diameter x 5m length.",
                    "Dead wood in the crown up to 400mm diameter x 10m length.",
                    "Die back of the crown density by approximately 20%.",
                    "Up to 2m length die back centrally to the upper crown.",
                    "Crown height over the track has been raised to 5m from ground level.",
                    "Crown presents approximately 30% of expected crown density.",
                    "Asymmetrical crown shape due to presence of partner trees.",
                } },
            new() { Name = "Condition", Cols = 3,
                Phrases = new()
                {
                    "Dead tree.",
                    "Tree in decline.",
                    "Single tree densely clad with ivy.",
                    "Ivy clad dead monolith stem.",
                    "Approximately 10% of the crown has been colonised with mistletoe.",
                    "Diminished leaf size and foliage density. Tree in decline.",
                    "Multiple stem bleeds from the base up to 2m from ground level.",
                    "Multiple ganoderma sp fungal fruit bodies at the base.",
                    "Low foliage density by approximately 50%.",
                    "Group of approximately twelve trees in varying stages of death and decline.",
                    "Areas of dysfunctional bark at the base.",
                    "1m area of exposed sap wood to the stem at 2m from ground level.",
                } },
            new() { Name = "Groups", Cols = 3,
                Phrases = new()
                {
                    "Group comprising of",
                    "Mature orchard comprising of approximately",
                    "Mixed scrub and broadleaf.",
                    "Mixed woodland group comprising of",
                    "Understory shrub group comprising of",
                    "Historically pruned to maintain crown shape and form.",
                    "Scaffold bar providing support for low stem.",
                    "Fork brace fitted at 6m from ground level.",
                    "Low branch in contact with adjacent built structure.",
                    "Crown height raised over roadside.",
                    "Grape vine is colonising the crown.",
                } },
            new() { Name = "Species", Cols = 3,
                Phrases = new()
                {
                    "Sycamore","Ash","Field maple","Hazel","Hawthorn",
                    "Silver birch","Wild cherry","Hornbeam","Yew","Elm",
                    "Common walnut","Goat willow","Aspen","Magnolia sp",
                    "Malus sp","Prunus sp","Norway maple","Leyland cypress",
                    "Common pear","Judas tree","Snake bark maple","Japanese maple",
                    "Indian bean tree","Cockspur hawthorn","Himalayan birch",
                    "Sweet bay","Turkey oak","Pink hawthorn","Mountain ash",
                    "Dog wood","Cherry laurel","Viburnum sp","Red hazel",
                    "Lilac","Hebe sp","Loquat",
                } },
        }
    };
}
