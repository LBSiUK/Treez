using System.Net;
using System.Text;
using System.Text.Json;

namespace SurveySentenceGenerator.Services;

public class MobileServerService : IDisposable
{
    public int Port { get; }

    // Shared state between server and UI
    private string _text = "";
    private int    _version = 0;
    private readonly object _lock = new();

    public event Action<string>? TextChanged;
    public event Action?         GoTriggered;

    private readonly HttpListener _listener = new();
    private readonly CancellationTokenSource _cts = new();

    public MobileServerService()
    {
        Port = 8765;
        _listener.Prefixes.Add($"http://+:{Port}/");
        StartListener();
        Task.Run(ServeLoop, _cts.Token);
    }

    private void StartListener()
    {
        try
        {
            _listener.Start();
        }
        catch (System.Net.HttpListenerException ex) when (ex.ErrorCode == 5)
        {
            // Access denied — register the URL ACL once (one-time UAC prompt)
            var psi = new System.Diagnostics.ProcessStartInfo
            {
                FileName = "netsh",
                Arguments = $"http add urlacl url=http://+:{Port}/ user=Everyone",
                Verb = "runas",
                UseShellExecute = true,
                CreateNoWindow = true,
            };
            var proc = System.Diagnostics.Process.Start(psi);
            proc?.WaitForExit();
            _listener.Start();
        }
    }

    public void UpdateText(string text)
    {
        lock (_lock) { _text = text; _version++; }
    }

    private async Task ServeLoop()
    {
        while (!_cts.Token.IsCancellationRequested)
        {
            try
            {
                var ctx = await _listener.GetContextAsync();
                _ = Task.Run(() => HandleRequest(ctx), _cts.Token);
            }
            catch (ObjectDisposedException) { break; }
            catch { }
        }
    }

    private void HandleRequest(HttpListenerContext ctx)
    {
        var req  = ctx.Request;
        var resp = ctx.Response;

        try
        {
            resp.AddHeader("Access-Control-Allow-Origin", "*");

            if (req.HttpMethod == "GET" && req.Url?.AbsolutePath == "/")
            {
                var html = Encoding.UTF8.GetBytes(MobileHtml);
                resp.ContentType = "text/html; charset=utf-8";
                resp.ContentLength64 = html.Length;
                resp.OutputStream.Write(html);
            }
            else if (req.HttpMethod == "GET" && req.Url?.AbsolutePath == "/state")
            {
                string text; int ver;
                lock (_lock) { text = _text; ver = _version; }
                var json = JsonSerializer.Serialize(new { text, version = ver });
                var bytes = Encoding.UTF8.GetBytes(json);
                resp.ContentType = "application/json";
                resp.ContentLength64 = bytes.Length;
                resp.OutputStream.Write(bytes);
            }
            else if (req.HttpMethod == "POST" && req.Url?.AbsolutePath == "/update")
            {
                using var reader = new StreamReader(req.InputStream, Encoding.UTF8);
                var body = reader.ReadToEnd();
                using var doc = JsonDocument.Parse(body);
                var incoming = doc.RootElement.GetProperty("text").GetString() ?? "";
                int ver;
                lock (_lock) { _text = incoming; ver = ++_version; }
                TextChanged?.Invoke(incoming);
                var json = JsonSerializer.Serialize(new { version = ver });
                var bytes = Encoding.UTF8.GetBytes(json);
                resp.ContentType = "application/json";
                resp.ContentLength64 = bytes.Length;
                resp.OutputStream.Write(bytes);
            }
            else if (req.HttpMethod == "POST" && req.Url?.AbsolutePath == "/go")
            {
                GoTriggered?.Invoke();
                resp.StatusCode = 204;
            }
            else
            {
                resp.StatusCode = 404;
            }
        }
        catch { }
        finally
        {
            try { resp.OutputStream.Close(); } catch { }
        }
    }

    public void Dispose()
    {
        _cts.Cancel();
        _listener.Stop();
        _listener.Close();
    }


    private const string MobileHtml = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
        <title>Survey Input</title>
        <style>
        *{box-sizing:border-box;margin:0;padding:0}
        html,body{height:100%;overflow:hidden}
        body{display:flex;flex-direction:column;background:#0D1117;color:#E6EDF3;
             font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
        #hdr{background:#161B22;border-bottom:1px solid #30363D;padding:12px 16px;
             display:flex;align-items:center;gap:10px;flex-shrink:0}
        #dot{width:9px;height:9px;border-radius:50%;background:#f85149;transition:background .3s;flex-shrink:0}
        #dot.on{background:#3fb950}
        #hdr h1{font-size:16px;font-weight:600;flex:1}
        #sync{font-size:12px;color:#8B949E;white-space:nowrap}
        #ta{flex:1;background:#0D1117;color:#E6EDF3;border:none;outline:none;
            resize:none;padding:16px;font-size:19px;line-height:1.6;width:100%}
        #ftr{background:#161B22;border-top:1px solid #30363D;padding:10px 14px;
             display:flex;gap:10px;flex-shrink:0}
        .btn{flex:1;padding:15px;font-size:17px;font-weight:700;border:none;
             border-radius:8px;cursor:pointer}
        #bGo{background:#238636;color:#fff}
        #bClear{background:#21262D;color:#E6EDF3;flex:0 0 90px}
        </style>
        </head>
        <body>
        <div id="hdr">
          <div id="dot"></div>
          <h1>Survey Input</h1>
          <span id="sync">connecting…</span>
        </div>
        <textarea id="ta" autocomplete="off" autocorrect="off"
          autocapitalize="off" spellcheck="false"
          placeholder="Tap to type…"></textarea>
        <div id="ftr">
          <button class="btn" id="bClear" onclick="doClear()">Clear</button>
          <button class="btn" id="bGo"    onclick="doGo()">GO ›</button>
        </div>
        <script>
        var ta=document.getElementById('ta'),dot=document.getElementById('dot'),sync=document.getElementById('sync');
        var ver=0,typing=false,timer;
        ta.addEventListener('input',function(){
          typing=true;clearTimeout(timer);
          timer=setTimeout(function(){typing=false;push();},700);
        });
        function push(){
          fetch('/update',{method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({text:ta.value})})
          .then(r=>r.json()).then(d=>{ver=d.version;dot.className='on';sync.textContent='synced';})
          .catch(()=>{dot.className='';sync.textContent='offline';});
        }
        function poll(){
          if(typing){setTimeout(poll,600);return;}
          fetch('/state?v='+ver)
          .then(r=>r.json()).then(d=>{
            dot.className='on';
            if(d.version!==ver){ver=d.version;ta.value=d.text;sync.textContent='updated';}
            else{sync.textContent='live';}
            setTimeout(poll,600);
          })
          .catch(()=>{dot.className='';sync.textContent='reconnecting…';setTimeout(poll,2000);});
        }
        function doClear(){ta.value='';push();}
        function doGo(){push();fetch('/go',{method:'POST'});}
        poll();
        </script>
        </body>
        </html>
        """;
}
