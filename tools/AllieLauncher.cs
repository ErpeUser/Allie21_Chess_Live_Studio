using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("Allie 2.1 Chess Live Studio")]
[assembly: AssemblyDescription("Windows-Starter für Allie 2.1 Chess Live Studio")]
[assembly: AssemblyCompany("Allie Chess Live Studio")]
[assembly: AssemblyProduct("Allie 2.1 Chess Live Studio")]
[assembly: AssemblyVersion("10.7.0.0")]
[assembly: AssemblyFileVersion("10.7.0.0")]

internal static class AllieLauncher
{
    private const string ViewerUrl = "http://127.0.0.1:8765/viewer";
    private const string HealthUrl = "http://127.0.0.1:8765/health";

    [STAThread]
    private static int Main(string[] args)
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string startScript = Path.Combine(root, "START_HIER.bat");
        string serverScript = Path.Combine(root, "backend", "live_server.py");

        if (args.Length > 0 && String.Equals(args[0], "--check", StringComparison.OrdinalIgnoreCase))
            return File.Exists(startScript) && File.Exists(serverScript) ? 0 : 2;

        if (ServerIsReady())
        {
            OpenViewer();
            return 0;
        }

        bool ownsMutex;
        using (var mutex = new Mutex(true, "Local\\Allie21ChessLiveStudioLauncher", out ownsMutex))
        {
            if (!ownsMutex)
            {
                MessageBox.Show(
                    "Allie Chess Live Studio wird bereits eingerichtet oder gestartet.\n\n" +
                    "Bitte warte kurz und öffne die EXE danach erneut.",
                    "Allie Chess Live Studio", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return 0;
            }

            if (!File.Exists(startScript))
            {
                MessageBox.Show(
                    "START_HIER.bat wurde nicht gefunden.\n\n" +
                    "Lege die EXE wieder in den vollständig entpackten Programmordner.",
                    "Start nicht möglich", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 2;
            }

            try
            {
                string commandProcessor = Environment.GetEnvironmentVariable("ComSpec");
                if (String.IsNullOrWhiteSpace(commandProcessor))
                    commandProcessor = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "cmd.exe");
                var startInfo = new ProcessStartInfo
                {
                    FileName = commandProcessor,
                    Arguments = "/d /c \"\"" + startScript + "\"\"",
                    WorkingDirectory = root,
                    UseShellExecute = false,
                    CreateNoWindow = false,
                    WindowStyle = ProcessWindowStyle.Normal
                };
                startInfo.EnvironmentVariables["ALLIE_NO_BROWSER"] = "1";
                Form progressWindow = CreateProgressWindow();
                progressWindow.Show();
                Application.DoEvents();
                using (Process process = Process.Start(startInfo))
                {
                    if (process == null)
                        throw new InvalidOperationException("Der Startprozess konnte nicht erzeugt werden.");
                    while (!process.WaitForExit(400))
                    {
                        Application.DoEvents();
                        if (ServerIsReady())
                        {
                            progressWindow.Close();
                            OpenViewer();
                            return 0;
                        }
                    }
                    progressWindow.Close();
                    if (ServerIsReady())
                    {
                        OpenViewer();
                        return 0;
                    }
                    if (process.ExitCode != 0)
                        throw new InvalidOperationException("Die Einrichtung wurde mit Fehlercode " + process.ExitCode + " beendet.");
                }
                throw new InvalidOperationException("Der Startprozess wurde beendet, bevor der lokale Server bereit war.");
            }
            catch (Exception exception)
            {
                MessageBox.Show(
                    "Der Studio-Start ist fehlgeschlagen.\n\n" + exception.Message,
                    "Allie Chess Live Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
        }
    }

    private static Form CreateProgressWindow()
    {
        var form = new Form
        {
            Text = "Allie Chess Live Studio",
            StartPosition = FormStartPosition.CenterScreen,
            FormBorderStyle = FormBorderStyle.FixedDialog,
            MaximizeBox = false,
            MinimizeBox = true,
            ClientSize = new System.Drawing.Size(470, 150),
            TopMost = true
        };
        var title = new Label
        {
            Text = "Allie Chess Live Studio wird gestartet …",
            AutoSize = false,
            Left = 24,
            Top = 22,
            Width = 420,
            Height = 28,
            Font = new System.Drawing.Font("Segoe UI", 12F, System.Drawing.FontStyle.Bold)
        };
        var note = new Label
        {
            Text = "Beim ersten Start werden Komponenten eingerichtet. Das kann einige Minuten dauern. Der Browser öffnet sich automatisch.",
            AutoSize = false,
            Left = 24,
            Top = 56,
            Width = 420,
            Height = 45
        };
        var bar = new ProgressBar
        {
            Left = 24,
            Top = 112,
            Width = 420,
            Height = 14,
            Style = ProgressBarStyle.Marquee,
            MarqueeAnimationSpeed = 30
        };
        form.Controls.Add(title);
        form.Controls.Add(note);
        form.Controls.Add(bar);
        return form;
    }

    private static bool ServerIsReady()
    {
        try
        {
            var request = (HttpWebRequest)WebRequest.Create(HealthUrl);
            request.Method = "GET";
            request.Timeout = 700;
            request.ReadWriteTimeout = 700;
            request.Proxy = null;
            using (var response = (HttpWebResponse)request.GetResponse())
            using (var reader = new StreamReader(response.GetResponseStream()))
                return response.StatusCode == HttpStatusCode.OK && reader.ReadToEnd().Contains("\"alive\": true");
        }
        catch (WebException)
        {
            return false;
        }
        catch (IOException)
        {
            return false;
        }
    }

    private static void OpenViewer()
    {
        try
        {
            Process.Start(new ProcessStartInfo { FileName = ViewerUrl, UseShellExecute = true });
        }
        catch (Exception exception)
        {
            MessageBox.Show(
                "Der Viewer läuft unter:\n" + ViewerUrl + "\n\n" + exception.Message,
                "Browser konnte nicht geöffnet werden", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }
}
