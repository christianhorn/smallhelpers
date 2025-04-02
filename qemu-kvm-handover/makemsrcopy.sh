#!/usr/bin/bash

set -x 

mkdir -p proc
cp /proc/cpuinfo proc

# rm -rf dev

for i in $(find /dev/cpu -mindepth 1 -type d); do
	PTH="`echo $i | sed -e 's,^/,,'`"
	mkdir -p $PTH
done

for i in $(find /dev/cpu/ -name msr); do
	DST="`echo $i | sed -e 's,^/,,'`"
	dd if=$i of=${DST} bs=128M count=1
done

# /sys/devices/system/cpu/cpu0/topology/physical_package_id
for i in $(find /sys/devices/system/cpu/cpu* -name physical_package_id); do
	DST="`echo $i | sed -e 's,^/,,'`"
	DIR="`echo $DST | sed -e 's,/physical_package_id,,'`"
	mkdir -p $DIR
	cp $i $DST
done

mkdir -p sys/class/powercap/intel-rapl/intel-rapl\:0/
cp 	/sys/class/powercap/intel-rapl/intel-rapl\:0/name	\
	/sys/class/powercap/intel-rapl/intel-rapl\:0/energy_uj \
	 sys/class/powercap/intel-rapl/intel-rapl\:0/

mkdir -p sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:0/
cp 	/sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:0/name	\
	/sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:0/energy_uj \
	 sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:0/
mkdir -p sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:1/
cp 	/sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:1/name	\
	/sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:1/energy_uj \
	 sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:1/
mkdir -p sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:2/
cp 	/sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:2/name	\
	/sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:2/energy_uj \
	 sys/class/powercap/intel-rapl/intel-rapl\:0/intel-rapl\:0\:2/
