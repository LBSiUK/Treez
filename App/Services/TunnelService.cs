using System.Diagnostics;
using System.Text.RegularExpressions;

namespace SurveySentenceGenerator.Services;

public class TunnelService : IDisposable
{
    public static readonly string ExePath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "SurveySentenceGenerator", "cloudflared.exe");

    public string? TunnelUrl { get; private set; }
    public event Action<string>? UrlReady;

    private readonly int _port;
    private Process? _proc;

    public TunnelService(int port) => _port = port;

    public async Task EnsureDownloadedAsync()
    {
        if (File.Exists(ExePath)) return;
        Directory.CreateDirectory(Path.GetDirectoryName(ExePath)!);
        using var http = new HttpClient { Timeout = TimeSpan.FromMinutes(3) };
        http.DefaultRequestHeaders.Add("User-Agent", "SurveySentenceGenerator");
        var bytes = await http.GetByteArrayAsync(
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe");
        await File.WriteAllBytesAsync(ExePath, bytes);
    }

    public void Start()
    {
        _proc = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = ExePath,
                Arguments = $"tunnel --url http://localhost:{_port} --no-autoupdate",
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            }
        };
        _proc.ErrorDataReceived += (_, e) =>
        {
            if (e.Data is null || TunnelUrl is not null) return;
            var m = Regex.Match(e.Data, @"https://[a-z0-9\-]+\.trycloudflare\.com");
            if (!m.Success) return;
            TunnelUrl = m.Value;
            UrlReady?.Invoke(TunnelUrl);
        };
        _proc.Start();
        _proc.BeginErrorReadLine();
    }

    public void Dispose()
    {
        try { _proc?.Kill(entireProcessTree: true); } catch { }
        _proc?.Dispose();
    }
}
