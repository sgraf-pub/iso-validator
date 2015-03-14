# iso-validator
- for RPM based distributions
- analyse given ISO and compare with the old one
- compare ISO with yum repos
- works on Fedora, RHEL, Centos (non-live) ISOs

## Usage
```
$ ./iso_analysis.py -h
Usage: iso_analysis.py [options]

Options:
  -h, --help         show this help message and exit
  --new_iso=NEW_ISO  URI of ISO image for validation (new)
  --old_iso=OLD_ISO  URI of ISO image for reference (old)
  --arch=ARCH        Target architecture (x86_64, i686...)
  --key_id=KEY_ID    Package signing Key ID
  --repo_comparison  Compare ISO packages NVRs to the available yum repos
```

## Example for Fedora Sever DVD:
```
$ sudo ./iso_analysis.py --new_iso Fedora-Server-DVD-x86_64-22_Alpha.iso --old_iso Fedora-Server-DVD-x86_64-22_Alpha_TC8.iso --arch=x86_64 --key_id=8e1431d5 --repo_comparison
Analysing /home/sgraf/Downloads/Fedora-Server-DVD-x86_64-22_Alpha.iso as new iso
ISO Analysing files
ISO Analysing packages
Analysing /home/sgraf/Downloads/Fedora-Server-DVD-x86_64-22_Alpha_TC8.iso as old iso
ISO Analysing files
ISO Analysing packages
File (non-rpm) tests: files added (new vs old iso)
set([])
File (non-rpm) tests: files removed (new vs old iso)
set([])
File (non-rpm) tests: changed files (new vs old iso)
set(['.discinfo',
     '.treeinfo',
[...]
     'repodata/TRANS.TBL',
     'repodata/repomd.xml'])
Package tests: packages added (new vs old iso)
set(['python-sss-1.12.4-2.fc22.x86_64',
     'python-sss-murmur-1.12.4-2.fc22.x86_64',
     'python-sssdconfig-1.12.4-2.fc22.noarch',
     'tomcat-el-2.2-api-7.0.59-3.fc22.noarch',
     'tomcat-jsp-2.2-api-7.0.59-3.fc22.noarch',
     'tomcat-servlet-3.0-api-7.0.59-3.fc22.noarch'])
Package tests: packages removed (new vs old iso)
set([])
Package tests: possibly unsigned (new iso only)
set([])
Package tests: missing source (new iso only)
set(['389-ds-base-1.3.3.8-1.fc22.src.rpm',
     'BackupPC-3.3.0-4.fc22.src.rpm',
[...]
     'zsh-5.0.7-6.fc22.src.rpm',
     'zvbi-0.2.33-18.fc22.src.rpm'])
Package tests: wrong arch (new iso only)
set([])
Package tests: comparing ISO with yum repos
YUM Analysing packages
Unreleased version (newer on ISO, older in yum repos)
set([])
Not updated packages (older on ISO, newer in yum repos)
set(['389-ds-base-1.3.3.8-1.fc22.x86_64',
     '389-ds-base-libs-1.3.3.8-1.fc22.x86_64',
[...]
     'xdg-utils-1.1.0-0.38.rc3.fc22.noarch',
     'yaml-cpp-0.5.1-5.fc22.x86_64'])
Packages on ISO, missing in yum repos
set(['tomcat-el-3.0-api-8.0.18-2.fc22.noarch',
     'tomcat-jsp-2.3-api-8.0.18-2.fc22.noarch',
     'tomcat-servlet-3.1-api-8.0.18-2.fc22.noarch'])
```

