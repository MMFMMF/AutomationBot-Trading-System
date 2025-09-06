Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Wait a moment for browser to load
Start-Sleep -Seconds 3

# Get the window that contains "localhost:5000"
$processes = Get-Process -Name msedge -ErrorAction SilentlyContinue
if ($processes) {
    # Bring Edge to foreground
    foreach ($process in $processes) {
        if ($process.MainWindowTitle -ne "") {
            [Microsoft.VisualBasic.Interaction]::AppActivate($process.Id)
            Start-Sleep -Milliseconds 500
            break
        }
    }
}

# Take screenshot of entire screen
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$screenshot = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($screenshot)
$graphics.CopyFromScreen($screen.X, $screen.Y, 0, 0, $screenshot.Size)
$screenshot.Save("C:\Users\Kamyar Shah\Documents\AutomationBot\dashboard_final.png")
$graphics.Dispose()
$screenshot.Dispose()

Write-Host "Screenshot saved to dashboard_final.png"