using System.Text.Json.Serialization;

namespace SurveySentenceGenerator.Models;

public class Category
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("phrases")]
    public List<string> Phrases { get; set; } = new();

    [JsonPropertyName("cols")]
    public int Cols { get; set; } = 3;

    [JsonPropertyName("color_idx")]
    public int ColorIdx { get; set; } = -1;
}

public class PhrasesData
{
    [JsonPropertyName("categories")]
    public List<Category> Categories { get; set; } = new();
}

public class AppSettings
{
    [JsonPropertyName("delay")]
    public double Delay { get; set; } = 1.0;

    [JsonPropertyName("clear_after_go")]
    public bool ClearAfterGo { get; set; } = true;

    [JsonPropertyName("font_size")]
    public int FontSize { get; set; } = 20;

    [JsonPropertyName("dark_mode")]
    public bool DarkMode { get; set; } = false;

    [JsonPropertyName("window_width")]
    public double WindowWidth { get; set; } = 1280;

    [JsonPropertyName("window_height")]
    public double WindowHeight { get; set; } = 900;

    [JsonPropertyName("groq_api_key")]
    public string GroqApiKey { get; set; } = "";
}

// Each (category|phrase) pair maps to its usage count
public class UsageData
{
    [JsonPropertyName("counts")]
    public Dictionary<string, int> Counts { get; set; } = new();
}
