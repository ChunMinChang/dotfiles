#!/bin/bash

function IsUserRoot()
{
  if [ "$EUID" -ne 0 ]; then
    echo 0
  else
    echo 1
  fi
}

# enum for os environment
# ENV_LINUX=0
# ENV_OSX=1
# ENV_SOLARIS=2
# ENV_BSD=3
# ENV_Cygwin=4
# ENV_OTHER=5

# Imitate the enum type:
# This function will declare global variable by the order
# Example:
#   enum fruit { apple, banana, cherry }
#   => The above declaration is same as:
#   apple=1
#   banana=2
#   cherry=3
enum ()
{
    # skip index ???
    shift
    AA=${@##*\{} # get string strip after {
    AA=${AA%\}*} # get string strip before }
    AA=${AA//,/} # delete commaa
    local I=0
    for A in $AA ; do
        eval "$A=$I"
        ((I++))
    done
}

enum ENV_MAP { ENV_LINUX, ENV_OSX, ENV_SOLARIS, ENV_BSD, ENV_Cygwin, ENV_OTHER }

function GetOSEnvironment()
{
  local OS="UNDETECTED" # OS Environment
  case "$OSTYPE" in
    linux*)
      # OS="LINUX" ;;
      OS=$ENV_LINUX ;;
    darwin*)
      # OS="OSX" ;;
      OS=$ENV_OSX ;;
    solaris*)
      # OS="SOLARIS" ;;
      OS=$ENV_SOLARIS ;;
    bsd*)
      # OS="BSD" ;;
      OS=$ENV_BSD ;;
    cygwin)
      # OS="cygwin" ;;
      OS=$ENV_Cygwin ;;
    *)
      OS=$ENV_OTHER ;;
  esac
  echo $OS
}

function GetPackageManager()
{
  # Set the package manager
  PackageManager[ENV_LINUX]=apt-get
  PackageManager[ENV_OSX]=brew
  echo ${PackageManager[$1]}
}

function GetPackageCommand()
{
  local OS=$(GetOSEnvironment)
  echo $(GetPackageManager $OS)
}
