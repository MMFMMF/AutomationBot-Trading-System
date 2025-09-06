@echo off
cd /d "C:\Users\Kamyar Shah\Documents\AutomationBot"
start "" "dashboard_static.html"
timeout /t 5 /nobreak >nul
powershell -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $screenshot = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height); $graphics = [System.Drawing.Graphics]::FromImage($screenshot); $graphics.CopyFromScreen($screen.X, $screen.Y, 0, 0, $screenshot.Size); $screenshot.Save('C:\Users\Kamyar Shah\Documents\AutomationBot\direct_proof.png'); $graphics.Dispose(); $screenshot.Dispose(); Write-Host 'DIRECT SCREENSHOT CAPTURED'"