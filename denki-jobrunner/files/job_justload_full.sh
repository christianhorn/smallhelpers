SLEEPTIME=$1
echo -en "\tDoing load for $SLEEPTIME sec"

CPUS=$(grep -c processor /proc/cpuinfo)
for cpu in $(seq $CPUS); do
	(md5sum /dev/urandom &)
done

sleep $SLEEPTIME
killall md5sum
echo $CPUS >/tmp/counter
