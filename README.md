# textage2bms
Convert textage.cc to BMS

### Dependencies
- Python3
- python-selenium
- Chrom{e, ium} or Firefox
- PyQuery

### Usage
`$ python3 textage2bms.py 'http://textage.cc/score/24/marenect.html?1AC0' > marenect.bms`

### Options
- LN_DISABLE = [True/False] to disable handling of LN (textage2bms.py)

### Not supported
- BPM Change
- DP

### Known issues
- LN support is wacky

# bms-anmitsu
Flatten 16th notes/jacks into 8th notes for practice

### Usage
`$ python3 bms-anmitsu.py [BMS file] [Optional=Target 8th notes BPM or BPM ratio, default to song BPM]`

Example command: `$ python3 bms-anmitsu.py gigadelic\(2\ A\).bms 1`

Example output:
```
#03216 0.16666666666666666 2N 3 1 4 Nice
#03216 0.25 2O 4 -1 3 Jack!
#06419 0.9947916666666666 33 16 0 16 Deferred to next section #06519
#06519 Replaced 1st object from 00 to 33
#07216 0.16666666666666666 2N 3 1 4 Nice
#07216 0.25 2O 4 -1 3 Jack!
#08016 0.5625 2K 9 1 10 Nice
#08216 0.5625 2K 9 1 10 Nice
#08416 0.5625 2K 9 1 10 Nice
#08616 0.5625 2K 9 1 10 Nice
#08716 0.5625 2K 9 1 10 Nice

Target 8th notes BPM: 172.7 (1)
Jack ratio: 2/10 = 0.2
```

In the new BMS "gigadelic(2 A).anmitsu.bme", all 16th notes has been flattened to 8th notes. Also, 8 of 10 jacks has been transformed to 8th notes. The other 2 can't be handled.

# tja2bms
Convert Taijo Jiro to BMS (3 5 as red, 2 6 as blue) for fun

### Usage
`$ python3 tja2bms.py [TJA file] > tja.bms`

# bms-merge
Adding keysound to keysound-less BMS using existing keysounded BMS files

### Usage
`$ python3 bms-merge.py [Keysounded BMS] [Keysoundless BMS] [Optional=Keysoundless BMS section offset]`

Example command: 
1. `$ python3 textage2bms.py 'http://textage.cc/score/21/verflchl.html?1AC0' > verflucht-l7.bme`
2. `$ python3 bms-merge.py verflucht-a7.bme verflucht-l7.bme 1 > verflucht-merged.bme`