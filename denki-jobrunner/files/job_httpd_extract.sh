cd /dev/shm;
LOOPTIME=$1
echo -en "\tlooping for $LOOPTIME sec"
ENDTIME=$(( $(date +'%s') + $LOOPTIME ))
COUNTER=0;
while [ `date +'%s'` -lt $ENDTIME ]; do
           echo -n '.';
           rm -rf httpd-2.4.57;
           tar xjf httpd-2.4.57.tar.bz2
           # sleep 1
           COUNTER=$(($COUNTER + 1));
done
# echo "\t Loop did run $COUNTER times."
echo $COUNTER >/tmp/counter
