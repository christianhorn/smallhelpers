#!/usr/bin/env pmpython

import sys
from pcp import pmapi
from pcp.pmapi import pmErr
import cpmapi as c_api
import time
import re

# Setup context, initiate fetching
ctx = pmapi.pmContext()
denkipmids = ctx.pmLookupName('lmsensors.macsmc_hwmon_isa_0000.total_system_power')
denkidescs = ctx.pmLookupDescs(denkipmids)

print("pmid:", denkidescs[0].contents.pmid)
print("type:", denkidescs[0].contents.type)
print("indom:", denkidescs[0].contents.indom)
print("sem:", denkidescs[0].contents.sem)
print("units:", denkidescs[0].contents.units)

denkiresults = ctx.pmFetch(denkipmids)
atom = ctx.pmExtractValue(denkiresults.contents.get_valfmt(0),
    denkiresults.contents.get_vlist(0, 0), denkidescs[0].contents.type,
    c_api.PM_TYPE_FLOAT)
denkivar = atom.f
print(denkivar)
