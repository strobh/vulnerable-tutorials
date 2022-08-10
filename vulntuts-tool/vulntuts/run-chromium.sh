#!/bin/sh

tmp_profile=false
profile_path=""

# reading options, source:
# http://mywiki.wooledge.org/BashFAQ/035
# https://stackoverflow.com/a/2875513
while test $# != 0; do
    case "$1" in
    -t|--tmp-profile)
        tmp_profile=true
        ;;
    -p|--profile)
        if [ "$2" ]; then
            profile_path="$2"
            shift
        else
            echo "ERROR: '-p/--profile' requires a non-empty profile path." >&2 && exit
        fi
        ;;
    -?*)
        echo "WARN: Unknown option (ignored): ${1}\n" >&2
        ;;
    *)
        echo "WARN: Unknown argument (ignored): ${1}\n" >&2
        ;;
    esac
    shift
done

# create temporary directory
if [ "$tmp_profile" = true ] && [ -z "$profile_path" ]; then
    profile_path=$(mktemp -d)
fi

# print profile path
if [ "$tmp_profile" = true ]; then
    echo "Starting chromium with temporary profile in '${profile_path}'..."
elif [ ! -z "$profile_path" ]; then
    echo "Starting chromium with profile in '${profile_path}'..."
else
    echo "Starting chromium with default profile."
fi

unameOut="$(uname -s)"
case "${unameOut}" in
#    Darwin*)
#        chromiumPath="/Applications/Chromium.app/Contents/MacOS/Chromium"
#        chromiumProcess="chromium"
#        ;;
    Darwin*)
        chromiumPath="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        chromiumProcess="Google Chrome"
        ;;
    Linux*)
        chromiumPath="/usr/bin/chromium"
        chromiumProcess="chromium"
        ;;
    *)          echo "ERROR: Unknown uname '${unameOut}'" >&2 && exit
esac

close_chromium()
{
    echo "\nStopping chromium..."

    # kill chromium
    pkill -o -i "$chromiumProcess"
    sleep 1

    # delete temporary profile
    if [ "$tmp_profile" = true ]; then
        rm -rf "$profile_path"
    fi
    exit 0
}

trap close_chromium INT

# chromium command line options
# - https://peter.sh/experiments/chromium-command-line-switches/
# - https://stackoverflow.com/questions/53280678/why-arent-network-requests-for-iframes-showing-in-the-chrome-developer-tools-un
# run in background
# - https://stackoverflow.com/questions/3683910/executing-shell-command-in-background-from-script
if [ ! -z "$profile_path" ]; then
    ("${chromiumPath}" \
        --remote-debugging-port=9222 --enable-automation \
        --user-data-dir="$profile_path" --no-first-run \
        --disk-cache-size=0 \
        --window-size=1400,950 --window-position=0,0 \
        --disable-features=IsolateOrigins,site-per-process \
        &>/dev/null & )
else
    ("${chromiumPath}" \
        --remote-debugging-port=9222 --enable-automation \
        --no-first-run \
        --disk-cache-size=0 \
        --window-size=1400,950 --window-position=0,0 \
        --disable-features=IsolateOrigins,site-per-process \
        &>/dev/null & )
fi

# wait for chromium to start
sleep 3

# check if chromium is running
# > while pgrep -o -i chromium > /dev/null; do
# when --no-startup-window is used, chromium keeps running even if it was quit in the UI
# ugly fix would be: check whether more than 4 processes are running
# > while (( $(pgrep -i chromium | wc -l) > 4 )); do
while pgrep -o -i "$chromiumProcess" > /dev/null; do
    sleep 1
done

sleep 1
close_chromium
