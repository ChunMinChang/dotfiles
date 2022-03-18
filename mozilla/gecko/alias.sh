# General
alias mb='./mach build'
alias mr='./mach run'
alias mc='./mach clobber'

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
