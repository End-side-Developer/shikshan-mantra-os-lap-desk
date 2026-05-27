# Calamares Shikshan Branding Bundle

This directory contains the Calamares installer branding assets for **Shikshan Mantra OS**.

At build time, live-build stages the entire tree into the chroot under
`/usr/share/shikshan/branding/calamares/shikshan/`.
Hook `0032-calamares-branding.hook.chroot` then copies everything into
`/etc/calamares/branding/shikshan/`, which is the path that
`config/includes.chroot/etc/calamares/settings.conf` (`branding: shikshan`) points at.

## Directory Layout

```text
shikshan/
├── branding.desc          # Calamares descriptor — product strings, colours, image refs
├── logo.svg               # Primary project mark (256×256 viewBox, Shikshan Mantra symbol)
├── welcome.svg            # Welcome-screen imagery  [PLACEHOLDER — see below]
├── slideshow/
│   ├── show.qml           # slideshowAPI 2 QML presentation
│   └── slide1.svg         # First slide artwork     [PLACEHOLDER — see below]
└── README.md              # This file
```

## Asset details

| File | Source | License |
|------|--------|---------|
| `logo.svg` | Authored in-house (`branding/logo/shikshan-mantra.svg`) | Project-owned |
| `welcome.svg` | **Inline placeholder** — simple grey circle SVG generated for CI testing | N/A (replace before production) |
| `slideshow/slide1.svg` | **Inline placeholder** — simple blue rectangle SVG generated for CI testing | N/A (replace before production) |

## Placeholder notes

`welcome.svg` and `slideshow/slide1.svg` are minimal inline SVGs created **for build and CI testing only**.
They satisfy the SVG-only constraint and the `xmlns="http://www.w3.org/2000/svg"` test.
They must be replaced with final in-house artwork before the OS ships publicly.

## How to replace placeholders

1. Obtain final SVG files from the design team.
2. Replace `welcome.svg` and `slideshow/slide1.svg` with the new assets.
3. Ensure every replacement:
   - Is a valid SVG (`<?xml ...?>` header + `<svg xmlns="http://www.w3.org/2000/svg" ...>`)
   - Contains **no raster elements** (no `<image href="*.png">` etc.)
   - Has an appropriate `viewBox` — recommended `0 0 800 520` for welcome/slides
4. Run `bash tests/build/test_calamares_branding.sh` from the repo root.
5. Mirror the new files into
   `config/includes.chroot/usr/share/shikshan/branding/calamares/shikshan/`
   (same relative structure).

## Runtime install path

```text
/etc/calamares/branding/shikshan/
├── branding.desc
├── logo.svg
├── welcome.svg
└── slideshow/
    ├── show.qml
    └── slide1.svg
```

This path is written by hook `0032-calamares-branding.hook.chroot` during the live chroot build.
