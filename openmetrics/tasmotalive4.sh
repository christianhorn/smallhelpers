#!/bin/bash

IP="192.168.0.3"

# exit if unreachable
if `ping -W 1 $IP -c1 >/dev/null`; then
       UNREACH=0
else
       UNREACH=1
fi

#
# UNREACH=1
# sleep 0.1

curl -s "http://$IP/cm?cmnd=Status%208" >/dev/shm/tmp_$$

# no correction for these
for var in Power ApparentPower ReactivePower Factor Voltage Current; do
		if [ $UNREACH == 1 ]; then
			VAR="N/A"
			# VAR="0"
		else
			VAR=$(cat /dev/shm/tmp_$$|jq ".StatusSNS.ENERGY.$var")
		fi
		echo "$var {var=\"out\"} $VAR"
done

# compute Wh for these/multiply by 1000
for var in Total Yesterday Today; do
		if [ $UNREACH == 1 ]; then
			VAR="N/A"
			# VAR="0"
		else
			VAR=$(cat /dev/shm/tmp_$$|jq ".StatusSNS.ENERGY.$var")
		fi
		# VAR2=$(echo "$VAR"|awk '{printf "%.2f", ( $1 - $2 ) / 60 }')
		VAR2=$(echo "$VAR"|awk '{printf "%d", $1 * 1000 }')
		echo "$var {var=\"out\"} $VAR2"
done


# cat /dev/shm/tmp_$$
# echo "/dev/shm/tmp_$$"
rm -f /dev/shm/tmp_$$
