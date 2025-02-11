#!/usr/bin/bash

SLEEPTIME=${1}
OS=$(uname -s)
echo -e "\tDoing load for $SLEEPTIME sec"

extract () {
	THREAD=${1}
        RUNS=0
        MYWORKDIR="/dev/shm/"

        echo "$RUNS" >/tmp/runcounter_${THREAD}
		cd $MYWORKDIR

        while :; do

        	echo -en "\n\tstarting-thread-${THREAD} - RUNS ${RUNS}"
                if [ $OS = "Linux" ]; then
                    dd if=/dev/zero of=1gbfile bs=1M count=1024 2>/dev/null
                else
                    # bsd etc.
                    dd if=/dev/zero of=1gbfile bs=1m count=1024 2>/dev/null
                fi

            RUNS=$(( $RUNS + 1 ))
            echo "$RUNS" >/tmp/runcounter
        done
}

rm -f /tmp/counter /tmp/runcounter* /tmp/runlog* /tmp/threads

echo -e "\tStarting job.. "
extract 1 &
procpid=${!}
echo

sleep $SLEEPTIME
kill $procpid

total=$(cat /tmp/runcounter)

echo $total >/tmp/results
