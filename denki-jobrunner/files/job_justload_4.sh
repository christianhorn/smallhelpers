SLEEPTIME=$1
echo -en "\tDoing load for $SLEEPTIME sec"
md5sum /dev/urandom &
md5sum /dev/urandom &
md5sum /dev/urandom &
md5sum /dev/urandom &
sleep $SLEEPTIME
killall md5sum
echo 1 >/tmp/counter
