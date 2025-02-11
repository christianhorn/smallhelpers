#!/usr/bin/bash

OS=$(uname -s)
echo -ne "\tStarting job.. "

rm -f $MYWORKDIR/1gbfile

MYWORKDIR="/home/chris/"

cd $MYWORKDIR

# Let's first write, we do not care about the speed here..
if [ $OS = "Linux" ]; then 
	touch $MYWORKDIR/1gbfile
	dd if=/dev/zero of=$MYWORKDIR/1gbfile bs=1M count=1024 oflag=sync >&/tmp/out
else
	# bsd etc.
	touch $MYWORKDIR/1gbfile
	dd if=/dev/zero of=$MYWORKDIR/1gbfile bs=1m count=1024 oflag=sync >&/tmp/out
fi

# Now read, we care about the speed.
if [ $OS = "Linux" ]; then 
	dd if=$MYWORKDIR/1gbfile of=/dev/null bs=1M >&/tmp/out
else
	# bsd etc.
	dd if=$MYWORKDIR/1gbfile of=/dev/null bs=1m msgfmt=human >&/tmp/out
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
