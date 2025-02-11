#!/usr/bin/bash

OS=$(uname -s)
echo -ne "\tStarting job.. "

rm -f $MYWORKDIR/1gbfile

MYWORKDIR="/home/chris/"

cd $MYWORKDIR

if [ $OS = "Linux" ]; then 
	touch $MYWORKDIR/1gbfile
	dd if=/dev/zero of=$MYWORKDIR/1gbfile bs=1M count=1024 oflag=sync >&/tmp/out
else
	# bsd etc.
	touch $MYWORKDIR/1gbfile
	dd if=/dev/zero of=$MYWORKDIR/1gbfile bs=1m count=1024 oflag=sync msgfmt=human >&/tmp/out
fi

rm -f $MYWORKDIR/1gbfile

if [ $OS = "Linux" ]; then 
	RESULT=$(tail -n 1 /tmp/out|sed -e 's/.*, //' -e 's, ,,')
else
	# bsd etc.
	RESULT=$(tail -n 1 /tmp/out|sed -e 's/.* - //' -e 's/)//' -e 's, ,,')
fi

echo "$RESULT"
echo "$RESULT" >/tmp/results
