# File Format References

## LIP file format

The LIP binary format was reverse-engineered from Black_Electric's LIPS.py and validated against LIP Editor. Key constants:

- Version: `0x00000002`
- Unknown constant at `0x04`: `0x00005800`
- Sample offset formula: `round(seconds × 2 × 22050)`
- ACM filename field: 8 bytes, uppercase, null-padded, followed by `VOC\0`

Format documented at https://fodev.net/files/fo2/lip.html

## DAT file format

Format documented at https://fodev.net/files/fo2/dat.html
