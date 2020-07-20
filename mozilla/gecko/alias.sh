# General
alias mb='./mach build'
alias mr='./mach run'
alias mc='./mach clobber'

# Format or analysis check
alias mfmt='./mach clang-format'
alias mfmtfor='./mach clang-format --path'
alias manal='./mach static-analysis check'

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

# Generate a w3c spec page from a .bs file
# ------------------------------------------------
function W3CSpec() {
  local file=$1
  local page=$2
  curl https://api.csswg.org/bikeshed/ -F file=@$file -F force=1 > $page
}