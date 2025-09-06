Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Wait for any processes to stabilize
Start-Sleep -Seconds 3

# Take screenshot immediately
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$screenshot = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($screenshot)
$graphics.CopyFromScreen($screen.X, $screen.Y, 0, 0, $screenshot.Size)
$screenshot.Save("C:\Users\Kamyar Shah\Documents\AutomationBot\immediate_proof.png")
$graphics.Dispose()
$screenshot.Dispose()

Write-Output "IMMEDIATE SCREENSHOT CAPTURED"