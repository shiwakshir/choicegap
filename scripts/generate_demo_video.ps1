$ErrorActionPreference = 'Stop'
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
Add-Type -AssemblyName System.Runtime.WindowsRuntime
Add-Type -AssemblyName System.Drawing

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await-WinRt($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

$allVoices = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices
$voiceMark = ($allVoices | Where-Object { $_.DisplayName -match 'Mark' } | Select-Object -First 1)
$voiceHazel = ($allVoices | Where-Object { $_.DisplayName -match 'Hazel|Susan|Zira' } | Select-Object -First 1)
$voiceGeorge = ($allVoices | Where-Object { $_.DisplayName -match 'George|David' } | Select-Object -First 1)
if (-not $voiceMark) { $voiceMark = $allVoices[0] }
if (-not $voiceHazel) { $voiceHazel = $allVoices[0] }
if (-not $voiceGeorge) { $voiceGeorge = $voiceMark }

Write-Output "Presenter Voice: $($voiceMark.DisplayName) | Moderator Voice: $($voiceHazel.DisplayName) | Participant Voice: $($voiceGeorge.DisplayName)"

$code = @"
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;
using System.Runtime.InteropServices;

public class StepSpec {
    public int Scene;
    public int SubStep;
    public string SceneTitle;
    public string HighlightLabel;
    public string Caption;
    public float Fx, Fy, Fw, Fh;
    public float Cx, Cy;
    public byte[] AudioPcm44k;
}

public class DemoVideoV2 {
    [DllImport("mfplat.dll", ExactSpelling = true)] public static extern int MFStartup(int version, int dwFlags);
    [DllImport("mfplat.dll", ExactSpelling = true)] public static extern int MFShutdown();
    [DllImport("mfplat.dll", ExactSpelling = true)] public static extern int MFCreateMediaType(out IntPtr ppMFType);
    [DllImport("mfplat.dll", ExactSpelling = true)] public static extern int MFCreateSample(out IntPtr ppIMFSample);
    [DllImport("mfplat.dll", ExactSpelling = true)] public static extern int MFCreateMemoryBuffer(uint cbMaxLength, out IntPtr ppBuffer);
    [DllImport("mfreadwrite.dll", ExactSpelling = true, CharSet = CharSet.Unicode)]
    public static extern int MFCreateSinkWriterFromURL(string pwszOutputURL, IntPtr pByteStream, IntPtr pAttributes, out IntPtr ppSinkWriter);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetGUIDDel(IntPtr pThis, ref Guid key, ref Guid val);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetUINT32Del(IntPtr pThis, ref Guid key, uint val);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetUINT64Del(IntPtr pThis, ref Guid key, ulong val);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int AddStreamDel(IntPtr pThis, IntPtr pTargetMediaType, out uint pdwStreamIndex);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetInputMediaTypeDel(IntPtr pThis, uint dwStreamIndex, IntPtr pInputMediaType, IntPtr pEncodingParameters);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int BeginWritingDel(IntPtr pThis);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int WriteSampleDel(IntPtr pThis, uint dwStreamIndex, IntPtr pSample);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int FinalizeDel(IntPtr pThis);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int LockDel(IntPtr pThis, out IntPtr ppbBuffer, out uint pcbMax, out uint pcbCur);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int UnlockDel(IntPtr pThis);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetCurrentLengthDel(IntPtr pThis, uint cbCurrentLength);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int AddBufferDel(IntPtr pThis, IntPtr pBuffer);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetSampleTimeDel(IntPtr pThis, long hnsSampleTime);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetSampleDurationDel(IntPtr pThis, long hnsSampleDuration);

    static T VCall<T>(IntPtr ptr, int index) where T : class {
        IntPtr vtable = Marshal.ReadIntPtr(ptr);
        IntPtr fn = Marshal.ReadIntPtr(vtable, index * IntPtr.Size);
        return Marshal.GetDelegateForFunctionPointer(fn, typeof(T)) as T;
    }

    static void SetGUID(IntPtr mt, Guid k, Guid v) { int hr = VCall<SetGUIDDel>(mt, 24)(mt, ref k, ref v); if (hr < 0) throw new Exception("SetGUID " + hr); }
    static void SetUINT32(IntPtr mt, Guid k, uint v) { int hr = VCall<SetUINT32Del>(mt, 21)(mt, ref k, v); if (hr < 0) throw new Exception("SetUINT32 " + hr); }
    static void SetUINT64(IntPtr mt, Guid k, ulong v) { int hr = VCall<SetUINT64Del>(mt, 22)(mt, ref k, v); if (hr < 0) throw new Exception("SetUINT64 " + hr); }

    static void WriteBuffer(IntPtr sw, uint stream, byte[] data, long timeHns, long durHns) {
        IntPtr buf; MFCreateMemoryBuffer((uint)data.Length, out buf);
        IntPtr ptr; uint max, cur;
        VCall<LockDel>(buf, 3)(buf, out ptr, out max, out cur);
        Marshal.Copy(data, 0, ptr, data.Length);
        VCall<UnlockDel>(buf, 4)(buf);
        VCall<SetCurrentLengthDel>(buf, 6)(buf, (uint)data.Length);

        IntPtr sample; MFCreateSample(out sample);
        VCall<AddBufferDel>(sample, 42)(sample, buf);
        VCall<SetSampleTimeDel>(sample, 36)(sample, timeHns);
        VCall<SetSampleDurationDel>(sample, 38)(sample, durHns);

        int hr = VCall<WriteSampleDel>(sw, 6)(sw, stream, sample);
        Marshal.Release(sample);
        Marshal.Release(buf);
        if (hr < 0) throw new Exception("WriteSample " + hr);
    }

    public static byte[] ConvertWavTo44kPcm(byte[] wavBytes, int padMs) {
        int sr = 16000;
        int channels = 1;
        int pos = 12;
        int dataOffset = 44;
        int dataLen = wavBytes.Length - 44;
        while (pos + 8 <= wavBytes.Length) {
            string chunkId = System.Text.Encoding.ASCII.GetString(wavBytes, pos, 4);
            int chunkSize = BitConverter.ToInt32(wavBytes, pos + 4);
            if (chunkId == "fmt ") {
                channels = BitConverter.ToInt16(wavBytes, pos + 10);
                sr = BitConverter.ToInt32(wavBytes, pos + 12);
            } else if (chunkId == "data") {
                dataOffset = pos + 8;
                dataLen = Math.Min(chunkSize, wavBytes.Length - dataOffset);
                break;
            }
            pos += 8 + chunkSize + (chunkSize % 2);
        }
        int frameSize = 2 * channels;
        int inSamples = dataLen / frameSize;
        double[] src = new double[inSamples];
        for (int i = 0; i < inSamples; i++) {
            src[i] = (double)BitConverter.ToInt16(wavBytes, dataOffset + i * frameSize);
        }
        int outSamples = (int)((long)inSamples * 44100L / sr);
        int padSamples = (44100 * padMs) / 1000;
        byte[] result = new byte[(outSamples + padSamples) * 2];
        // Exact sample-rate ratio (inSamples / outSamples) so playback speed & pitch are 100% unaltered
        double ratio = (double)sr / 44100.0;
        for (int i = 0; i < outSamples; i++) {
            double idx = i * ratio;
            int i1 = (int)idx;
            int i0 = Math.Max(0, i1 - 1);
            int i2 = Math.Min(inSamples - 1, i1 + 1);
            int i3 = Math.Min(inSamples - 1, i1 + 2);
            double t = idx - i1;
            // Catmull-Rom cubic interpolation for clean, natural voice timbre
            double a0 = -0.5 * src[i0] + 1.5 * src[i1] - 1.5 * src[i2] + 0.5 * src[i3];
            double a1 = src[i0] - 2.5 * src[i1] + 2.0 * src[i2] - 0.5 * src[i3];
            double a2 = -0.5 * src[i0] + 0.5 * src[i2];
            double a3 = src[i1];
            double val = ((a0 * t + a1) * t + a2) * t + a3;
            int clamped = Math.Max(-32000, Math.Min(32000, (int)Math.Round(val * 0.92)));
            short s = (short)clamped;
            result[i * 2] = (byte)(s & 0xFF);
            result[i * 2 + 1] = (byte)((s >> 8) & 0xFF);
        }
        return result;
    }

    static GraphicsPath RoundedRect(RectangleF r, float radius) {
        GraphicsPath path = new GraphicsPath();
        float d = radius * 2f;
        if (d <= 0f) { path.AddRectangle(r); return path; }
        path.AddArc(r.X, r.Y, d, d, 180, 90);
        path.AddArc(r.Right - d, r.Y, d, d, 270, 90);
        path.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
        path.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
        path.CloseFigure();
        return path;
    }

    static void FillRound(Graphics g, Brush b, float x, float y, float w, float h, float rad) {
        using (GraphicsPath p = RoundedRect(new RectangleF(x, y, w, h), rad)) g.FillPath(b, p);
    }

    static void DrawRound(Graphics g, Pen pen, float x, float y, float w, float h, float rad) {
        using (GraphicsPath p = RoundedRect(new RectangleF(x, y, w, h), rad)) g.DrawPath(pen, p);
    }

    static void Card(Graphics g, float x, float y, float w, float h, Color bg, Color border, float rad = 10f) {
        using (SolidBrush b = new SolidBrush(bg)) FillRound(g, b, x, y, w, h, rad);
        using (Pen p = new Pen(border, 1.5f)) DrawRound(g, p, x, y, w, h, rad);
    }

    static void Pill(Graphics g, string text, float x, float y, Color bg, Color fg, Font f) {
        SizeF sz = g.MeasureString(text, f);
        float w = sz.Width + 20f, h = sz.Height + 8f;
        using (SolidBrush b = new SolidBrush(bg)) FillRound(g, b, x, y, w, h, h / 2f);
        using (SolidBrush tb = new SolidBrush(fg)) g.DrawString(text, f, tb, x + 10f, y + 4f);
    }

    static void DrawSpotlightAndHighlight(Graphics g, float fx, float fy, float fw, float fh, string label, float p) {
        if (fw <= 0 || fh <= 0) return;
        // 1. Softly dim everything outside the highlighted focus rectangle (above the caption bar)
        using (Region dimRegion = new Region(new RectangleF(0, 74, 1920, 842)))
        using (GraphicsPath cutPath = RoundedRect(new RectangleF(fx - 6, fy - 6, fw + 12, fh + 12), 14f)) {
            dimRegion.Exclude(cutPath);
            using (SolidBrush dimBrush = new SolidBrush(Color.FromArgb(68, 14, 24, 22))) {
                g.FillRegion(dimBrush, dimRegion);
            }
        }

        // 2. Pulsing outer glow + crisp highlight ring around the exact element being spoken about
        float pulse = (float)(Math.Sin(p * Math.PI * 6.0) * 2.5 + 2.5);
        using (Pen glowPen1 = new Pen(Color.FromArgb(75, 16, 185, 129), 9f + pulse))
            DrawRound(g, glowPen1, fx - 5, fy - 5, fw + 10, fh + 10, 14f);
        using (Pen glowPen2 = new Pen(Color.FromArgb(230, 16, 163, 112), 3.5f))
            DrawRound(g, glowPen2, fx - 3, fy - 3, fw + 6, fh + 6, 12f);

        // 3. Floating callout badge anchored cleanly at the top-right border of the highlighted box
        using (Font fTag = new Font("Segoe UI", 10.5f, FontStyle.Bold)) {
            string badgeText = "\u25B6 SPEAKING ABOUT: " + label;
            SizeF sz = g.MeasureString(badgeText, fTag);
            float bw = sz.Width + 28f, bh = 32f;
            float bx = Math.Max(40f, Math.Min(1870f - bw, fx + fw - bw - 14f));
            float by = Math.Max(78f, fy - 16f);
            using (SolidBrush shadow = new SolidBrush(Color.FromArgb(70, 0, 0, 0)))
                FillRound(g, shadow, bx + 2, by + 3, bw, bh, 16f);
            using (SolidBrush bg = new SolidBrush(Color.FromArgb(20, 83, 68)))
                FillRound(g, bg, bx, by, bw, bh, 16f);
            using (Pen borderPen = new Pen(Color.FromArgb(110, 231, 183), 2f))
                DrawRound(g, borderPen, bx, by, bw, bh, 16f);
            using (SolidBrush fg = new SolidBrush(Color.FromArgb(236, 253, 245)))
                g.DrawString(badgeText, fTag, fg, bx + 14f, by + 6f);
        }
    }

    static void DrawHeader(Graphics g, bool participantMode, int activeStep, string metaBadge) {
        Color line = Color.FromArgb(223, 228, 230);
        Color ink = Color.FromArgb(36, 49, 54);
        Color green = Color.FromArgb(35, 90, 80);
        Color muted = Color.FromArgb(98, 109, 114);

        g.FillRectangle(Brushes.White, 0, 0, 1920, 74);
        using (Pen p = new Pen(line, 1.5f)) g.DrawLine(p, 0, 74, 1920, 74);

        using (SolidBrush b = new SolidBrush(ink)) FillRound(g, b, 48, 19, 36, 36, 8f);
        using (Font fLogo = new Font("Segoe UI", 11f, FontStyle.Bold))
            g.DrawString("CG", fLogo, Brushes.White, 53, 27);
        using (Font fBrand = new Font("Segoe UI", 18f, FontStyle.Bold))
        using (SolidBrush bInk = new SolidBrush(ink))
            g.DrawString("ChoiceGap", fBrand, bInk, 94, 21);

        using (Pen p = new Pen(line, 1.5f)) g.DrawLine(p, 240, 22, 240, 52);
        using (Font fCtx = new Font("Segoe UI", 11.5f, FontStyle.Regular))
        using (SolidBrush bMut = new SolidBrush(muted))
            g.DrawString(participantMode ? "Participant session \u00B7 Blinded to researcher hypotheses" : "Research Studio \u00B7 Verifiable Meta Muse Agent", fCtx, bMut, 258, 27);

        using (Font fBadge = new Font("Consolas", 10.5f, FontStyle.Bold)) {
            SizeF sz = g.MeasureString(metaBadge, fBadge);
            float bx = 1360 - sz.Width;
            Card(g, bx, 19, sz.Width + 28, 36, Color.FromArgb(232, 244, 239), green, 18f);
            using (SolidBrush bg = new SolidBrush(green))
                g.DrawString(metaBadge, fBadge, bg, bx + 14, 28);
        }

        Card(g, 1410, 18, 195, 38, Color.FromArgb(237, 244, 240), green, 7f);
        using (Font fBtn = new Font("Segoe UI", 10.5f, FontStyle.Bold))
        using (SolidBrush bg = new SolidBrush(green))
            g.DrawString(participantMode ? "\u2190 Researcher view" : "Participant view \u2192", fBtn, bg, 1432, 27);

        Card(g, 1620, 18, 130, 38, Color.White, line, 7f);
        using (Font fBtn = new Font("Segoe UI", 10.5f, FontStyle.Bold))
        using (SolidBrush bInk = new SolidBrush(ink))
            g.DrawString("Study library", fBtn, bInk, 1640, 27);

        Card(g, 1765, 18, 110, 38, Color.White, line, 7f);
        using (Font fBtn = new Font("Segoe UI", 10f, FontStyle.Regular))
        using (SolidBrush bMut = new SolidBrush(muted))
            g.DrawString("localhost:8000", fBtn, bMut, 1775, 28);

        if (!participantMode && activeStep > 0) {
            string[] titles = { "Brief", "Study design", "Collect", "Findings" };
            string[] subs = { "Define the research", "Review the questions", "Invite participants", "Review the evidence" };
            using (Font fNavLbl = new Font("Segoe UI", 9.5f, FontStyle.Bold))
            using (SolidBrush bMut = new SolidBrush(muted))
                g.DrawString("STUDY WORKFLOW", fNavLbl, bMut, 54, 108);

            for (int i = 0; i < 4; i++) {
                float ny = 140 + i * 74;
                bool cur = (i + 1) == activeStep;
                if (cur) {
                    using (SolidBrush bCur = new SolidBrush(Color.FromArgb(231, 238, 235)))
                        FillRound(g, bCur, 44, ny, 210, 62, 8f);
                }
                using (SolidBrush bCirc = new SolidBrush(cur ? green : Color.White))
                    g.FillEllipse(bCirc, 58, ny + 16, 28, 28);
                using (Pen pCirc = new Pen(cur ? green : Color.FromArgb(186, 197, 196), 1.5f))
                    g.DrawEllipse(pCirc, 58, ny + 16, 28, 28);
                using (Font fIdx = new Font("Segoe UI", 10f, FontStyle.Bold))
                using (SolidBrush bIdx = new SolidBrush(cur ? Color.White : muted))
                    g.DrawString((i + 1).ToString(), fIdx, bIdx, 67, ny + 21);

                using (Font fT = new Font("Segoe UI", 11.5f, FontStyle.Bold))
                using (SolidBrush bT = new SolidBrush(cur ? Color.FromArgb(33, 79, 70) : ink))
                    g.DrawString(titles[i], fT, bT, 98, ny + 11);
                using (Font fS = new Font("Segoe UI", 9.5f, FontStyle.Regular))
                using (SolidBrush bS = new SolidBrush(muted))
                    g.DrawString(subs[i], fS, bS, 98, ny + 33);
            }
        }
    }

    static void DrawCaptionBar(Graphics g, string sceneTitle, string highlightLabel, string caption, float progress, float elapsedSec, float totalSec) {
        float bx = 90, by = 922, bw = 1740, bh = 132;
        using (SolidBrush shadow = new SolidBrush(Color.FromArgb(65, 0, 0, 0)))
            FillRound(g, shadow, bx + 4, by + 6, bw, bh, 14f);
        Card(g, bx, by, bw, bh, Color.FromArgb(248, 18, 30, 29), Color.FromArgb(72, 138, 120), 14f);

        using (Font fScene = new Font("Segoe UI", 10.5f, FontStyle.Bold))
        using (SolidBrush bMint = new SolidBrush(Color.FromArgb(153, 232, 209)))
            g.DrawString(sceneTitle + "   \u00B7   FOCUS: " + highlightLabel, fScene, bMint, bx + 26, by + 14);

        string timeStr = string.Format("{0}:{1:00} / {2}:{3:00}", (int)(elapsedSec / 60), (int)(elapsedSec % 60), (int)(totalSec / 60), (int)(totalSec % 60));
        using (Font fTime = new Font("Consolas", 10.5f, FontStyle.Bold))
        using (SolidBrush bMint = new SolidBrush(Color.FromArgb(153, 232, 209)))
            g.DrawString(timeStr, fTime, bMint, bx + bw - 135, by + 14);

        using (Font fCap = new Font("Segoe UI", 14.5f, FontStyle.Bold))
        using (SolidBrush bWhite = new SolidBrush(Color.FromArgb(250, 253, 252)))
            g.DrawString("\"" + caption + "\"", fCap, bWhite, new RectangleF(bx + 26, by + 42, bw - 52, 68));

        using (SolidBrush bTrack = new SolidBrush(Color.FromArgb(45, 70, 66)))
            FillRound(g, bTrack, bx + 26, by + bh - 12, bw - 52, 5, 2.5f);
        using (SolidBrush bFill = new SolidBrush(Color.FromArgb(110, 231, 183)))
            FillRound(g, bFill, bx + 26, by + bh - 12, Math.Max(8f, (bw - 52) * progress), 5, 2.5f);
    }

    static void DrawCursor(Graphics g, float x, float y, bool clicking) {
        if (x <= 0 && y <= 0) return;
        if (clicking) {
            using (Pen pRipple = new Pen(Color.FromArgb(200, 16, 185, 129), 3.5f))
                g.DrawEllipse(pRipple, x - 20, y - 20, 40, 40);
            using (SolidBrush bRipple = new SolidBrush(Color.FromArgb(75, 16, 185, 129)))
                g.FillEllipse(bRipple, x - 14, y - 14, 28, 28);
        }
        PointF[] pts = new PointF[] {
            new PointF(x, y),
            new PointF(x, y + 28),
            new PointF(x + 7, y + 21),
            new PointF(x + 14, y + 33),
            new PointF(x + 18, y + 31),
            new PointF(x + 11, y + 19),
            new PointF(x + 21, y + 19)
        };
        using (SolidBrush bShadow = new SolidBrush(Color.FromArgb(95, 0, 0, 0))) {
            PointF[] sp = new PointF[pts.Length];
            for (int i = 0; i < pts.Length; i++) sp[i] = new PointF(pts[i].X + 2, pts[i].Y + 2);
            g.FillPolygon(bShadow, sp);
        }
        g.FillPolygon(Brushes.White, pts);
        using (Pen p = new Pen(Color.FromArgb(20, 32, 30), 2f)) g.DrawPolygon(p, pts);
    }

    public static void RenderFrame(Graphics g, StepSpec step, float p, float curX, float curY, float elapsedSec, float totalSec) {
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
        Color paper = Color.FromArgb(245, 246, 247);
        Color ink = Color.FromArgb(36, 49, 54);
        Color muted = Color.FromArgb(98, 109, 114);
        Color green = Color.FromArgb(35, 90, 80);
        Color line = Color.FromArgb(215, 222, 225);
        Color mintBg = Color.FromArgb(234, 244, 239);
        g.Clear(paper);

        int scene = step.Scene;
        int sub = step.SubStep;

        using (Font fH1 = new Font("Segoe UI", 24f, FontStyle.Bold))
        using (Font fH2 = new Font("Segoe UI", 15f, FontStyle.Bold))
        using (Font fH3 = new Font("Segoe UI", 12.5f, FontStyle.Bold))
        using (Font fBody = new Font("Segoe UI", 11.5f, FontStyle.Regular))
        using (Font fBold = new Font("Segoe UI", 11.5f, FontStyle.Bold))
        using (Font fSmall = new Font("Segoe UI", 10f, FontStyle.Regular))
        using (Font fMono = new Font("Consolas", 10.5f, FontStyle.Bold))
        using (SolidBrush bInk = new SolidBrush(ink))
        using (SolidBrush bMut = new SolidBrush(muted))
        using (SolidBrush bGreen = new SolidBrush(green)) {

            if (scene == 0) {
                DrawHeader(g, false, 0, "Meta Global AI Developer Hackathon \u00B7 Build for Your World");
                Card(g, 80, 102, 1760, 800, Color.White, line, 14f);
                Pill(g, "BRIEF-LED ADAPTIVE SURVEYS & VERIFIABLE AI-MODERATED UX RESEARCH", 120, 132, mintBg, green, fMono);
                g.DrawString("ChoiceGap: Verifiable Multimodal UX Research with Meta Muse", fH1, bInk, 120, 172);
                g.DrawString("Bridging the say\u2013do gap between static surveys and unscalable human interviews\u2014while code enforces strict methodological guardrails.", fBody, bMut, 120, 222);

                Card(g, 120, 268, 810, 175, Color.FromArgb(253, 246, 244), Color.FromArgb(228, 190, 180), 10f);
                using (SolidBrush bRed = new SolidBrush(Color.FromArgb(155, 55, 40)))
                    g.DrawString("The UX & Product Research Bottleneck", fH2, bRed, 145, 286);
                g.DrawString("\u2022 Static surveys capture what users click, but miss context and practical barriers.\n\u2022 Human-moderated interviews don't scale across hundreds of sessions.\n\u2022 Unguarded AI chatbots ask leading questions, invent stimuli, or hallucinate findings.", fBody, bInk, new RectangleF(145, 322, 760, 110));

                Card(g, 960, 268, 840, 175, mintBg, Color.FromArgb(165, 205, 190), 10f);
                g.DrawString("How ChoiceGap Solves It (Verifiable Agent Loop)", fH2, bGreen, 985, 286);
                g.DrawString("\u2022 Researcher approves every question, stimulus, follow-up topic, and comparison variant.\n\u2022 3D Spoken AI Moderator + live Muse Voice streaming + participant transcript review.\n\u2022 Native tool calling tests single-cell trade-offs; synthesis cites exact response IDs.", fBody, bInk, new RectangleF(985, 322, 790, 110));

                string[,] models = new string[,] {
                    { "1. Muse Spark 1.3 \u00B7 Web Grounding", "POST /v1/responses (web_search)", "Cited desk research with validated URL spans & SHA-256 brief digest." },
                    { "2. Muse Image 1.0 \u00B7 Visual Stimuli", "POST /v1/images/generations & /edits", "Generates & revises fictional product concept stimuli before study lock." },
                    { "3. Muse Spark 1.3 \u00B7 Structured Design", "POST /v1/chat/completions (strict JSON)", "Drafts multi-type surveys, interview guides, and bounded probes." },
                    { "4. Muse Voice Transcribe 1.0 \u00B7 Live ASR", "wss://api.meta.ai/v1/asr/realtime", "16 kHz PCM streaming with native endpointing & vocabulary hints." },
                    { "5. Muse Spark 1.3 \u00B7 Video Task Review", "POST /v1/responses (input_video)", "Extracts timestamped visible task events for participant confirmation." },
                    { "6. Muse Spark 1.3 \u00B7 Native Tool Calling", "select_approved_condition + Synthesis", "Selects single-cell variants mid-study & synthesizes 0\u20134 cited findings." }
                };
                for (int i = 0; i < 6; i++) {
                    int col = i % 3, row = i / 3;
                    float mx = 120 + col * 570, my = 468 + row * 195;
                    Card(g, mx, my, 540, 172, Color.FromArgb(248, 252, 250), green, 10f);
                    Pill(g, models[i, 1], mx + 20, my + 18, mintBg, green, fMono);
                    g.DrawString(models[i, 0], fH3, bInk, mx + 20, my + 58);
                    g.DrawString(models[i, 2], fBody, bMut, new RectangleF(mx + 20, my + 90, 500, 68));
                }
            }
            else if (scene == 1) {
                DrawHeader(g, false, 1, "muse-spark-1.3 (/v1/responses web_search) + muse-image-1.0 (/v1/images/generations)");
                g.DrawString("STEP 1 \u00B7 RESEARCH BRIEF & MULTIMODAL PREPARATION", fMono, bGreen, 290, 96);
                g.DrawString("Start with a research question.", fH1, bInk, 290, 120);

                Card(g, 290, 178, 760, 720, Color.White, line, 10f);
                g.DrawString("The brief \u00B7 Sustainable shopping example loaded", fH2, bInk, 318, 200);
                Card(g, 318, 238, 704, 130, Color.FromArgb(250, 251, 252), line, 7f);
                g.DrawString("A grocery retailer wants to understand why shoppers who care about sustainability sometimes choose conventional delivery. We need to decide whether to test price, convenient delivery slots or clearer evidence behind environmental claims.", fBody, bInk, new RectangleF(332, 250, 676, 108));

                Card(g, 318, 386, 704, 245, mintBg, green, 8f);
                Pill(g, "Muse Spark 1.3 \u00B7 POST /v1/responses \u00B7 tools: [{\"type\": \"web_search\"}]", 336, 402, Color.White, green, fMono);
                g.DrawString("Reviewed desk research (SHA-256 brief digest verified)", fH3, bInk, 336, 440);
                g.DrawString("\u2022 Online grocery shoppers frequently cite delivery-window width (4-hour vs 1-hour slots) and perishable arrival timing alongside delivery fees when evaluating eco-van consolidation.\n\u2022 Validated URL citations attached (kept strictly separate from participant evidence):", fBody, bInk, new RectangleF(336, 468, 668, 95));
                Pill(g, "[1] OECD Sustainable Last-Mile Logistics", 336, 560, Color.White, green, fSmall);
                Pill(g, "[2] Consumer Delivery Window Trade-Offs", 625, 560, Color.White, green, fSmall);
                g.DrawString("\u2611 I reviewed these sources and want them to inform the study draft.", fBold, bGreen, 336, 598);

                Card(g, 318, 650, 280, 48, green, green, 7f);
                g.DrawString("Create study draft \u2192", fH3, Brushes.White, 352, 662);

                Card(g, 1076, 178, 780, 720, Color.White, line, 10f);
                Pill(g, "Muse Image 1.0 \u00B7 POST /v1/images/generations & /v1/images/edits", 1104, 200, mintBg, green, fMono);
                g.DrawString("Visual Concept Stimulus (Researcher-Reviewed)", fH2, bInk, 1104, 238);
                g.DrawString("Prompt: \"Clean fictional mobile checkout comparing Eco-Van Consolidated Delivery (Tue 8am\u201312pm, \u00240) vs Standard 1-Hour Slot (Tue 5pm\u20136pm, \u00243.99)\"", fSmall, bMut, new RectangleF(1104, 272, 724, 44));

                Card(g, 1104, 326, 724, 415, Color.FromArgb(242, 247, 245), Color.FromArgb(170, 198, 188), 12f);
                g.DrawString("FICTIONAL GROCERY CHECKOUT CONCEPT \u00B7 GENERATED BY MUSE IMAGE 1.0", fMono, bGreen, 1132, 346);

                Card(g, 1132, 382, 330, 290, Color.White, green, 10f);
                Pill(g, "LOWER EMISSIONS \u00B7 \u00240 FEE", 1152, 402, mintBg, green, fMono);
                g.DrawString("Eco-Van Consolidated", fH2, bInk, 1152, 444);
                g.DrawString("Arrival window:\nTuesday, 8:00 AM \u2013 12:00 PM\n(4-hour daytime window)\n\nDelivery fee: \u00240.00\nGrouped neighborhood route", fBody, bInk, new RectangleF(1152, 484, 290, 165));

                Card(g, 1482, 382, 320, 290, Color.White, line, 10f);
                Pill(g, "DIRECT DISPATCH \u00B7 \u00243.99", 1502, 402, Color.FromArgb(240, 242, 244), ink, fMono);
                g.DrawString("Standard 1-Hour Slot", fH2, bInk, 1502, 444);
                g.DrawString("Arrival window:\nTuesday, 5:00 PM \u2013 6:00 PM\n(1-hour evening window)\n\nDelivery fee: \u00243.99\nIndividual courier trip", fBody, bInk, new RectangleF(1502, 484, 280, 165));

                g.DrawString("\u2713 Selected as approved study stimulus (locked with SHA-256 digest upon publication)", fBold, bGreen, 1132, 696);

                Card(g, 1104, 760, 220, 44, Color.White, line, 7f);
                g.DrawString("Generate a concept", fBold, bInk, 1134, 771);
                Card(g, 1340, 760, 240, 44, Color.White, green, 7f);
                g.DrawString("Edit the attached image", fBold, bGreen, 1368, 771);
            }
            else if (scene == 2) {
                DrawHeader(g, false, 2, "muse-spark-1.3 \u00B7 Structured JSON Schema (strict: true) & Single-Cell Matrix");
                g.DrawString("STEP 2 \u00B7 STUDY DESIGN, COMPARISON MATRIX & IMMUTABLE APPROVAL", fMono, bGreen, 290, 96);
                g.DrawString("Review your study before publishing.", fH1, bInk, 290, 120);

                // Left card: Survey & Interview Guide with full researcher editing tools
                Card(g, 290, 178, 770, 720, Color.White, line, 10f);
                Pill(g, "Drafted by Muse Spark 1.3 \u00B7 Full Researcher Input & Editing Controls", 316, 198, mintBg, green, fMono);
                g.DrawString("Survey & Open Interview Guide", fH2, bInk, 316, 234);

                // Section 1: Survey questions header + Add Question button
                g.DrawString("Survey questions (1 of 6)", fBold, bInk, 316, 266);
                Card(g, 908, 260, 132, 28, Color.White, green, 6f);
                g.DrawString("+ Add question", fSmall, bGreen, 924, 266);

                // Question 1 Editor Card
                Card(g, 314, 296, 724, 132, Color.FromArgb(250, 251, 252), line, 8f);
                g.DrawString("Question 1", fBold, bInk, 330, 308);
                Pill(g, "Rating scale (1\u20135) \u25BE", 416, 304, Color.White, green, fSmall);
                Pill(g, "\u2022 Stated priority", 584, 304, mintBg, green, fSmall);
                // Action tools: Up, Down, Remove
                Card(g, 894, 304, 30, 24, Color.White, line, 4f);
                g.DrawString("\u2191", fSmall, bInk, 904, 308);
                Card(g, 928, 304, 30, 24, Color.White, line, 4f);
                g.DrawString("\u2193", fSmall, bInk, 938, 308);
                Card(g, 962, 304, 64, 24, Color.FromArgb(254, 242, 242), Color.FromArgb(239, 68, 68), 4f);
                g.DrawString("Remove", fSmall, Brushes.Crimson, 968, 308);

                Card(g, 330, 336, 692, 46, Color.White, line, 6f);
                g.DrawString("\"When ordering groceries online, how important is reducing delivery emissions?\"", fBody, bInk, 338, 348);
                g.DrawString("Endpoints: 1 \u00B7 Not at all important   <->   5 \u00B7 Very important", fSmall, bMut, 332, 392);

                // Section 2: Interview guide header + Add Question button
                g.DrawString("Interview guide (1 of 4)", fBold, bInk, 316, 442);
                Card(g, 908, 436, 132, 28, Color.White, green, 6f);
                g.DrawString("+ Add question", fSmall, bGreen, 924, 442);

                // Interview 1 Editor Card
                Card(g, 314, 472, 724, 136, Color.FromArgb(250, 251, 252), line, 8f);
                g.DrawString("Interview 1", fBold, bInk, 330, 484);
                Pill(g, "Open ended \u25BE", 416, 480, Color.White, green, fSmall);
                Pill(g, "Spoken AI Moderator", 530, 480, mintBg, green, fSmall);
                Card(g, 894, 480, 30, 24, Color.White, line, 4f);
                g.DrawString("\u2191", fSmall, bInk, 904, 484);
                Card(g, 928, 480, 30, 24, Color.White, line, 4f);
                g.DrawString("\u2193", fSmall, bInk, 938, 484);
                Card(g, 962, 480, 64, 24, Color.FromArgb(254, 242, 242), Color.FromArgb(239, 68, 68), 4f);
                g.DrawString("Remove", fSmall, Brushes.Crimson, 968, 484);

                Card(g, 330, 512, 692, 54, Color.White, line, 6f);
                g.DrawString("\"Think of your most recent online grocery order. Walk me through which delivery slot you picked and what practical details mattered that day.\"", fBody, bInk, new RectangleF(338, 520, 676, 42));
                g.DrawString("Participant response: Spoken voice or typed text \u00B7 Editable transcript before sending", fSmall, bMut, 332, 576);

                // Section 3: Permitted Follow-Up Topics
                Card(g, 314, 622, 724, 140, mintBg, green, 8f);
                g.DrawString("Permitted Follow-Up Topics (Editable by Researcher \u00B7 Enforced by Code)", fH3, bInk, 330, 638);
                Pill(g, "Delivery timing & schedule constraints", 330, 668, Color.White, green, fBold);
                Pill(g, "Perishable food safety", 645, 668, Color.White, green, fBold);
                Pill(g, "Delivery fee trade-offs", 330, 710, Color.White, green, fBold);
                Pill(g, "Trust in environmental claims", 545, 710, Color.White, green, fBold);
                g.DrawString("Probe budget: max 2 survey & 3 interview probes. Out-of-bounds topics rejected.", fSmall, bMut, 316, 772);

                // Right card: Perfectly aligned comparison grid table & publication controls
                Card(g, 1084, 178, 772, 720, Color.White, line, 10f);
                Pill(g, "Controlled Single-Cell Comparison Matrix \u00B7 Audited by Code", 1108, 198, mintBg, green, fMono);
                g.DrawString("Test Which Conditions Change a Choice", fH2, bInk, 1108, 234);

                // Grid Table Card
                Card(g, 1108, 270, 724, 218, Color.White, line, 8f);
                // Header Row Background
                using (SolidBrush bThBg = new SolidBrush(Color.FromArgb(240, 246, 243)))
                    FillRound(g, bThBg, 1109, 271, 722, 42, 7f);
                using (SolidBrush bThBgFix = new SolidBrush(Color.FromArgb(240, 246, 243)))
                    g.FillRectangle(bThBgFix, 1109, 290, 722, 23);

                // Columns: Detail (x=1126), Option A (x=1290), Option B (x=1570)
                g.DrawString("Detail", fBold, bInk, 1126, 282);
                g.DrawString("Option A: Eco-Van", fBold, bGreen, 1290, 282);
                g.DrawString("Option B: Standard Slot", fBold, bInk, 1570, 282);

                using (Pen pGrid = new Pen(line, 1f)) {
                    // Horizontal dividers
                    g.DrawLine(pGrid, 1108, 313, 1832, 313);
                    g.DrawLine(pGrid, 1108, 355, 1832, 355);
                    g.DrawLine(pGrid, 1108, 397, 1832, 397);
                    g.DrawLine(pGrid, 1108, 439, 1832, 439);
                    // Vertical dividers
                    g.DrawLine(pGrid, 1275, 270, 1275, 439);
                    g.DrawLine(pGrid, 1555, 270, 1555, 439);
                }

                // Row 1: Arrival window
                g.DrawString("Arrival window", fBold, bInk, 1126, 324);
                g.DrawString("Tue 8:00 AM \u2013 12:00 PM", fBody, bInk, 1290, 324);
                g.DrawString("Tue 5:00 PM \u2013 6:00 PM", fBody, bInk, 1570, 324);

                // Row 2: Delivery fee
                g.DrawString("Delivery fee", fBold, bInk, 1126, 366);
                g.DrawString("\u00240.00 (No fee)", fBold, bGreen, 1290, 366);
                g.DrawString("\u00243.99", fBody, bInk, 1570, 366);

                // Row 3: CO2 impact
                g.DrawString("CO2 impact", fBold, bInk, 1126, 408);
                g.DrawString("Consolidated (-45% CO2e)", fBody, bInk, 1290, 408);
                g.DrawString("Standard courier trip", fBody, bInk, 1570, 408);

                // Single-cell variation callout strip
                using (SolidBrush bV1Strip = new SolidBrush(mintBg))
                    FillRound(g, bV1Strip, 1109, 440, 722, 46, 7f);
                g.DrawString("\u25B6 Approved Change V1: Change ONLY Option A Arrival window \u2192 \"Tue 5:00 PM \u2013 6:00 PM\"", fBold, bGreen, 1124, 454);

                // Collection & Moderator Settings
                Card(g, 1108, 508, 724, 280, Color.FromArgb(250, 251, 252), line, 8f);
                g.DrawString("Collection & Moderator Settings", fH3, bInk, 1128, 526);
                g.DrawString("\u2611 Study format: Survey, then interview\n\u2611 Offer a spoken AI moderator and voice answers (Muse Voice Transcribe 1.0)\n\u2611 Moderator appearance: Included 3D AI character (Local Three.js)\n\u2611 I reviewed the questions, stimulus, follow-up topics and use of participant data.", fBody, bInk, new RectangleF(1128, 558, 684, 140));

                Card(g, 1128, 716, 310, 52, green, green, 8f);
                g.DrawString("Publish participant link \u2192", fH3, Brushes.White, 1160, 729);
            }
            else if (scene == 3) {
                DrawHeader(g, true, 0, "muse-spark-1.3 \u00B7 POST /v1/responses (input_video) \u00B7 Task Recording Review");
                Card(g, 210, 102, 1500, 800, Color.White, line, 14f);
                Pill(g, "PARTICIPANT MODE \u00B7 BLINDED TO HYPOTHESES \u00B7 EXPLICIT CONSENT", 250, 130, mintBg, green, fMono);
                g.DrawString("Task Recording & Baseline Priority Check", fH1, bInk, 250, 166);

                Card(g, 250, 232, 660, 630, Color.FromArgb(250, 251, 252), line, 10f);
                g.DrawString("SURVEY \u00B7 QUESTION 1 OF 1", fMono, bGreen, 278, 256);
                g.DrawString("When ordering groceries online, how important is reducing delivery emissions to you?", fH2, bInk, new RectangleF(278, 286, 600, 70));

                for (int r = 1; r <= 5; r++) {
                    float rx = 278 + (r - 1) * 122;
                    bool sel = (r == 5);
                    Card(g, rx, 378, 108, 86, sel ? mintBg : Color.White, sel ? green : line, 8f);
                    g.DrawString(r.ToString(), fH1, sel ? bGreen : bInk, rx + 38, 392);
                    g.DrawString(r == 1 ? "Not at all" : r == 5 ? "Very much" : "", fSmall, bMut, rx + 16, 440);
                }
                g.DrawString("Recorded as R1 (stated_priority): 5 / 5 \u00B7 Approved concept stimulus displayed.", fBold, bGreen, 278, 492);

                Card(g, 278, 536, 604, 295, Color.White, line, 8f);
                g.DrawString("Strict Participant Blinding Guardrails", fH3, bInk, 302, 558);
                g.DrawString("\u2022 Starting hypotheses, expected information gain (EIG), and rival explanations are never sent to the browser in participant mode.\n\u2022 Every question has a single-use cryptographic nonce.\n\u2022 Replayed or out-of-order responses are rejected before updating state.", fBody, bMut, new RectangleF(302, 594, 556, 190));

                Card(g, 940, 232, 730, 630, Color.White, green, 10f);
                Pill(g, "Muse Spark 1.3 \u00B7 POST /v1/responses \u00B7 input_video (<= 60s WebM/MP4)", 968, 254, mintBg, green, fMono);
                g.DrawString("Participant-Reviewed Task Recording", fH2, bInk, 968, 294);
                g.DrawString("Muse Spark inspects the screen clip and proposes timestamped visible events. Only events confirmed by the participant enter the research record; raw video is never saved.", fBody, bMut, new RectangleF(968, 330, 674, 65));

                Card(g, 968, 404, 674, 82, mintBg, green, 7f);
                g.DrawString("\u2611 [T1 \u00B7 01.2s] Participant viewed Eco-Van Consolidated slot (Tue 8:00 AM \u2013 12:00 PM, \u00240.00 fee).", fBold, bInk, new RectangleF(986, 420, 640, 55));

                Card(g, 968, 498, 674, 82, mintBg, green, 7f);
                g.DrawString("\u2611 [T2 \u00B7 03.4s] Participant selected Standard 1-Hour Slot (Tue 5:00 PM \u2013 6:00 PM, \u00243.99 fee).", fBold, bInk, new RectangleF(986, 514, 640, 55));

                Card(g, 968, 594, 674, 118, Color.FromArgb(250, 251, 252), line, 7f);
                g.DrawString("Participant correction / note on recording:", fBold, bInk, 986, 610);
                g.DrawString("\"Confirmed T1 and T2. Note: this checkout walkthrough used fictional demonstration data.\"", fBody, bGreen, new RectangleF(986, 640, 640, 58));

                Card(g, 968, 736, 260, 50, green, green, 8f);
                g.DrawString("Confirm & continue \u2192", fH3, Brushes.White, 1002, 749);
            }
            else if (scene == 4) {
                DrawHeader(g, true, 0, "muse-voice-transcribe-1.0 \u00B7 wss://api.meta.ai/v1/asr/realtime + muse-spark-1.3 Probe");
                Card(g, 160, 98, 1600, 804, Color.White, line, 14f);
                g.DrawString("INTERVIEW \u00B7 SPOKEN AI MODERATOR + LIVE MUSE VOICE TRANSCRIBE", fMono, bGreen, 200, 122);
                g.DrawString("\"Think of your most recent online grocery order. Walk me through which delivery slot you picked and what mattered that day.\"", fH2, bInk, new RectangleF(200, 150, 1520, 64));

                Card(g, 200, 224, 540, 340, Color.FromArgb(234, 242, 238), green, 12f);
                Pill(g, "Included 3D AI Moderator (Local Three.js)", 224, 242, Color.White, green, fMono);

                float cx = 470, cy = 395;
                float pulse = (float)(Math.Sin(p * 25.0) * 8.0);
                using (SolidBrush bGlow = new SolidBrush(Color.FromArgb(45, 35, 90, 80)))
                    g.FillEllipse(bGlow, cx - 95 - pulse, cy - 95 - pulse, 190 + pulse * 2, 190 + pulse * 2);
                using (SolidBrush bBody = new SolidBrush(Color.FromArgb(43, 104, 92)))
                    FillRound(g, bBody, cx - 75, cy + 48, 150, 75, 35f);
                using (SolidBrush bHead = new SolidBrush(Color.FromArgb(245, 250, 248)))
                    g.FillEllipse(bHead, cx - 56, cy - 62, 112, 116);
                using (Pen pHead = new Pen(green, 3f))
                    g.DrawEllipse(pHead, cx - 56, cy - 62, 112, 116);
                g.FillEllipse(bGreen, cx - 24, cy - 18, 12, 12);
                g.FillEllipse(bGreen, cx + 12, cy - 18, 12, 12);
                float mouthH = (sub == 0 || sub == 1) ? 6f + (float)Math.Abs(Math.Sin(p * 38.0)) * 14f : 5f;
                using (SolidBrush bMouth = new SolidBrush(green))
                    FillRound(g, bMouth, cx - 18, cy + 14, 36, mouthH, 4f);
                g.DrawString("AI character \u00B7 identified as AI \u00B7 hide anytime", fSmall, bMut, 230, 532);

                Card(g, 768, 224, 952, 340, Color.FromArgb(244, 248, 246), green, 12f);
                using (SolidBrush bOrb = new SolidBrush(green))
                    FillRound(g, bOrb, 796, 248, 52, 52, 12f);
                for (int b = 0; b < 3; b++) {
                    float bh = 12f + (float)Math.Abs(Math.Sin(p * 30.0 + b * 1.2)) * 22f;
                    g.FillRectangle(Brushes.White, 810 + b * 9, 274 - bh / 2f, 4, bh);
                }
                g.DrawString("Muse \u00B7 AI Research Moderator", fH3, bInk, 864, 248);
                string stateText = sub == 0
                    ? "Speaking question aloud via device speech synthesis (microphone off)..."
                    : sub == 1
                    ? "Streaming 16 kHz PCM via wss://api.meta.ai/v1/asr/realtime (ENDPOINTING)..."
                    : "Speech turn complete \u00B7 Transcript reviewed and submitted.";
                g.DrawString(stateText, fBold, bGreen, 864, 276);

                Card(g, 796, 320, 896, 165, Color.White, green, 8f);
                g.DrawString("Live Editable Transcript (muse-voice-transcribe-1.0 \u00B7 never auto-submitted):", fMono, bGreen, 816, 336);
                string fullTranscript = "\"In my fictional order yesterday, I picked standard one-hour delivery because I work until 5 PM and could not leave groceries outside.\"";
                string shownTranscript = sub == 0
                    ? "Waiting for moderator to finish reading question..."
                    : sub == 1
                    ? fullTranscript.Substring(0, Math.Min(fullTranscript.Length, (int)(fullTranscript.Length * Math.Min(1.0f, p * 1.35f)))) + " |"
                    : fullTranscript;
                g.DrawString(shownTranscript, fH3, bInk, new RectangleF(816, 368, 856, 100));

                Card(g, 796, 500, 230, 46, green, green, 7f);
                g.DrawString("Send reviewed answer \u2192", fBold, Brushes.White, 820, 512);
                Card(g, 1042, 500, 235, 46, Color.White, line, 7f);
                g.DrawString("Use sample spoken clip", fBold, bInk, 1066, 512);

                Card(g, 200, 586, 1520, 286, sub == 2 ? mintBg : Color.FromArgb(250, 251, 252), sub == 2 ? green : line, 10f);
                Pill(g, "Muse Spark 1.3 \u00B7 Bounded Adaptive Follow-Up Planner (probe)", 228, 606, Color.White, green, fMono);
                g.DrawString("Adaptive Follow-Up Question Inserted (Probe 1 of 3 max \u00B7 Topic verified: \"Delivery timing & schedule constraints\")", fH3, bInk, 228, 646);
                g.DrawString("Muse Probe P1 (citing R1, R2): \"When you ordered yesterday, would a narrower 1-hour evening window for the consolidated van have worked with your 5 PM schedule, or did other factors matter too?\"", fBody, bInk, new RectangleF(228, 680, 1460, 60));
                Card(g, 228, 748, 1464, 96, Color.White, line, 7f);
                g.DrawString("Participant Answer (R3): \"Yes\u2014if the lower-emission van offered a 1-hour window after 5 PM, that would completely solve my weekday work constraint in this fictional example.\"", fBold, bGreen, new RectangleF(248, 768, 1420, 64));
            }
            else if (scene == 5) {
                DrawHeader(g, true, 0, "muse-spark-1.3 \u00B7 Native Tool Call: select_approved_condition + Member Check (C1)");
                Card(g, 140, 98, 1640, 804, Color.White, line, 14f);
                g.DrawString("CONTROLLED SINGLE-CELL COMPARISON & PARTICIPANT MEMBER CHECK", fMono, bGreen, 180, 122);
                g.DrawString("Testing Competing Explanations via Native Tool Calling", fH1, bInk, 180, 148);

                Card(g, 180, 212, 760, 280, Color.FromArgb(250, 251, 252), line, 10f);
                Pill(g, "Step A \u00B7 Baseline Comparison (CB)", 204, 230, Color.White, ink, fMono);
                g.DrawString("Baseline Table (4-Hour Morning Window vs 1-Hour Evening Slot)", fH3, bInk, 204, 268);
                g.DrawString("\u2022 Eco-Van Consolidated:   Tue 8:00 AM \u2013 12:00 PM   |   \u00240.00 fee\n\u2022 Standard 1-Hour Slot:   Tue 5:00 PM \u2013 6:00 PM     |   \u00243.99 fee", fBody, bInk, new RectangleF(204, 304, 700, 68));
                Card(g, 204, 386, 712, 82, Color.White, line, 7f);
                g.DrawString("Participant Baseline Choice (CB):\n\u25CF Selected \"Standard 1-Hour Slot (Tue 5:00 PM \u2013 6:00 PM, \u00243.99)\"", fBold, bInk, new RectangleF(224, 400, 670, 56));

                Card(g, 972, 212, 768, 280, mintBg, green, 10f);
                Pill(g, "Step B \u00B7 Muse Spark Native Tool Call: select_approved_condition", 996, 230, Color.White, green, fMono);
                g.DrawString("Tool Call Selected Approved Change V1 (Citing R1, R2, R3)", fH3, bInk, 996, 268);
                g.DrawString("\u2022 Eco-Van Consolidated:   Tue 5:00 PM \u2013 6:00 PM [1 CELL CHANGED]  |  \u00240.00\n\u2022 Standard 1-Hour Slot:   Tue 5:00 PM \u2013 6:00 PM [HELD FIXED]          |  \u00243.99", fBold, bGreen, new RectangleF(996, 304, 720, 68));
                Card(g, 996, 386, 720, 82, Color.White, green, 7f);
                g.DrawString("Participant Variant Choice (CV) \u2014 Option Switched!\n\u25CF Selected \"Eco-Van Consolidated (Tue 5:00 PM \u2013 6:00 PM, \u00240.00)\"", fBold, bGreen, new RectangleF(1016, 400, 680, 56));

                Card(g, 180, 516, 1560, 354, Color.White, green, 10f);
                Pill(g, "Final Step (C1) \u00B7 Participant Member Check \u00B7 Supersedes Model Interpretation", 208, 538, mintBg, green, fMono);
                g.DrawString("Muse Spark Tentative Understanding (Addressed to Participant for Correction):", fH3, bInk, 208, 578);
                Card(g, 208, 610, 1504, 86, Color.FromArgb(245, 249, 247), line, 7f);
                g.DrawString("\"My understanding is: In your fictional example, you rated reducing emissions highly (5/5) but chose the standard slot because you work until 5 PM. When the consolidated van offered a 5\u20136 PM window (V1), you switched to the lower-emission option. What should I correct or add?\"", fBody, bInk, new RectangleF(228, 624, 1464, 64));

                Card(g, 208, 710, 1504, 68, Color.White, line, 7f);
                g.DrawString("Participant Correction (C1): \"Accurate summary\u2014please keep the note that this is fictional demonstration data, not a real purchase.\"", fBold, bGreen, 228, 732);

                Card(g, 208, 796, 365, 52, green, green, 8f);
                g.DrawString("Return to Researcher Findings \u2192", fH3, Brushes.White, 238, 809);
            }
            else {
                DrawHeader(g, false, 4, "muse-spark-1.3 \u00B7 Behavioral Science Synthesis & Evidence Triangulation");
                g.DrawString("STEP 4 \u00B7 BEHAVIORAL-SCIENCE-GROUNDED FINDINGS, TRIANGULATION & VERIFICATION", fMono, bGreen, 290, 92);
                g.DrawString("What the evidence supports.", fH1, bInk, 290, 114);

                Card(g, 290, 168, 1566, 204, Color.White, green, 10f);
                Pill(g, "Muse Spark 1.3 Synthesis \u00B7 Grounded in COM-B (Michie et al., 2011) & Intention\u2013Behavior Gap", 316, 184, mintBg, green, fMono);
                g.DrawString("Multi-Layer Evidence Overview & Single-Cell Comparison Audit (1 Completed Session)", fH2, bInk, 316, 220);
                g.DrawString("\u2022 Behavioral Triangulation: High pro-environmental Reflective Motivation (5/5 in S1:R1) diverged from the reported past episode (S1:R2) due to a COM-B Temporal Opportunity constraint (fixed 5 PM workday schedule, S1:P1) rather than low value alignment.\n\u2022 Single-Cell Intervention Audit (V1 \u00B7 Arrival window: Tue 8am\u201312pm \u2192 Tue 5pm\u20136pm, fee & CO2e held fixed): 1 of 1 completed pair switched from Standard Slot to Eco-Van. Participant member-check correction (S1:C1 \u00B7 fictional demo material) preserved.", fBody, bInk, new RectangleF(316, 252, 1514, 110));

                Card(g, 290, 386, 1024, 514, Color.White, line, 10f);
                Pill(g, "Finding 1 \u00B7 COM-B Temporal Opportunity vs. Reflective Motivation \u00B7 Citations: S1:R1, S1:R2, S1:P1, S1:CB, S1:CV, S1:C1", 314, 402, mintBg, green, fSmall);
                g.DrawString("Pro-environmental intention (5/5) was blocked by Temporal Opportunity friction; narrowing the Eco-Van window from 4 hours (daytime) to 1 hour (5\u20136 PM) reversed the choice.", fH3, bInk, new RectangleF(314, 438, 976, 48));
                g.DrawString("\u2022 Behavioral Mechanism (COM-B & Planning Uncertainty): Under Michie et al. (2011), the barrier is Physical/Temporal Opportunity, not Reflective Motivation. Wide 4-hour morning windows impose high waiting & coordination friction (Ellsberg, 1961); aligning arrival with post-work availability (5\u20136 PM) enabled value-consistent choice.\n\u2022 Rival / Competing Explanation: Baseline options also differed on fee (\u00240.00 vs \u00243.99; reference-dependent valuation, Kahneman & Tversky, 1979) and within-session order may create demand effects.\n\u2022 What to Test Next (Falsifiable 2\u00D72 Field Experiment): Cross Window Width (4-hr vs 1-hr evening) \u00D7 Fee Parity (\u00240.00 vs \u00243.99) with randomized default preselection (Dinner et al., 2011) in checkout.", fSmall, bInk, new RectangleF(314, 490, 976, 168));

                Card(g, 314, 662, 976, 222, Color.FromArgb(247, 250, 248), green, 8f);
                g.DrawString("Evidence Triangulation Across 4 Epistemological Layers (Verified Non-Skipped IDs)", fBold, bGreen, 332, 676);
                g.DrawString("[S1:R1 \u00B7 Stated Priority / Reflective Motivation] Rated reducing delivery emissions 5 / 5.\n[S1:R2, S1:P1 \u00B7 Reported Episode / COM-B Opportunity] \"I picked standard 1-hour delivery because I work until 5 PM...\"\n[S1:CB \u2192 S1:CV \u00B7 Controlled Single-Cell Tool Call (V1)] Switched Standard (\u00243.99) \u2192 Eco-Van (\u00240.00) when window narrowed to 5\u20136 PM.\n[S1:C1 \u00B7 Participant Member Check (Epistemic Authority)] \"Accurate summary\u2014please keep the note that this is fictional demo data.\"", fSmall, bInk, new RectangleF(332, 704, 944, 172));

                Card(g, 1334, 386, 522, 514, Color.White, green, 10f);
                Pill(g, "Behavioral & Technical Rigor", 1360, 404, mintBg, green, fMono);
                g.DrawString("Why ChoiceGap Is Verifiable", fH2, bInk, 1360, 440);
                g.DrawString("\u2713 Grounded in COM-B (Michie et al., 2011), Default Effects (Dinner et al., 2011), Planning Uncertainty (Ellsberg, 1961) & Credibility (Hovland & Weiss, 1951)\n\u2713 Triangulates Stated Priorities, Reported Episodes, Single-Cell Comparisons & Member Checks\n\u2713 Zero-finding inconclusive reports supported (never forces a hallucinated mechanism)\n\u2713 154 Python unit tests & 5 JS suites passing\n\u2713 Seeded 2,000-participant Bayesian EIG benchmark:\n   \u2022 Adaptive EIG: 91.60% top-1 recovery\n   \u2022 Fixed baseline: 81.10% (+10.50 pp gain)", fBody, bInk, new RectangleF(1360, 478, 472, 326));

                Card(g, 1360, 822, 470, 58, green, green, 8f);
                g.DrawString("github.com/shiwakshir/choicegap", fH3, Brushes.White, 1435, 837);
            }
        }

        // Apply synchronized spotlight + glowing frame around the exact area being spoken about
        DrawSpotlightAndHighlight(g, step.Fx, step.Fy, step.Fw, step.Fh, step.HighlightLabel, p);
        DrawCursor(g, curX, curY, p > 0.72f);
        DrawCaptionBar(g, step.SceneTitle, step.HighlightLabel, step.Caption, p, elapsedSec, totalSec);
    }

    public static void BuildVideo(string outputPath, StepSpec[] steps, int fps) {
        MFStartup(0x00020070, 0);
        IntPtr sw;
        int hr = MFCreateSinkWriterFromURL(outputPath, IntPtr.Zero, IntPtr.Zero, out sw);
        if (hr < 0) throw new Exception("SinkWriter " + hr);

        Guid MF_MT_MAJOR_TYPE = new Guid("48eba18e-f8c9-4687-bf11-0a74c9f96a8f");
        Guid MF_MT_SUBTYPE = new Guid("f7e34c9a-42e8-4714-b74b-cb29d72c35e5");
        Guid MFMediaType_Video = new Guid("73646976-0000-0010-8000-00AA00389B71");
        Guid MFVideoFormat_H264 = new Guid("34363248-0000-0010-8000-00AA00389B71");
        Guid MFVideoFormat_RGB32 = new Guid("00000016-0000-0010-8000-00AA00389B71");
        Guid MF_MT_AVG_BITRATE = new Guid("20332624-fb0d-4d9e-bd0d-cbf6786c102e");
        Guid MF_MT_INTERLACE_MODE = new Guid("e2724bb8-e676-4806-b4b2-a8d6efb44ccd");
        Guid MF_MT_FRAME_SIZE = new Guid("1652c33d-d6b2-4012-b834-72030849a37d");
        Guid MF_MT_FRAME_RATE = new Guid("c459a2e8-3d2c-4e44-b132-fee5156c7bb0");
        Guid MF_MT_PIXEL_ASPECT_RATIO = new Guid("c6376a1e-8d0a-4027-be45-6d9a0ad39bb6");

        Guid MFMediaType_Audio = new Guid("73647561-0000-0010-8000-00AA00389B71");
        Guid MFAudioFormat_AAC = new Guid("00001610-0000-0010-8000-00aa00389b71");
        Guid MFAudioFormat_PCM = new Guid("00000001-0000-0010-8000-00aa00389b71");
        Guid MF_MT_AUDIO_NUM_CHANNELS = new Guid("37e48bf5-645e-4c5b-89de-ada9e29b696a");
        Guid MF_MT_AUDIO_SAMPLES_PER_SECOND = new Guid("5faeeae7-0290-4c31-9e8a-c534f68d9dba");
        Guid MF_MT_AUDIO_BITS_PER_SAMPLE = new Guid("f2deb57f-40fa-4764-aa33-ed4f2d1ff669");
        Guid MF_MT_AUDIO_AVG_BYTES_PER_SECOND = new Guid("1aab75c8-cfef-451c-ab95-ac034b8e1731");
        Guid MF_MT_AUDIO_BLOCK_ALIGNMENT = new Guid("322de230-9eeb-43bd-ab7a-ff412251541d");

        IntPtr mtOut; MFCreateMediaType(out mtOut);
        SetGUID(mtOut, MF_MT_MAJOR_TYPE, MFMediaType_Video);
        SetGUID(mtOut, MF_MT_SUBTYPE, MFVideoFormat_H264);
        SetUINT32(mtOut, MF_MT_AVG_BITRATE, 5000000);
        SetUINT32(mtOut, MF_MT_INTERLACE_MODE, 2);
        SetUINT64(mtOut, MF_MT_FRAME_SIZE, ((ulong)1920 << 32) | 1080);
        SetUINT64(mtOut, MF_MT_FRAME_RATE, ((ulong)fps << 32) | 1);
        SetUINT64(mtOut, MF_MT_PIXEL_ASPECT_RATIO, ((ulong)1 << 32) | 1);
        uint vStream; VCall<AddStreamDel>(sw, 3)(sw, mtOut, out vStream);

        IntPtr mtIn; MFCreateMediaType(out mtIn);
        SetGUID(mtIn, MF_MT_MAJOR_TYPE, MFMediaType_Video);
        SetGUID(mtIn, MF_MT_SUBTYPE, MFVideoFormat_RGB32);
        SetUINT32(mtIn, MF_MT_INTERLACE_MODE, 2);
        SetUINT64(mtIn, MF_MT_FRAME_SIZE, ((ulong)1920 << 32) | 1080);
        SetUINT64(mtIn, MF_MT_FRAME_RATE, ((ulong)fps << 32) | 1);
        SetUINT64(mtIn, MF_MT_PIXEL_ASPECT_RATIO, ((ulong)1 << 32) | 1);
        VCall<SetInputMediaTypeDel>(sw, 4)(sw, vStream, mtIn, IntPtr.Zero);

        IntPtr aOut; MFCreateMediaType(out aOut);
        SetGUID(aOut, MF_MT_MAJOR_TYPE, MFMediaType_Audio);
        SetGUID(aOut, MF_MT_SUBTYPE, MFAudioFormat_AAC);
        SetUINT32(aOut, MF_MT_AUDIO_NUM_CHANNELS, 1);
        SetUINT32(aOut, MF_MT_AUDIO_SAMPLES_PER_SECOND, 44100);
        SetUINT32(aOut, MF_MT_AUDIO_BITS_PER_SAMPLE, 16);
        SetUINT32(aOut, MF_MT_AUDIO_AVG_BYTES_PER_SECOND, 16000);
        uint aStream; VCall<AddStreamDel>(sw, 3)(sw, aOut, out aStream);

        IntPtr aIn; MFCreateMediaType(out aIn);
        SetGUID(aIn, MF_MT_MAJOR_TYPE, MFMediaType_Audio);
        SetGUID(aIn, MF_MT_SUBTYPE, MFAudioFormat_PCM);
        SetUINT32(aIn, MF_MT_AUDIO_NUM_CHANNELS, 1);
        SetUINT32(aIn, MF_MT_AUDIO_SAMPLES_PER_SECOND, 44100);
        SetUINT32(aIn, MF_MT_AUDIO_BITS_PER_SAMPLE, 16);
        SetUINT32(aIn, MF_MT_AUDIO_BLOCK_ALIGNMENT, 2);
        SetUINT32(aIn, MF_MT_AUDIO_AVG_BYTES_PER_SECOND, 88200);
        VCall<SetInputMediaTypeDel>(sw, 4)(sw, aStream, aIn, IntPtr.Zero);

        VCall<BeginWritingDel>(sw, 5)(sw);

        float totalSec = 0f;
        int[] stepFrames = new int[steps.Length];
        for (int i = 0; i < steps.Length; i++) {
            float sec = (float)steps[i].AudioPcm44k.Length / 88200f;
            stepFrames[i] = Math.Max(fps, (int)Math.Round(sec * fps));
            totalSec += (float)stepFrames[i] / fps;
        }

        long frameDurHns = 10000000L / fps;
        long videoTimeHns = 0;
        long audioTimeHns = 0;
        int globalFrame = 0;
        float prevCx = 960f, prevCy = 540f;

        using (Bitmap bmp = new Bitmap(1920, 1080, PixelFormat.Format32bppRgb)) {
            byte[] rawBytes = new byte[1920 * 1080 * 4];
            for (int s = 0; s < steps.Length; s++) {
                StepSpec st = steps[s];
                long aDurHns = (long)((double)st.AudioPcm44k.Length / 88200.0 * 10000000.0);
                WriteBuffer(sw, aStream, st.AudioPcm44k, audioTimeHns, aDurHns);
                audioTimeHns += aDurHns;

                int count = stepFrames[s];
                for (int f = 0; f < count; f++) {
                    float p = count > 1 ? (float)f / (count - 1) : 1f;
                    float moveT = Math.Min(1f, p * 3.0f);
                    // Smooth ease-out cursor glide toward the highlighted element
                    float ease = 1f - (float)Math.Pow(1.0 - moveT, 3.0);
                    float curX = prevCx + (st.Cx - prevCx) * ease;
                    float curY = prevCy + (st.Cy - prevCy) * ease;
                    float elapsedSec = (float)globalFrame / fps;

                    using (Graphics g = Graphics.FromImage(bmp)) {
                        RenderFrame(g, st, p, curX, curY, elapsedSec, totalSec);
                    }
                    bmp.RotateFlip(RotateFlipType.RotateNoneFlipY);
                    BitmapData bd = bmp.LockBits(new Rectangle(0, 0, 1920, 1080), ImageLockMode.ReadOnly, PixelFormat.Format32bppRgb);
                    Marshal.Copy(bd.Scan0, rawBytes, 0, rawBytes.Length);
                    bmp.UnlockBits(bd);

                    WriteBuffer(sw, vStream, rawBytes, videoTimeHns, frameDurHns);
                    videoTimeHns += frameDurHns;
                    globalFrame++;
                }
                prevCx = st.Cx;
                prevCy = st.Cy;
            }
        }

        hr = VCall<FinalizeDel>(sw, 11)(sw);
        if (hr < 0) throw new Exception("Finalize " + hr);
        Marshal.Release(sw);
        MFShutdown();
    }
}
"@

Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing

function Synthesize-WinRtSegment($voice, [string]$ssmlBody, [int]$padMs = 350) {
    $synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
    $synth.Voice = $voice
    $lang = $voice.Language
    # Pure native voice output: no <prosody> pitch or rate warping
    $ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='$lang'>$ssmlBody</speak>"
    $stream = Await-WinRt ($synth.SynthesizeSsmlToStreamAsync($ssml)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
    $netStream = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($stream)
    $ms = New-Object System.IO.MemoryStream
    $netStream.CopyTo($ms)
    $wavBytes = $ms.ToArray()
    return [DemoVideoV2]::ConvertWavTo44kPcm($wavBytes, $padMs)
}

$rawSteps = @(
    # Scene 0 (Overview)
    @{ Scene=0; Sub=0; Title="SCENE 1 / 7 - THE PROBLEM & ARCHITECTURE"; Label="THE UX RESEARCH BOTTLENECK";
       Rect=@(120, 268, 810, 175); Cur=@(520, 360); Voice=$voiceMark;
       Caption="Static surveys tell you what users click, but miss the why. Human UX interviews don't scale, and unguarded AI chatbots hallucinate findings.";
       Ssml="Static surveys show what users click, <break time='180ms'/> but miss the why. <break time='180ms'/> Interviews don't scale, and unguarded chatbots hallucinate." },
    @{ Scene=0; Sub=1; Title="SCENE 1 / 7 - THE PROBLEM & ARCHITECTURE"; Label="VERIFIABLE AGENT LOOP";
       Rect=@(960, 268, 840, 175); Cur=@(1380, 360); Voice=$voiceMark;
       Caption="Meet ChoiceGap: a brief-led adaptive survey and verifiable AI-moderated research studio built on the Meta Muse stack.";
       Ssml="Meet ChoiceGap: <break time='180ms'/> an adaptive survey and research studio built on Meta Muse, where code audits every model decision." },
    @{ Scene=0; Sub=2; Title="SCENE 1 / 7 - THE PROBLEM & ARCHITECTURE"; Label="6 META MODEL API INTEGRATIONS";
       Rect=@(114, 462, 1692, 378); Cur=@(960, 640); Voice=$voiceMark;
       Caption="Combines Muse Spark 1.3 (web_search, strict JSON, input_video, tool calling), Muse Image 1.0, and realtime Muse Voice Transcribe 1.0.";
       Ssml="It connects Muse Spark 1.3 for web search, study design, video review, and tool calling, <break time='180ms'/> with Muse Image and Muse Voice." },

    # Scene 1 (Step 1: Brief, Web Search, Muse Image)
    @{ Scene=1; Sub=0; Title="SCENE 2 / 7 - STEP 1: BRIEF, GROUNDING & MUSE IMAGE"; Label="RESEARCH BRIEF & HYPOTHESES";
       Rect=@(310, 194, 720, 180); Cur=@(640, 290); Voice=$voiceMark;
       Caption="In Step 1, a researcher loads a sustainability brief: why do grocery shoppers who value lower emissions still pick conventional delivery?";
       Ssml="In Step 1, we enter a research brief: <break time='180ms'/> why do shoppers who value lower emissions still pick standard delivery?" },
    @{ Scene=1; Sub=1; Title="SCENE 2 / 7 - STEP 1: BRIEF, GROUNDING & MUSE IMAGE"; Label="MUSE SPARK 1.3 - NATIVE WEB_SEARCH GROUNDING";
       Rect=@(310, 382, 720, 252); Cur=@(660, 520); Voice=$voiceMark;
       Caption="Muse Spark 1.3 runs native web_search grounding via POST /v1/responses, validating inline URL citations and locking a SHA-256 brief digest.";
       Ssml="First, Muse Spark runs native web search grounding, <break time='180ms'/> validating source links and locking a brief digest." },
    @{ Scene=1; Sub=2; Title="SCENE 2 / 7 - STEP 1: BRIEF, GROUNDING & MUSE IMAGE"; Label="MUSE IMAGE 1.0 - CONCEPT GENERATION & EDITING";
       Rect=@(1096, 192, 742, 622); Cur=@(1450, 520); Voice=$voiceMark;
       Caption="Muse Image 1.0 (/v1/images/generations & /edits) generates and revises a fictional checkout concept stimulus for researcher review.";
       Ssml="Next, Muse Image 1.0 generates and edits a checkout card <break time='180ms'/> comparing a four-hour morning Eco-Van with a one-hour evening slot." },

    # Scene 2 (Step 2: Study Design, Comparison Matrix, Approval)
    @{ Scene=2; Sub=0; Title="SCENE 3 / 7 - STEP 2: STUDY DESIGN & APPROVAL"; Label="RESEARCHER INPUT: ADD, REMOVE & EDIT QUESTIONS";
       Rect=@(290, 178, 770, 720); Cur=@(650, 480); Voice=$voiceMark;
       Caption="In Step 2, researchers have full editorial input: add, remove, reorder, or edit questions and types, while locking approved follow-up topics.";
       Ssml="In Step 2, researchers maintain full editorial control to add, remove, reorder, or edit questions, while locking approved follow-up topics." },
    @{ Scene=2; Sub=1; Title="SCENE 3 / 7 - STEP 2: STUDY DESIGN & APPROVAL"; Label="AUDITED SINGLE-CELL COMPARISON MATRIX (V1)";
       Rect=@(1108, 270, 724, 218); Cur=@(1460, 360); Voice=$voiceMark;
       Caption="Under comparison tasks, Muse drafts a baseline table and approved single-cell variants, like narrowing only the Eco-Van window to 5:00 PM.";
       Ssml="For comparison tasks, Muse drafts a baseline table and single-cell variants, <break time='180ms'/> like narrowing only the Eco-Van window to five P M." },
    @{ Scene=2; Sub=2; Title="SCENE 3 / 7 - STEP 2: STUDY DESIGN & APPROVAL"; Label="3D AI MODERATOR & IMMUTABLE PUBLICATION";
       Rect=@(1108, 508, 724, 280); Cur=@(1280, 742); Voice=$voiceMark;
       Caption="The researcher enables spoken moderation with the local 3D AI character, confirms review, and locks an immutable published study.";
       Ssml="The researcher enables spoken moderation with the 3D character, confirms review, and publishes an immutable study snapshot." },

    # Scene 3 (Participant View: Blinded Survey & Video Task Review)
    @{ Scene=3; Sub=0; Title="SCENE 4 / 7 - PARTICIPANT VIEW & VIDEO TASK REVIEW"; Label="BLINDED PARTICIPANT SURVEY (R1)";
       Rect=@(244, 226, 672, 642); Cur=@(780, 420); Voice=$voiceMark;
       Caption="Switching to Participant View in one click, researcher hypotheses remain completely blind as the participant rates emissions 5 out of 5.";
       Ssml="Switching to Participant View in one click, hypotheses stay blind <break time='180ms'/> as the participant rates lower emissions five out of five." },
    @{ Scene=3; Sub=1; Title="SCENE 4 / 7 - PARTICIPANT VIEW & VIDEO TASK REVIEW"; Label="MUSE SPARK 1.3 - VIDEO UNDERSTANDING (input_video)";
       Rect=@(934, 226, 742, 642); Cur=@(1100, 760); Voice=$voiceMark;
       Caption="Muse Spark video understanding (POST /v1/responses + input_video) extracts timestamped visible task events for participant confirmation.";
       Ssml="In optional task review, Muse Spark video understanding extracts timestamped task events for participant confirmation." },

    # Scene 4 (3D AI Moderator + Realtime Muse Voice Transcribe + Probe)
    @{ Scene=4; Sub=0; Title="SCENE 5 / 7 - 3D AI MODERATOR & MUSE VOICE TRANSCRIBE"; Label="3D AI MODERATOR SPEAKING INTERVIEW QUESTION";
       Rect=@(194, 218, 552, 352); Cur=@(470, 395); Voice=$voiceHazel;
       Caption="3D AI Moderator (speaking question aloud): 'Walk me through which delivery slot you picked on your last order, and what mattered that day.'";
       Ssml="Now our 3D Moderator asks the interview question: <break time='220ms'/> Walk me through which delivery slot you picked on your last order, and what mattered that day." },
    @{ Scene=4; Sub=1; Title="SCENE 5 / 7 - 3D AI MODERATOR & MUSE VOICE TRANSCRIBE"; Label="MUSE VOICE TRANSCRIBE 1.0 - REALTIME WSS STREAMING";
       Rect=@(762, 218, 964, 352); Cur=@(910, 522); Voice=$voiceGeorge;
       Caption="Participant spoken response streamed to Muse Voice Transcribe 1.0 (wss://api.meta.ai/v1/asr/realtime) for review before sending.";
       Ssml="In my fictional order yesterday, I picked the five P M slot because I work all day. <break time='200ms'/> Muse Voice Transcribe streams this live for review." },
    @{ Scene=4; Sub=2; Title="SCENE 5 / 7 - 3D AI MODERATOR & MUSE VOICE TRANSCRIBE"; Label="MUSE SPARK 1.3 - BOUNDED ADAPTIVE PROBE (P1)";
       Rect=@(194, 580, 1532, 296); Cur=@(860, 790); Voice=$voiceMark;
       Caption="Once submitted, Muse Spark 1.3 dynamically inserts a bounded follow-up probe (P1) verified against approved follow-up topics.";
       Ssml="Once submitted, Muse Spark dynamically asks a bounded follow-up probe from our approved topics to explore that evening schedule." },

    # Scene 5 (Native Tool Calling & Member Check C1)
    @{ Scene=5; Sub=0; Title="SCENE 6 / 7 - NATIVE TOOL CALLING & MEMBER CHECK"; Label="BASELINE HYPOTHETICAL COMPARISON (CB)";
       Rect=@(174, 206, 772, 292); Cur=@(540, 425); Voice=$voiceMark;
       Caption="On the baseline comparison table (CB), where the Eco-Van only offers a 4-hour morning window, the participant selects the Standard 5-6 PM slot.";
       Ssml="On the baseline comparison table, where the Eco-Van only offers a morning window, the participant picks the standard five P M slot." },
    @{ Scene=5; Sub=1; Title="SCENE 6 / 7 - NATIVE TOOL CALLING & MEMBER CHECK"; Label="MUSE SPARK NATIVE TOOL CALL - select_approved_condition";
       Rect=@(966, 206, 780, 292); Cur=@(1350, 425); Voice=$voiceMark;
       Caption="Muse Spark calls select_approved_condition to test V1 (changing ONLY Eco-Van window to 5-6 PM), and the participant switches to Eco-Van!";
       Ssml="Muse Spark then calls select approved condition to test a five P M Eco-Van slot, <break time='180ms'/> and the participant switches to the Eco-Van." },
    @{ Scene=5; Sub=2; Title="SCENE 6 / 7 - NATIVE TOOL CALLING & MEMBER CHECK"; Label="PARTICIPANT MEMBER CHECK (C1) & ONE-CLICK RETURN";
       Rect=@(174, 510, 1572, 366); Cur=@(390, 822); Voice=$voiceMark;
       Caption="In the final member check (C1), Muse shares its tentative summary for participant correction before returning to Researcher Findings.";
       Ssml="Before finishing, Muse shares its tentative summary so the participant can confirm or correct it." },

    # Scene 6 (Findings & Verification - Grounded in Behavioral Science)
    @{ Scene=6; Sub=0; Title="SCENE 7 / 7 - BEHAVIORAL SCIENCE FINDINGS & VERIFICATION"; Label="COM-B & BEHAVIORAL SCIENCE SYNTHESIS";
       Rect=@(280, 162, 1586, 214); Cur=@(920, 270); Voice=$voiceMark;
       Caption="Back in Researcher Findings, Muse Spark synthesizes findings under COM-B: distinguishing Temporal Opportunity barriers from Reflective Motivation.";
       Ssml="Back in Researcher Findings, Muse Spark synthesizes findings grounded in COM-B, distinguishing temporal opportunity barriers from reflective motivation." },
    @{ Scene=6; Sub=1; Title="SCENE 7 / 7 - BEHAVIORAL SCIENCE FINDINGS & VERIFICATION"; Label="4-LAYER EVIDENCE TRIANGULATION (S1:R1 .. S1:C1)";
       Rect=@(280, 380, 1044, 524); Cur=@(780, 720); Voice=$voiceMark;
       Caption="Every finding triangulates Stated Priority, Reported Episodes, Controlled Single-Cell Tool Calls, and Participant Corrections with exact citations.";
       Ssml="Findings triangulate stated priority, reported episodes, controlled single-cell comparisons, and participant member checks." },
    @{ Scene=6; Sub=2; Title="SCENE 7 / 7 - BEHAVIORAL SCIENCE FINDINGS & VERIFICATION"; Label="FALSIFIABLE INTERVENTIONS & RIGOR AUDIT";
       Rect=@(1324, 380, 542, 524); Cur=@(1590, 840); Voice=$voiceMark;
       Caption="Proposes falsifiable 2x2 field experiments, backed by 154 Python unit tests, 5 JS test suites, and a 91.6% Bayesian benchmark.";
       Ssml="Each finding proposes a falsifiable experiment, backed by 154 unit tests and a 91.6 percent Bayesian benchmark." }
)

$stepSpecs = New-Object StepSpec[] $rawSteps.Count
$totalDurationSec = 0.0

for ($i = 0; $i -lt $rawSteps.Count; $i++) {
    $r = $rawSteps[$i]
    $pcm = Synthesize-WinRtSegment $r.Voice $r.Ssml 350
    $spec = New-Object StepSpec
    $spec.Scene = $r.Scene
    $spec.SubStep = $r.Sub
    $spec.SceneTitle = $r.Title
    $spec.HighlightLabel = $r.Label
    $spec.Caption = $r.Caption
    $spec.Fx = [float]$r.Rect[0]
    $spec.Fy = [float]$r.Rect[1]
    $spec.Fw = [float]$r.Rect[2]
    $spec.Fh = [float]$r.Rect[3]
    $spec.Cx = [float]$r.Cur[0]
    $spec.Cy = [float]$r.Cur[1]
    $spec.AudioPcm44k = $pcm
    $stepSpecs[$i] = $spec
    $sec = [math]::Round($pcm.Length / 88200.0, 2)
    $totalDurationSec += $sec
    Write-Output "Step $($i+1)/$($rawSteps.Count) [$($r.Label)]: $sec s"
}

Write-Output "Total video duration: $([math]::Round($totalDurationSec, 1)) seconds"
$outMp4 = "C:\Users\HP\.gemini\antigravity\scratch\choicegap\choicegap-hackathon-demo.mp4"
if (Test-Path $outMp4) { Remove-Item $outMp4 -Force }
Write-Output "Encoding 1080p H.264 + AAC MP4 with synchronized spotlights to $outMp4 ..."
[DemoVideoV2]::BuildVideo($outMp4, $stepSpecs, 12)
Get-Item $outMp4 | Select-Object FullName, Length

