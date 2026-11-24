#!/bin/zsh
cd "$(dirname "$0")"
python3 launcher.py
launcher_exit_code=$?
if [ $launcher_exit_code -ne 0 ]; then
  echo
  echo "FocusAway launcher exited with status $launcher_exit_code"
  echo "Press Enter to close."
  read
fi
exit "$launcher_exit_code"
