# General
alias mb='./mach build'
alias mr='./mach run'
alias mc='./mach clobber'
alias mfb='mfmt && mb'
# WebCodecs VideoFrame
alias vf1='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-construction.any.js'
alias vf2='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-construction.window.js'
alias vf3='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-construction.crossOriginIsolated.https.any.js'
alias vf4='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-construction.crossOriginSource.sub.html'
alias vf5='./mach wpt testing/web-platform/tests/webcodecs/video-frame-serialization.any.js'
alias vf6='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-serialization.crossAgentCluster.https.html'
alias vf7='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-createImageBitmap.https.any.js'
alias vf8='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-canvasImageSource.html'
alias vf9='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-copyTo.any.js'
alias vf10='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-copyTo.crossOriginIsolated.https.any.js'
alias vf11='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-copyTo-rgb.any.js'
# WebCodecs VideoDecoder
alias vd1='./mach wpt testing/web-platform/tests/webcodecs/encoded-video-chunk.any.js'
alias vd2='./mach wpt testing/web-platform/tests/webcodecs/encoded-video-chunk.crossOriginIsolated.https.any.js'
alias vd3='./mach wpt testing/web-platform/tests/webcodecs/encodedVideoChunk-serialization.crossAgentCluster.https.html'
alias vd4='./mach wpt testing/web-platform/tests/webcodecs/chunk-serialization.any.js'
alias vd5='./mach wpt testing/web-platform/tests/webcodecs/video-decoder.https.any.js'
alias vd6='./mach wpt testing/web-platform/tests/webcodecs/video-decoder.crossOriginIsolated.https.any.js'
alias vd7='./mach wpt testing/web-platform/tests/webcodecs/videoDecoder-codec-specific.https.any.js'
# WebCodecs VideoEncoder
alias ve1='./mach wpt testing/web-platform/tests/webcodecs/video-encoder-config.https.any.js'
alias ve2='./mach wpt testing/web-platform/tests/webcodecs/video-encoder-content-hint.https.any.js'
alias ve3='./mach wpt testing/web-platform/tests/webcodecs/reconfiguring-encoder.https.any.js'
alias ve4='./mach wpt testing/web-platform/tests/webcodecs/video-encoder-flush.https.any.js'
alias ve5='./mach wpt testing/web-platform/tests/webcodecs/video-encoder-h264.https.any.js'
alias ve6='./mach wpt testing/web-platform/tests/webcodecs/video-encoder.https.any.js'
alias ve7='./mach wpt testing/web-platform/tests/webcodecs/temporal-svc-encoding.https.any.js'
alias ve8='./mach wpt testing/web-platform/tests/webcodecs/per-frame-qp-encoding.https.any.js'
alias ve9='./mach wpt testing/web-platform/tests/webcodecs/video-encoder-rescaling.https.any.js'
alias ve10='./mach wpt testing/web-platform/tests/webcodecs/video-encoder-h26x-annexb.https.any.js'
# WebCodecs full-cycle
alias wcf='./mach wpt testing/web-platform/tests/webcodecs/full-cycle-test.https.any.js'

# Format check
alias mfmt='./mach clang-format'
alias mfmtfor='./mach clang-format --path'
alias manal='./mach static-analysis check' # usage: `manal <FILE_PATH>`

# Format all uncommit files
function MozFormatUncommit() {
  GitUncommit './mach clang-format --path'
}
alias mfmtuc='MozFormatUncommit'

# Debug
alias mmd10='./mach mochitest --disable-e10s'
alias mrgd10='./mach run --disable-e10s --debug --debugger=gdb'
alias mrrd10='./mach run --disable-e10s --debug --debugger=rr'

# Install Fennec to Android
alias mpack='./mach package'
alias minst='./mach install'

# mochitest
alias mm='./mach mochitest'

# gtest
alias mg='./mach gtest'

# try server
alias mt='./mach try'
alias mt-all='./mach try -b do -p all -u all -t none'
alias mt-debug-all='./mach try -b d -p all -u all -t none'

# wpt
alias mw='./mach wpt'

# Check if the diff meets lints
function MozCheckDiff() {
  git diff --name-only "$1" | while IFS= read -r file; do
    printf "Check %s\n" "$file"
    ./mach clang-format --path "$file"
    ./mach static-analysis check "$file"
    printf "\n"
  done
}

# Update a crate under <path-to>/<gecko>/toolkit/library/rust/shared/Cargo.toml
function UpdateCrate() {
  local crate="$1"
  cargo update -p "$crate" && ./mach vendor rust --ignore-modified
}

# Generate a w3c spec page from a .bs file
function W3CSpec() {
  local file="$1"
  local page="$2"
  curl https://api.csswg.org/bikeshed/ -F "file=@$file" -F force=1 > "$page"
}
