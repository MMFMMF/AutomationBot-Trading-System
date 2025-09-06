Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Clear any cached display
[System.GC]::Collect()

# Kill any background processes that might interfere
Get-Process -Name "msedge*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Wait for system cleanup
Start-Sleep -Seconds 2

# Open browser with specific parameters for static HTML
$htmlPath = "C:\Users\Kamyar Shah\Documents\AutomationBot\dashboard_static.html"
Start-Process -FilePath "msedge.exe" -ArgumentList "--new-window", "--start-maximized", "--disable-web-security", "--disable-features=VizDisplayCompositor", "file:///$htmlPath"

# Wait for complete page load
Start-Sleep -Seconds 6

# Take screenshot at exact moment
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$screenshot = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($screenshot)
$graphics.CopyFromScreen($screen.X, $screen.Y, 0, 0, $screenshot.Size)
$screenshot.Save("C:\Users\Kamyar Shah\Documents\AutomationBot\forensic_dashboard_proof.png")
$graphics.Dispose()
$screenshot.Dispose()

Write-Output "FORENSIC SCREENSHOT CAPTURED"