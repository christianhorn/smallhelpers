#!/usr/bin/bash

WORKTIME=${1}
echo -e "\tDoing network load for $WORKTIME sec"

rm -f /tmp/counter /tmp/runcounter* /tmp/runlog* /tmp/threads

echo -e "\tStarting job.. "
iperf3 -c 192.168.4.1 -t ${WORKTIME}s >/tmp/iperf_tmp 2>/tmp/iperf_stderr

# cat /tmp/iperf_tmp
SENDER=$(grep sender /tmp/iperf_tmp 		| awk '{print $7,$8}' | sed -e 's, ,,')
RECEIVER=$(grep receiver /tmp/iperf_tmp 	| awk '{print $7,$8}' | sed -e 's, ,,')

echo "$SENDER-$RECEIVER" > /tmp/results
