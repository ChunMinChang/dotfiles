# General
alias mb='./mach build'
alias mr='./mach run'
alias mc='./mach clobber'
alias mfb='mfmt && mb'
# WebCodecs VideoFrame
alias wc='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-construction.any.js'
alias wc2='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-construction.window.js'
alias wc3='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-copyTo.any.js'
alias wc4='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-copyTo.crossOriginIsolated.https.any.js'
alias wc5='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-construction.crossOriginIsolated.https.any.js'
alias wc6='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-construction.crossOriginSource.sub.html'
alias wc7='./mach wpt testing/web-platform/tests/webcodecs/video-frame-serialization.any.js'
alias wc8='./mach wpt testing/web-platform/tests/webcodecs/videoFrame-serialization.crossAgentCluster.https.html'
# WebCodecs VideoDecoder
alias wc9='./mach wpt testing/web-platform/tests/webcodecs/encoded-video-chunk.any.js'
alias wc10='./mach wpt testing/web-platform/tests/webcodecs/encoded-video-chunk.crossOriginIsolated.https.any.js'
alias wc11='./mach wpt testing/web-platform/tests/webcodecs/encodedVideoChunk-serialization.crossAgentCluster.https.html'
alias wc12='./mach wpt testing/web-platform/tests/webcodecs/chunk-serialization.any.js'
alias wc13='./mach wpt testing/web-platform/tests/webcodecs/video-decoder.https.any.js'
alias wc14='./mach wpt testing/web-platform/tests/webcodecs/video-decoder.crossOriginIsolated.https.any.js'
alias wc15='./mach wpt testing/web-platform/tests/webcodecs/videoDecoder-codec-specific.https.any.js'
# WebCodecs VideoEncoder
alias wc16='./mach wpt testing/web-platform/tests/webcodecs/video-encoder-config.https.any.js'
alias wc17='./mach wpt testing/web-platform/tests/webcodecs/video-encoder-content-hint.https.any.js'
alias wc18='./mach wpt testing/web-platform/tests/webcodecs/reconfiguring-encoder.https.any.js'
alias wc19='./mach wpt testing/web-platform/tests/webcodecs/video-encoder-flush.https.any.js'
alias wc20='./mach wpt testing/web-platform/tests/webcodecs/video-encoder-h264.https.any.js'
alias wc21='./mach wpt testing/web-platform/tests/webcodecs/video-encoder.https.any.js'
alias wc22='./mach wpt testing/web-platform/tests/webcodecs/full-cycle-test.https.any.js'
alias wc23='./mach wpt testing/web-platform/tests/webcodecs/temporal-svc-encoding.https.any.js'
alias wc24='./mach wpt testing/web-platform/tests/webcodecs/per-frame-qp-encoding.https.any.js'

# Format check
alias mfmt='./mach clang-format'
alias mfmtfor='./mach clang-format --path'
alias mfmtuc='GitUncommit "./mach clang-format --path"' # Format all uncommit files
alias manal='./mach static-analysis check' # usage: `manal <FILE_PATH>`

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
  local files=`git diff --name-only $1`
  for file in $files; do
    printf "Check $file\n"
    ./mach clang-format --path $file
    ./mach static-analysis check $file
    printf "\n"
  done
}

# Update a crate under <path-to>/<gecko>/toolkit/library/rust/shared/Cargo.toml
function UpdateCrate() {
  local crate=$1
  cargo update -p $crate && ./mach vendor rust --ignore-modified
}

# Generate a w3c spec page from a .bs file
function W3CSpec() {
  local file=$1
  local page=$2
  curl https://api.csswg.org/bikeshed/ -F file=@$file -F force=1 > $page
}
