Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Wait for browser to fully load the static HTML
Start-Sleep -Seconds 4

# Take screenshot of the entire screen
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$screenshot = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($screenshot)
$graphics.CopyFromScreen($screen.X, $screen.Y, 0, 0, $screenshot.Size)
$screenshot.Save("C:\Users\Kamyar Shah\Documents\AutomationBot\final_dashboard_verification.png")
$graphics.Dispose()
$screenshot.Dispose()

Write-Host "Final verification screenshot saved!"