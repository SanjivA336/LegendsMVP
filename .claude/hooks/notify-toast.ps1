param(
    [string]$Title = "Claude Code",
    [string]$DefaultMessage = "Claude is waiting for your response"
)

$ErrorActionPreference = 'SilentlyContinue'

try {
    $message = $DefaultMessage
    $raw = [Console]::In.ReadToEnd()
    if ($raw) {
        try {
            $data = $raw | ConvertFrom-Json
            if ($data.message) { $message = $data.message }
        } catch {}
    }

    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null

    $escapedTitle = [System.Net.WebUtility]::HtmlEncode($Title)
    $escapedMessage = [System.Net.WebUtility]::HtmlEncode($message)

    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml("<toast><visual><binding template=`"ToastGeneric`"><text>$escapedTitle</text><text>$escapedMessage</text></binding></visual></toast>")
    $toast = New-Object Windows.UI.Notifications.ToastNotification $xml

    # 'Windows PowerShell' as a bare app id is not a registered AUMID, so the
    # toast is silently dropped. This CLSID-prefixed form maps an unpackaged
    # exe to its own shell identity/icon without needing a real registration.
    $AppId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show($toast)
} catch {}
