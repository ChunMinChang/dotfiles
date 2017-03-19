#!/bin/bash

function CommandExists()
{
  local cmd=$1
  if command -v $cmd >/dev/null 2>&1; then
    echo 1
  else
    echo >&2 "$cmd is not installed.";
    echo 0
  fi
}
