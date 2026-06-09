# Focus or launch native Chrome for Hub (http://127.0.0.1:8869/)
# Excludes browser panel instance (Skills Hub Debug / 9221)

$HubUrl = 'http://127.0.0.1:8869/'
$PanelProfileMarker = 'Skills Hub Debug'
$HubTitleHint = 'Project Manager'

function Get-ChromePath {
    $candidates = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        ${env:ProgramFiles(x86)} + '\Google\Chrome\Application\chrome.exe',
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}

function Test-IsNativeChromeProcess {
    param([string]$CommandLine)
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $false }
    if ($CommandLine -match [regex]::Escape($PanelProfileMarker)) { return $false }
    if ($CommandLine -match "--user-data-dir=" -and $CommandLine -notmatch "User Data") { return $false }
    return $true
}

function Get-NativeChromeProcesses {
    Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue |
        Where-Object { Test-IsNativeChromeProcess $_.CommandLine }
}

if (-not ([System.Management.Automation.PSTypeName]'HubChromeFocus').Type) {
    Add-Type @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class HubChromeFocus {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool AllowSetForegroundWindow(uint dwProcessId);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);

    public const int SW_RESTORE = 9;

    public static List<Tuple<IntPtr, string>> FindTitledWindows(uint[] pids) {
        var result = new List<Tuple<IntPtr, string>>();
        var pidSet = new HashSet<uint>(pids);
        EnumWindows((hWnd, lParam) => {
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            if (!pidSet.Contains(pid) || !IsWindowVisible(hWnd)) {
                return true;
            }
            int len = GetWindowTextLength(hWnd);
            if (len <= 0) {
                return true;
            }
            var sb = new StringBuilder(len + 1);
            GetWindowText(hWnd, sb, sb.Capacity);
            string title = sb.ToString();
            if (!string.IsNullOrWhiteSpace(title)) {
                result.Add(Tuple.Create(hWnd, title));
            }
            return true;
        }, IntPtr.Zero);
        return result;
    }

    public static bool FocusWindow(IntPtr hWnd, uint browserPid) {
        if (hWnd == IntPtr.Zero) {
            return false;
        }
        AllowSetForegroundWindow(browserPid);
        if (IsIconic(hWnd)) {
            ShowWindow(hWnd, SW_RESTORE);
        }
        return SetForegroundWindow(hWnd);
    }
}
'@
}

function Select-HubWindow {
    param(
        [System.Collections.Generic.List[System.Tuple[IntPtr, string]]]$Windows
    )
    if ($Windows.Count -eq 0) { return $null }
    $preferred = $Windows | Where-Object { $_.Item2 -like "*$HubTitleHint*" } | Select-Object -First 1
    if ($preferred) { return $preferred.Item1 }
    return $Windows[0].Item1
}

$chrome = Get-ChromePath
if (-not $chrome) {
    Write-Error 'Chrome not found.'
    exit 1
}

$nativeProcs = @(Get-NativeChromeProcesses)
if ($nativeProcs.Count -eq 0) {
    Start-Process -FilePath $chrome -ArgumentList $HubUrl
    exit 0
}

$pids = @($nativeProcs | ForEach-Object { [UInt32]$_.ProcessId })
$windows = [HubChromeFocus]::FindTitledWindows($pids)
$hwnd = Select-HubWindow -Windows $windows

if ($hwnd -ne $null) {
    $browserProc = $nativeProcs | Where-Object { $_.CommandLine -notmatch "--type=" } | Select-Object -First 1
    if (-not $browserProc) { $browserProc = $nativeProcs[0] }
    [void][HubChromeFocus]::FocusWindow($hwnd, [UInt32]$browserProc.ProcessId)
    exit 0
}

Start-Process -FilePath $chrome -ArgumentList $HubUrl
exit 0
