#!/bin/zsh
cd "$(dirname "$0")"
python3 launcher.py
status=$?
if [ $status -ne 0 ]; then
  echo
  echo "FocusAway launcher exited with status $status"
  echo "Press Enter to close."
  read
fi
