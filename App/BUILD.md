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

From the root of your clone:

```powershell
cd App
dotnet run
```

## Publish as single .exe

```powershell
cd App
dotnet publish -c Release -r win-x64 --self-contained -o ..\dist\
```

The output exe will be at `dist\SurveySentenceGenerator.exe` in the repo root (the same name the Python build uses, so move one aside if you build both).

## Data location

All user data (phrases, settings, usage stats) is stored in:
`%APPDATA%\SurveySentenceGenerator\`

This is the **same location** as the Python version, so all your existing phrases carry over automatically.
