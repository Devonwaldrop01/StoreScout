#!/bin/sh
# Unconditionally inert: do not source application code or consult services.
child=
stop() {
    trap '' TERM INT
    if [ -n "$child" ]; then
        kill "$child" 2>/dev/null
        wait "$child" 2>/dev/null
    fi
    echo 'STORE_INDEX_MAINTENANCE_BRIDGE clean exit'
    exit 0
}
trap stop TERM INT
sleep infinity &
child=$!
echo 'STORE_INDEX_MAINTENANCE_BRIDGE idle; application not imported'
wait "$child"
echo 'STORE_INDEX_MAINTENANCE_BRIDGE unexpected child exit' >&2
exit 1
