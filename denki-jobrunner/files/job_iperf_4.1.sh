#!/usr/bin/bash

WORKTIME=${1}
echo -e "\tDoing network load for $WORKTIME sec"

rm -f /tmp/counter /tmp/runcounter* /tmp/runlog* /tmp/threads

echo -e "\tStarting job.. "
# iperf3 -c 192.168.4.1 -t ${WORKTIME}s >/tmp/iperf_tmp 2>/tmp/iperf_stderr
iperf -c 192.168.4.1 -t ${WORKTIME} >/tmp/iperf_tmp 2>/tmp/iperf_stderr

# cat /tmp/iperf_tmp
BANDW=$(tail -n 1 /tmp/iperf_tmp|cut -d ' ' -f 11,12|sed -e 's, ,,')

echo "$BANDW" > /tmp/results
