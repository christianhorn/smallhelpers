cd /dev/shm;
LOOPTIME=$1
echo -en "\tlooping for $LOOPTIME sec"
ENDTIME=$(( $(date +'%s') + $LOOPTIME ))
COUNTER=0;
while [ `date +'%s'` -lt $ENDTIME ]; do
       	echo -n '.';
       	cp -r httpd-2.4.57 httpd-work;
		cd httpd-work
		./configure >/tmp/tmp 2>&1
		if [ $? != 0 ]; then
			echo -n 'configure failed.'
			exit 1
		fi
		make >>/tmp/tmp 2>&1
		if [ $? != 0 ]; then
			echo -n 'make failed.'
			exit 1
		fi
		cd ..
		rm -rf httpd-work
        # sleep 1
        COUNTER=$(($COUNTER + 1));
done
# echo "\t Loop did run $COUNTER times."
echo $COUNTER >/tmp/counter
