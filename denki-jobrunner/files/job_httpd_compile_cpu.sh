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

                rm -rf $MYWORKDIR
                cp -r httpd-2.4.57 $MYWORKDIR;
                cd $MYWORKDIR
                ./configure >/tmp/runlog_${THREAD} 2>&1
                if [ $? != 0 ]; then
                        echo -n 'configure failed.'
                        exit 1
                fi
                make >>/tmp/runlog_${THREAD} 2>&1
                if [ $? != 0 ]; then
                        echo -n 'make failed.'
                        exit 1
                fi
                cd ..

                RUNS=$(( $RUNS + 1 ))
                echo "$RUNS" >/tmp/runcounter_${THREAD}
        done
}

rm -f /tmp/counter /tmp/runcounter* /tmp/runlog* /tmp/threads

echo -e "\tpreparing.."
rm -rf httpd-work* httpd-2.4.57
tar xjf httpd-2.4.57.tar.bz2

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
