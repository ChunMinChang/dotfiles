#!/bin/bash

# Common utilities
# ============================================
# Print the log with header 1 prefix
function LogH1()
{
  echo ">>>>> $1"
}

# Print the log with header 2 prefix
function LogH2()
{
  echo ">> $1"
}

function Warning()
{
  echo -e "## Warning ##\n  $1"
}

function GetTime()
{
  date +%Y-%m-%d:%H:%M:%S
}

function GetUnixTimestamp()
{
  date +%s
}

# List all file matches the input pattern
# Example:
#   $ RecurFind *.DS_Store
#   ./.DS_Store
#   ./css/.DS_Store
#   ./images/.DS_Store
#   ./images/chunmin/.DS_Store
#   ./images/gallery/.DS_Store
#   ./images/works/.DS_Store
#   ./js/.DS_Store
function RecurFind()
{
  local file=$1
  find . -name ``$file''
}

# Delete all file matches the input pattern
# Example:
#   $ RecurFindAndDelete *.DS_Store
# Then all the files list by ($ RecurFind *.DS_Store) will be removed
function RecurFindAndDelete()
{
  local file=$1
  find . -name ``$file'' -type f -delete
}

# Return the real path fromb a symblic link
# Example:
#  $ GetRealLink ~/.bash_profile
#  /Users/chunminchang/dotfiles/bash_profile
function GetRealLink()
{
  local link=$1
  echo $(python -c "import os; print os.path.realpath('$link')")
}

# Return the string without the prefix
# Example:
#   $ StripPrefix demoHelloWorld demo
#   HelloWorld
function StripPrefix()
{
  local string=$1 prefix=$2
  echo ${string#$prefix}
}

# Return the string without the prefix
# Example:
#   $ StripSuffix demoHelloWorld World
#   demoHello
function StripSuffix()
{
  local string=$1 suffix=$2
  echo ${string%$suffix}
}

# Return true if the user is root. Otherwise, return false
function IsUserRoot()
{
  # if [ "$(id -u)" == "0" ]; then
  if [[ $EUID -eq 0 ]]; then
    echo 1
  else
    echo 0
  fi
}

# Return true if the input path is a file and it exist. Otherwise, return false
#
# Parameters:
#   $1: the file's path
function DoseFileExist()
{
  local file=$1
  if [ -f $file ]; then
    echo 1
  else
    echo 0
  fi
}

function ExportToPATH()
{
  local directory=$1
  if [ -d "$directory" ]; then
    export PATH=$directory:$PATH
  fi
}

function Move()
{
  local oldPath=$1 newPath=$2

  if [ ! -f $oldPath ]; then
    Warning "$oldPath doesn't exist!"
    return
  fi

  # if newPath already has a existing file and it's not a symblic link
  # then we will rename the existing file to "FILENAME_TIMESTAMP".
  if [ -f $newPath ] && [ ! -L $newPath ]; then
    local timestamp=$(GetUnixTimestamp)
    local pathWithDate="$newPath-$timestamp"
    Warning "Rename $newPath to $pathWithDate"
    Move $newPath $pathWithDate
  fi

  mv $oldPath $newPath
}

function Trash()
{
  local file=$1
  local trashcanPath=$(GetTrashPath)
  mv $file $trashcanPath
}

# Return true if the file has the input string pattern. Otherwise, return false
# Example:
#   ret=$(GrepStringInFile \[world\] hello.txt) // ret = 1
#   hello.txt:
#     hello
#     [world]
#
# Parameters:
#   $1: the string patteren with regular expression
#   $2: the file's path
function GrepStringInFile()
{
  local string=$1 filepath=$2

  exist=$(DoseFileExist $filepath)

  if [ $exist -eq 0 ]; then # if file doesn't exist, return false
    echo 0
  else
    if grep -q "$string" $filepath; then
      echo 1
    else
      echo 0
    fi
  fi
}

# Append the input string to the input file
#
# Parameters:
#   $1: the string that will be appended
#   $2: the file's path
function AppendStringToFile()
{
  local string=$1 filepath=$2

  exist=$(DoseFileExist $filepath)

  if [ $exist -eq 0 ]; then # if file doesn't exist, return
    return -1
  fi

  echo -e "$1" >> $filepath
}

#
function SourceFile()
{
  local sourceFile=$1 targetFile=$2
  AppendStringToFile "source $sourceFile" $targetFile
}

# Link or import a file into others
#   If the target file exist and it's a symblic link, then we just remove
#   the it then link it. If the target file exist and it's not a symblic link,
#   then we import our file into it.
#
function LinkOrImportFile()
{
  local sourceFile=$1 targetFile=$2

  # If the target file is not a symblic link and it does exist,
  # then we import our file into it
  if [ -f $targetFile ]; then
    echo "Import $sourceFile to $targetFile"
    SourceFile $sourceFile $targetFile
    return
  fi

  # If the target file exist and it is a symblic link
  if [[ -L "$targetFile" ]]; then
    local link=$(GetRealLink $targetFile)
    # if the target file is same as the source file, then it's nothing to do!
    if [ "$link" == "$sourceFile" ]; then
      return
    # otherwise, we will remove the old symbolic link
    else
      echo "Remove the existing symlink to $targetFile and re-link it!"
      rm $targetFile
    fi
  fi

  # Link the source file to target file
  echo "Symbolically link $sourceFile to $targetFile"
  ln -s $sourceFile $targetFile
}

# Symbolically link source file to target file
#   If the target file exist and it's a symblic link, then we just remove
#   the it then link it. If the target file exist and it's not a symblic link,
#   then we rename the old file to <FILENAME>_backup and then link our file.
#
# Parameters:
#   $1: the source file
#   $2: the target file
function LinkFile()
{
  local sourceFile=$1 targetFile=$2
  local postfix=_backup

  # If the target file is a symblic link
  if [[ -L "$targetFile" ]]; then
    local link=$(GetRealLink $targetFile)
    # if the target file is same as the source file, then it's nothing to do!
    if [ "$link" == "$sourceFile" ]; then
      return
    # otherwise, we will remove the old symbolic link
    else
      echo "Remove the existing symlink to $targetFile and re-link it!"
      rm $targetFile
    fi
  # If the target file is not a symblic link and it does exist,
  # then we will rename it as ./machrc[postfix string]
  elif [ -f $targetFile ]; then
    echo "Rename the existing $targetFile to $targetFile$postfix"
    mv $targetFile $targetFile$postfix
  fi

  # Link the source file to target file
  echo "Symbolically link $sourceFile to $targetFile"
  ln -s $sourceFile $targetFile
}

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

# Functions with OS dependency
# ============================================
# enum for os environment
# ENV_LINUX=0
# ENV_OSX=1
# ENV_SOLARIS=2
# ENV_BSD=3
# ENV_Cygwin=4
# ENV_OTHER=5
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

function GetPackageCommand()
{
  local envIndex=$(GetOSEnvironment)
  packageManager[ENV_LINUX]=apt-get
  packageManager[ENV_OSX]=brew
  echo ${packageManager[$envIndex]}
}

function GetTrashPath()
{
  local envIndex=$(GetOSEnvironment)
  trashPath[ENV_LINUX]="$HOME/.local/share/Trash/files/"
  trashPath[ENV_OSX]="$HOME/.Trash"
  echo ${trashPath[$envIndex]}
}
