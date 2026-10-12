# Volume Controller NEO (patcher)

Builds **Volume Controller NEO** — Elgato's Volume Controller Stream Deck plugin
with **Stream Deck Neo** support and redesigned keys — from **your own** copy of
the official plugin.

This repository contains **no Elgato code or assets**. It holds only the changes
(as patches), a manifest and a build script; the plugin is assembled locally from
the Volume Controller you installed from the Elgato Marketplace.

## Features

- **Auto Software Detection on the Neo.** The Neo has 2 rows and no dials, so the
  auto layout puts one app per row — `[Back][Mute][Vol−][Vol+]` /
  `[Next][Mute][Vol−][Vol+]` — and *Next* wraps around. Vol−/Vol+ draw a
  horizontal fader across the two keys.
- **Redesigned Manual Software Detection keys**, with a **Style** per key: *Default*
  (stock Stream Deck look, original app icons) or *Duotone* (flat two-tone style of
  the *Duotone Essentials* icon pack: blue / orange / purple / red presets or custom
  colours, app icons recoloured to match). Keys turn red when the app is muted,
  `100%` reads `MAX`, long names are cut to fit.
- **[VolumeProxy](https://github.com/XenSide/VolumeProxy) integration:** bundles and
  starts `Foreground.exe` (one copy only, run from `%LOCALAPPDATA%\VolumeProxy`),
  always offers "Foreground" in the app picker, and keys set to it show the icon and
  name of the focused app. Focus changes come from a Windows event hook in a worker
  thread, so nothing is polled.
- **Two-key widgets:** an adjacent Vol+ / Vol− pair for the same app is drawn as
  one control spanning both keys — vertical when stacked, horizontal side by side.
- **Back To Profile** keeps working after a plugin restart.
- Runs under its own ID (`com.xenside.volumecontroller`), next to — or instead of —
  the official plugin.

## Requirements

- Windows, Stream Deck 6.5+
- **Volume Controller 2.0.4.196** installed from the Elgato Marketplace (it also
  installs the Audio Router, `ElgatoAudioControlServer.exe`, which this plugin uses)
- Python 3.9+ and Node.js (for `npx js-beautify` and `npm install koffi`)

[VolumeProxy](https://github.com/XenSide/VolumeProxy)'s `Foreground.exe` is included
(`template/bin/`) and always bundled. To use your own build instead, pass
`--volumeproxy path\to\Foreground.exe`.

## Build & install

```
python patch.py --install
```

This reads the official plugin from
`%APPDATA%\Elgato\StreamDeck\Plugins\com.elgato.volume-controller.sdPlugin`
(override with `--source`), writes the result to `out/`, and opens the
`.streamDeckPlugin` package so Stream Deck installs it (accept the prompt — this
is also how the Neo auto profile gets imported).

Optional: once your keys use the NEO actions you can remove the official plugin by
deleting its folder from `%APPDATA%\Elgato\StreamDeck\Plugins\`. Don't uninstall it
through Stream Deck — that may also remove the Audio Router.

## How it works

1. Copies the official plugin and pretty-prints its bundle with
   `js-beautify@1.15.1` (pinned, so the output is reproducible).
2. Renames the plugin ID so it is a separate, non-Marketplace plugin (no
   integrity check).
3. Applies `patches/*.patch`.
4. Adds a plain-text `manifest.json` and the plugin's own files (`template/`), and
   generates the Neo auto profile.
5. Installs `koffi` (pinned) with npm. VolumeProxy comes from `template/bin` (or
   `--volumeproxy`).
6. Packs `out/com.xenside.volumecontroller.streamDeckPlugin`.

If Elgato ships a new plugin version the patches may stop applying; the script
then tells you which hunk failed.

## License

The code in this repository (patches, script, manifest) is MIT licensed — see
`LICENSE`. Volume Controller itself is © Elgato / Corsair and is not included.
