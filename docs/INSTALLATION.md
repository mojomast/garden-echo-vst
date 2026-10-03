# Install a Garden Echo VST3 candidate

These instructions describe the experimental native packages. Use only a
candidate whose platform checks have actually passed; source availability or a
successful build on another OS is not proof of compatibility with your host.

## Pick the correct download

| Your system | Package target |
|---|---|
| Linux on an Intel/AMD 64-bit CPU | `linux-x86_64` |
| Windows using a 64-bit Intel/AMD host | `windows-x64` |
| Intel or Apple Silicon Mac | `macos-universal` |

VST3 is a common interface, not portable machine code. A `.vst3` folder contains
an OS-specific module. The macOS universal bundle contains **two Mac CPU slices**;
it does not contain the Linux or Windows module. Renaming a file cannot convert it.

Download the binary ZIP and its `.sha256` sidecar from the published release.
The `-source.zip` is corresponding source, not the installable plugin. Verify
the checksum, extract the binary ZIP, then copy the complete `Garden Echo.vst3`
folder—not just the internal `.so`, DLL or Mach-O file.

Before upgrading, close the host, back up a test session and remove only the old
installed **Garden Echo.vst3** bundle. Do not merge new files into a stale bundle.
Saved settings remain in your DAW project; do not delete other plugins or host data.

## Linux x86_64

Copy the bundle to `~/.vst3/`, then rescan VST3 plugins in your host. Check the
release's measured GLIBC requirement before installing on an older distribution.
The existing Linux review module requires symbols through `GLIBC_2.38`; that is
not a guarantee of compatibility with every distribution.

## Windows x64

Copy the bundle to `C:\Program Files\Common Files\VST3\`. This system-wide
location may require administrator permission. A configured per-user location
is an alternative only when your host supports scanning it. Use a 64-bit host
and rescan its VST3 plugin list after installation.

If loading reports missing `VCRUNTIME` or `MSVCP` DLLs, install the supported
**x64 Microsoft Visual C++ Redistributable** from Microsoft, not an arbitrary
DLL-download site: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist .
No Microsoft runtime installer is bundled here.

## macOS universal

Copy the bundle to `~/Library/Audio/Plug-Ins/VST3/`, then rescan in a VST3-capable
host. The experimental package is not Developer ID signed or notarized; an
ad-hoc signature does not establish Apple notarization. Gatekeeper or the host
may block it. Do not disable system security globally or blindly clear quarantine
attributes. A signed/notarized distribution is a separate release step.

**Logic Pro and GarageBand use Audio Units, not VST3.** This VST3 package is not
an AU; a separate AU build and validation would be needed for those hosts.

## First check and removal

1. Rescan, insert Garden Echo on a mono/stereo test track and start playback.
2. Select Leaf Chamber, then a study. Check Wet/Dry and bypass with modest levels.
3. Save, close and reopen a test project before trusting important sessions.
4. Report the OS/CPU, host version, package checksum and exact failure steps.
   Redact personal paths and do not attach unlicensed audio or credentials.

To uninstall, close the host and remove only the installed `Garden Echo.vst3`
folder from the same location, then rescan. Native CTest/pluginval results do
not replace physical listening, device testing or validation in your own DAW.
