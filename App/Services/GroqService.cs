using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace SurveySentenceGenerator.Services;

public class GroqService
{
    private const string BaseUrl = "https://api.groq.com/openai/v1/chat/completions";
    private const string Model   = "llama-3.3-70b-versatile";

    private const string SystemPrompt =
        "You are an expert arborist and tree surveyor writing formal BS 5837 tree survey reports in the UK.\n\n" +
        "Rewrite the user's draft survey note into polished, professional arboricultural report language.\n\n" +
        "Rules:\n" +
        "- Preserve ALL technical observations, dimensions, species names, and measurements exactly as given.\n" +
        "- Use professional arboricultural terminology and BS 5837 conventions where appropriate.\n" +
        "- Write in third person, past tense (e.g. 'The tree was observed…').\n" +
        "- Be concise — one to three sentences maximum.\n" +
        "- Output ONLY the rewritten text. No preamble, no explanation, no commentary.";

    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(30) };

    public async Task<string> CleanAsync(string text, string apiKey)
    {
        _http.DefaultRequestHeaders.Authorization =
            new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", apiKey);

        var body = new
        {
            model = Model,
            max_tokens = 512,
            messages = new[]
            {
                new { role = "system", content = SystemPrompt },
                new { role = "user",   content = text },
            }
        };

        using var resp = await _http.PostAsJsonAsync(BaseUrl, body);
        resp.EnsureSuccessStatusCode();

        var json = await resp.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(json);
        return doc.RootElement
                  .GetProperty("choices")[0]
                  .GetProperty("message")
                  .GetProperty("content")
                  .GetString() ?? text;
    }
}
