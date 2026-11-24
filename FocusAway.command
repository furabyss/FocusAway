#!/bin/zsh
cd "$(dirname "$0")" || exit 1

# Finder/Terminal may resolve python3 to Apple's legacy Tk 8.5 build even
# when a current Homebrew Python and Tk are installed.
if [[ -n "${FOCUSAWAY_PYTHON:-}" ]]; then
  python_candidates=("$FOCUSAWAY_PYTHON")
else
  python_candidates=(
    python3
    /opt/homebrew/opt/python@*/libexec/bin/python3(NOn)
    /usr/local/opt/python@*/libexec/bin/python3(NOn)
    /opt/homebrew/bin/python3(N)
    /opt/homebrew/bin/python3.<->(NOn)
    /usr/local/bin/python3(N)
    /usr/local/bin/python3.<->(NOn)
    /Library/Frameworks/Python.framework/Versions/*/bin/python3(NOn)
  )
fi

python_bin=""
for candidate in "${python_candidates[@]}"; do
  if "$candidate" -c 'import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 10) and tkinter.TkVersion >= 8.6 else 1)' >/dev/null 2>&1; then
    python_bin="$candidate"
    break
  fi
done

if [[ -n "$python_bin" ]]; then
  "$python_bin" -c 'import sys, tkinter; print("FocusAway Python:", sys.executable); print("Python:", sys.version.split()[0], "Tk:", tkinter.TkVersion)'
  "$python_bin" launcher.py
  launcher_exit_code=$?
else
  echo "FocusAway requires Python 3.10+ with Tk 8.6+."
  echo "Install a current Python with tkinter, or set FOCUSAWAY_PYTHON to its executable."
  launcher_exit_code=1
fi
if [ $launcher_exit_code -ne 0 ]; then
  echo
  echo "FocusAway launcher exited with status $launcher_exit_code"
  echo "Press Enter to close."
  read
fi
exit "$launcher_exit_code"
