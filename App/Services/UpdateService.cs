using System.Net.Http.Json;
using System.Text.Json;

namespace SurveySentenceGenerator.Services;

public record ReleaseInfo(string TagName, string ExeUrl);

public static class UpdateService
{
    private const string Owner = "011-sam-110";
    private const string Repo  = "Treez";

    private static readonly HttpClient Http = new();

    public static async Task<ReleaseInfo?> CheckAsync(string currentVersion)
    {
        try
        {
            Http.DefaultRequestHeaders.UserAgent.ParseAdd("SurveySentenceGenerator");
            var url  = $"https://api.github.com/repos/{Owner}/{Repo}/releases/latest";
            var json = await Http.GetStringAsync(url);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            var tag  = root.GetProperty("tag_name").GetString()?.TrimStart('v') ?? "";
            if (string.IsNullOrEmpty(tag) || tag == currentVersion) return null;

            var assets = root.GetProperty("assets");
            string? exeUrl = null;
            foreach (var a in assets.EnumerateArray())
            {
                var name = a.GetProperty("name").GetString() ?? "";
                if (name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                {
                    exeUrl = a.GetProperty("browser_download_url").GetString();
                    break;
                }
            }
            return exeUrl is null ? null : new ReleaseInfo(tag, exeUrl);
        }
        catch { return null; }
    }

    public static async Task DownloadAndReplaceAsync(string exeUrl, string currentExePath)
    {
        var tmp = currentExePath + ".new";
        var bytes = await Http.GetByteArrayAsync(exeUrl);
        await File.WriteAllBytesAsync(tmp, bytes);

        // Batch file swaps the exe after this process exits
        var bat = Path.Combine(Path.GetTempPath(), "treez_update.bat");
        await File.WriteAllTextAsync(bat,
            $"@echo off\r\n" +
            $"timeout /t 2 /nobreak >nul\r\n" +
            $"move /y \"{tmp}\" \"{currentExePath}\"\r\n" +
            $"start \"\" \"{currentExePath}\"\r\n" +
            $"del \"%~f0\"\r\n");

        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
        {
            FileName = bat,
            CreateNoWindow = true,
            WindowStyle = System.Diagnostics.ProcessWindowStyle.Hidden,
        });
    }
}
