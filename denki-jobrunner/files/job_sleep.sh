#!/usr/bin/bash

SLEEPTIME=$1
echo -en "\tsleeping for $SLEEPTIME sec"

sleep $SLEEPTIME
echo 1 >/tmp/counter
echo 1 >/tmp/threads
