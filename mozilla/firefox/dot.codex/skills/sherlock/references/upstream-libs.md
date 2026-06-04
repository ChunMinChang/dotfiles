# Firefox Third-Party Media Library Upstream Mapping

## How to Use

1. Identify the library from the file path (e.g., `media/libvpx/...` → libvpx)
2. Read the vendored revision from moz.yaml:
   ```bash
   git show HEAD:<moz_yaml_path> | grep -E '(revision|release):'
   ```
3. Construct the permanent link using the forge URL pattern from source-permalinks.md

## Library Table

| Library | Firefox Path | moz.yaml | Upstream Repo | Forge | Link Template |
|---------|-------------|----------|---------------|-------|---------------|
| libvpx | media/libvpx | media/libvpx/moz.yaml | chromium.googlesource.com/webm/libvpx | googlesource | `https://chromium.googlesource.com/webm/libvpx/+/{hash}/{path}#{line}` |
| libaom | media/libaom | media/libaom/moz.yaml | aomedia.googlesource.com/aom | googlesource | `https://aomedia.googlesource.com/aom/+/{hash}/{path}#{line}` |
| libdav1d | media/libdav1d | media/libdav1d/moz.yaml | code.videolan.org/videolan/dav1d | gitlab | `https://code.videolan.org/videolan/dav1d/-/blob/{hash}/{path}#L{line}` |
| libopus | media/libopus | media/libopus/moz.yaml | gitlab.xiph.org/xiph/opus | gitlab | `https://gitlab.xiph.org/xiph/opus/-/blob/{hash}/{path}#L{line}` |
| libvorbis | media/libvorbis | media/libvorbis/moz.yaml | gitlab.xiph.org/xiph/vorbis | gitlab | `https://gitlab.xiph.org/xiph/vorbis/-/blob/{hash}/{path}#L{line}` |
| libogg | media/libogg | media/libogg/moz.yaml | gitlab.xiph.org/xiph/ogg | gitlab | `https://gitlab.xiph.org/xiph/ogg/-/blob/{hash}/{path}#L{line}` |
| libnestegg | media/libnestegg | media/libnestegg/moz.yaml | github.com/mozilla/nestegg | github | `https://github.com/mozilla/nestegg/blob/{hash}/{path}#L{line}` |
| libpng | media/libpng | media/libpng/moz.yaml | github.com/pnggroup/libpng | github | `https://github.com/pnggroup/libpng/blob/{hash}/{path}#L{line}` |
| libwebp | media/libwebp | media/libwebp/moz.yaml | github.com/webmproject/libwebp | github | `https://github.com/webmproject/libwebp/blob/{hash}/{path}#L{line}` |
| libyuv | media/libyuv | media/libyuv/moz.yaml | chromium.googlesource.com/libyuv/libyuv | googlesource | `https://chromium.googlesource.com/libyuv/libyuv/+/{hash}/{path}#{line}` |
| libjpeg-turbo | media/libjpeg | media/libjpeg/moz.yaml | github.com/libjpeg-turbo/libjpeg-turbo | github | `https://github.com/libjpeg-turbo/libjpeg-turbo/blob/{hash}/{path}#L{line}` |
| libcubeb | media/libcubeb | media/libcubeb/moz.yaml | github.com/mozilla/cubeb | github | `https://github.com/mozilla/cubeb/blob/{hash}/{path}#L{line}` |
| libsoundtouch | media/libsoundtouch | media/libsoundtouch/moz.yaml | codeberg.org/soundtouch/soundtouch | codeberg | `https://codeberg.org/soundtouch/soundtouch/src/commit/{hash}/{path}#L{line}` |
| speexdsp | media/libspeex_resampler | media/libspeex_resampler/moz.yaml | gitlab.xiph.org/xiph/speexdsp | gitlab | `https://gitlab.xiph.org/xiph/speexdsp/-/blob/{hash}/{path}#L{line}` |
| ffvpx | media/ffvpx | media/ffvpx/moz.yaml | github.com/FFmpeg/FFmpeg | github | `https://github.com/FFmpeg/FFmpeg/blob/{hash}/{path}#L{line}` |
| mp4parse-rust | media/mp4parse-rust | — (see Cargo.toml) | github.com/mozilla/mp4parse-rust | github | `https://github.com/mozilla/mp4parse-rust/blob/{hash}/{path}#L{line}` |
| libwebrtc | third_party/libwebrtc | third_party/libwebrtc/moz.yaml | webrtc.googlesource.com/src | googlesource | `https://webrtc.googlesource.com/src/+/{hash}/{path}#{line}` |
| libsrtp | netwerk/srtp/src | netwerk/srtp/src/moz.yaml | github.com/cisco/libsrtp | github | `https://github.com/cisco/libsrtp/blob/{hash}/{path}#L{line}` |

## Notes

- For Rust crates (mp4parse-rust), the revision is in `Cargo.toml` under `[dependencies]`, not in a moz.yaml file.
- ffvpx is a Firefox-customized fork of FFmpeg. Use the GitHub mirror `github.com/FFmpeg/FFmpeg` for upstream references.
- Some libraries store source in `third_party/` rather than `media/`.
- Firefox may apply local patches on top of vendored libraries. Check for `.patch` files or diffs from the upstream revision.

## Library Test Frameworks

For creating standalone tests in upstream repos (Step T3 of third-party workflow):

| Library | Build System | Test Framework | Test Command |
|---------|-------------|----------------|--------------|
| libaom | CMake | googletest | `cmake -B build && cmake --build build && ctest --test-dir build` |
| libvpx | CMake/configure | googletest | `./configure && make test` |
| libdav1d | meson | custom harness | `meson setup build && ninja -C build test` |
| libopus | CMake/autotools | custom | `cmake -B build && cmake --build build && ctest --test-dir build` |
| FFmpeg | configure + make | FATE suite | `./configure && make fate` |
| libwebrtc | gn/ninja | googletest | `gn gen out/Default && ninja -C out/Default` |
| libcubeb | CMake | googletest | `cmake -B build && cmake --build build && ctest --test-dir build` |
