# General
alias mb='./mach build'
alias mr='./mach run'
alias mc='./mach clobber'

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