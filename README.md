# iso-validator
- for RPM based distributions
- analyse given ISO or disk image (raw) and compare with the old one
- compare ISO or disk image (raw) with yum repos
- works on Fedora, RHEL, Centos (non-live) ISOs and images (raw)

## Usage
```
$ ./iso-analysis.py -h
Usage: iso-analysis.py [options]

Options:
  -h, --help            show this help message and exit
  --new-iso=NEW_ISO     URI of binary content for validation (new)
  --source-iso=SOURCE_ISO
                        URI of source content for validation (new)
  --old-iso=OLD_ISO     URI of content for reference (old)
  --arch=ARCH           Target architecture (x86_64, i686...)
  --key-id=KEY_ID       Package signing Key ID (can be specified multiple
                        times)
  --repo-comparison     Compare ISO packages NVRs to the available yum repos
  --repofrompath=REPOFROMPATH
                        Specify repoid & paths of additional repositories -
                        unique repoid and complete path required, can be
                        specified multiple times. Example.
                        --repofrompath=myrepo,/path/to/repo
```
