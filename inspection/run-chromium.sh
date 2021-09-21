#!/bin/sh
BASE_TEMP_DIR="/tmp"
TEMP_DIR=$(mktemp -d "$BASE_TEMP_DIR/chromium.XXXXXXXX")

echo "Running chromium with temporary profile in: $TEMP_DIR"

unameOut="$(uname -s)"
case "${unameOut}" in
    Darwin*)    chromiumPath="/Applications/Chromium.app/Contents/MacOS/Chromium";;
    Linux*)     chromiumPath="/usr/bin/chromium";;
    *)          echo "Unknown uname: ${unameOut}" && exit
esac

close_chromium()
{
    echo "\nStopping chromium..."

    # kill chromium
    pkill -o -i chromium
    sleep 1
    pkill -o -i chromium
    sleep 1

    # delete temporary profile
    rm -rf "$TEMP_DIR"
    exit 0
}

trap close_chromium INT

# Chromium
# - https://peter.sh/experiments/chromium-command-line-switches/
# - https://stackoverflow.com/questions/53280678/why-arent-network-requests-for-iframes-showing-in-the-chrome-developer-tools-un
# Run in background
# - https://stackoverflow.com/questions/3683910/executing-shell-command-in-background-from-script
("${chromiumPath}" \
    --remote-debugging-port=9222 --enable-automation \
    --user-data-dir="$TEMP_DIR" --no-first-run --no-startup-window \
    --disk-cache-size=0  \
    --window-size=1400,950 --window-position=0,0 \
    --disable-features=IsolateOrigins,site-per-process \
    &>/dev/null & )

# while pgrep -o -i chromium > /dev/null; do # while chromium is running
# when --no-startup-window is used, 
# chromium process keeps running even if app was quit in the UI
# -> ugly fix: check whether more than 4 processes are running

sleep 3
while (( $(pgrep -i chromium | wc -l) > 4 )); do 
    sleep 1
done

sleep 1
close_chromium
