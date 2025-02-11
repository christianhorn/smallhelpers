#!/usr/bin/bash

if [ ${1} = 'all' ]; then
	CPUS=$(grep -c processor /proc/cpuinfo)
else
	CPUS=${1}
fi

SLEEPTIME=${2}
echo -e "\tDoing load for $SLEEPTIME sec"

extract () {
	THREAD=${1}
        RUNS=0
        echo "$RUNS" >/tmp/runcounter_${THREAD}

        while :; do

        	echo -en "\n\tstarting-for-cpu-${THREAD} - RUNS ${RUNS}"
                MYWORKDIR="httpd-work-${THREAD}"

		bzcat httpd-2.4.57.tar.bz2 >/dev/null
		# /mnt/store/deploy3/images/tmp2/usr/bin/bzcat httpd-2.4.57.tar.bz2 >/dev/null

                RUNS=$(( $RUNS + 1 ))
                echo "$RUNS" >/tmp/runcounter_${THREAD}
        done
}

rm -f /tmp/counter /tmp/runcounter* /tmp/runlog* /tmp/threads

echo -e "\tStarting jobs.. "
for cpu in $(seq $CPUS); do
        extract $cpu &
        pids[$cpu]=${!}
        # echo -ne "pid:${!} "
done
echo

sleep $SLEEPTIME
for pid in ${pids[@]}; do
        # echo -n "killing:$pid "
        kill $pid
done

total=0
for cpu in $(seq $CPUS); do
        counter=$(cat /tmp/runcounter_$cpu)
        total=$(( $total + $counter ))
done

echo $total >/tmp/counter
echo $CPUS >/tmp/threads
