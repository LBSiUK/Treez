# Build Instructions

## Prerequisites

Install once:

```powershell
# 1. .NET 8 SDK
winget install Microsoft.DotNet.SDK.8

# 2. Windows App SDK runtime (needed to run unpackaged builds)
winget install Microsoft.WindowsAppRuntimeInstaller
```

Restart your terminal after installing.

## Run in development

```powershell
cd C:\Users\leonb\Treez\App
dotnet run
```

## Publish as single .exe

```powershell
cd C:\Users\leonb\Treez\App
dotnet publish -c Release -r win-x64 --self-contained -o ..\dist\
```

The output exe will be at `C:\Users\leonb\Treez\dist\SurveySentenceGenerator.exe`.

## Data location

All user data (phrases, settings, usage stats) is stored in:
`%APPDATA%\SurveySentenceGenerator\`

This is the **same location** as the Python version, so all your existing phrases carry over automatically.
