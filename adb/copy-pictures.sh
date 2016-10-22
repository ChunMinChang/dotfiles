#!/bin/bash

# Get ADB Devices
declare -a devices
let i=0
getADBDevices(){
  while read line #get devices list
  do
    if [ -n "$line" ] && [ "`echo $line | awk '{print $2}'`" == "device" ]
    then
      device="`echo $line | awk '{print $1}'`"
      devices[i]="$device" # $ is optional
      let i=$i+1
    fi
  done < <(adb devices)

echo "getADBDevices: ${devices[*]}"
}

# Get adb device list
getADBDevices

## Get folder list in sdcard/DCIM
DCIMFolders=($(adb shell ls sdcard/DCIM | tr -d '\r'))
#DCIMFolders=($(adb shell ls | tr -d '\r'))
#echo "DCIMFolders: ${DCIMFolders[*]}"

# If more than 1 device, then exit
if test ${#devices[@]} -gt 1
then
  echo "More than 1 adb devices!"
  exit
fi

# If no folders under sdcard/DCIM, then exit
if [ ${#DCIMFolders[@]} -lt 1 ]; then
  echo "Less than 1 folder in sdcard/DCIM!"
  exit
# If no pictures under the first folder, then exit
elif [[ -z $(adb shell ls /sdcard/DCIM/${DCIMFolders[0]}) ]]; then
  echo "No files in sdcard/DCIM/${DCIMFolders[0]}"
  exit
fi


echo "Copy pictures from device via ADB"
echo "================================="

# Generate a folder name
DATE=$(date +%Y-%m-%d_%H:%M:%S)
DIR_NAME="ADB-Pictures_$DATE"

# Create an folder
echo "Create folder $DIR_NAME in $(pwd)"
mkdir -p "$DIR_NAME"

# Copy pictures under these folders
for i in "${DCIMFolders[@]}"
do
  echo "under: $i:"
  echo "---------------"
  folder="sdcard/DCIM/$i"
  adb shell ls $folder
  adb pull $folder $DIR_NAME
done
