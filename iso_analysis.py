#!/usr/bin/python2

# for RPM based distributions, analyse given ISO and compare with the old one
# Copyright (C) 2015  Stanislav Graf
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import optparse
import os
import pprint
import re
import subprocess
import sys
import tempfile


def run(cmd):
    cmd_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    std_output, error_output = cmd_process.communicate()
    if cmd_process.returncode != 0:
        print cmd
        print std_output
        print error_output
        sys.exit(cmd_process.returncode)
    return std_output


class MountedIso:
    def __init__(self, iso_uri):
        self.temp_dir = tempfile.mkdtemp()
        run('mount -o loop %s %s' % (iso_uri, self.temp_dir,))
        print "Analysing files"
        self.file_dict = self.__get_files__()
        print "Analysing packages"
        self.package_dict = self.__get_packages__()

    def __del__(self):
        run('umount %s' % self.temp_dir)

    def __get_files__(self):
        def add_file(file_type):
            single_file_path = os.path.join(root[len(self.temp_dir) + 1:], single_file)
            single_file_crc = run("md5sum %s" % (os.path.join(root, single_file))).split()[0]
            file_dict[single_file_path] = {'name': single_file, 'type': file_type, 'crc': single_file_crc}

        file_dict = {}
        for root, _, files in os.walk(self.temp_dir):
            if re.search('repodata', root):
                for single_file in files:
                    add_file('repodata')
            else:
                for single_file in files:
                    if single_file[-4:] == '.rpm':
                        add_file('rpm')
                    else:
                        add_file('none')
        return file_dict

    def __get_packages__(self):
        package_dict = {}
        for k, v in self.file_dict.iteritems():
            if v['type'] == 'rpm':
                package_raw_data = run(("rpm -q --qf='%%{name} %%{version} %%{release} %%{arch} %%{sourcerpm} "
                                        "%%{SIGPGP:pgpsig}' --nosignature -p %s")
                                       % os.path.join(self.temp_dir, k)).split()
                if k[-8:] == '.src.rpm':
                    package_raw_data[3] = 'source'
                    package_raw_data[4] = os.path.split(k)[-1]
                package_dict['%s.%s' % (package_raw_data[0], package_raw_data[3],)] = {
                    'name': package_raw_data[0],
                    'version': package_raw_data[1],
                    'release': package_raw_data[2],
                    'arch': package_raw_data[3],
                    'source': package_raw_data[4],
                    'signature': package_raw_data[-1][-8:]}
        return package_dict


def main():
    parser = optparse.OptionParser()
    parser.add_option("--new_iso", help="URI of ISO image for validation (new)")
    parser.add_option("--old_iso", help="URI of ISO image for reference (old)")
    parser.add_option("--arch", help="Target architecture (x86_64, i686...)")
    parser.add_option("--key_id", help="Package signing Key ID")
    args, _ = parser.parse_args()

    if args.new_iso is None:
        print "URI of ISO image for validation (--new_iso) is mandatory"
        sys.exit(1)
    print "Analysing %s as new iso" % args.new_iso
    new_iso = MountedIso(args.new_iso)

    if args.old_iso is None:
        print "Skipping analysis of old iso"
        print "Skipping tests requiring old iso"
    else:
        print "Analysing %s as old iso" % args.old_iso
        old_iso = MountedIso(args.old_iso)
        print 'File (non-rpm) tests: files added (new vs old iso)'
        extra_files = [k
                       for k, v in new_iso.file_dict.iteritems()
                       if k in set(new_iso.file_dict.iterkeys()) - set(old_iso.file_dict.iterkeys())
                       and v['type'] == 'none']
        pprint.pprint(set(extra_files))

        print 'File (non-rpm) tests: files removed (new vs old iso)'
        missing_files = [k
                         for k, v in new_iso.file_dict.iteritems()
                         if k in set(old_iso.file_dict.iterkeys()) - set(new_iso.file_dict.iterkeys())
                         and v['type'] == 'none']
        pprint.pprint(set(missing_files))

        print 'File (non-rpm) tests: changed files (new vs old iso)'
        crc_mismatch = [single_file
                        for single_file in set(new_iso.file_dict.iterkeys()) & set(old_iso.file_dict.iterkeys())
                        if new_iso.file_dict[single_file]['crc'] != old_iso.file_dict[single_file]['crc']]
        pprint.pprint(set(crc_mismatch))

        print 'Package tests: packages added (new vs old iso)'
        extra_packages = [new_iso.package_dict[package]
                          for package in set(new_iso.package_dict.iterkeys()) - set(old_iso.package_dict.iterkeys())]
        extra_packages_set = set()
        for package in extra_packages:
            extra_packages_set.add(".".join(["-".join([package['name'], package['version'], package['release']]),
                                             package['arch']]))
        pprint.pprint(extra_packages_set)

        print 'Package tests: packages removed (new vs old iso)'
        missing_packages = [old_iso.package_dict[package]
                            for package in set(old_iso.package_dict.iterkeys()) - set(new_iso.package_dict.iterkeys())]
        missing_packages_set = set()
        for package in missing_packages:
            missing_packages_set.add(".".join(["-".join([package['name'], package['version'], package['release']]),
                                               package['arch']]))
        pprint.pprint(missing_packages_set)

    if args.key_id is None:
        print "Skipping tests requiring Key ID"
    else:
        print 'Package tests: possibly unsigned (new iso only)'
        unsigned_packages = [k
                             for k, v in new_iso.package_dict.iteritems()
                             if v['signature'] != args.key_id]
        pprint.pprint(set(unsigned_packages))

    print 'Package tests: missing source (new iso only)'
    source_names = [v['name']
                    for v in new_iso.file_dict.itervalues()
                    if len(v['name']) > 8 and v['name'][-8:] == '.src.rpm']
    missing_source_rpms = [v['source']
                           for v in new_iso.package_dict.itervalues()
                           if not v['source'] in source_names]
    pprint.pprint(set(missing_source_rpms))

    if args.arch is None:
        print "Skipping tests requiring target architecture"
    else:
        print 'Package tests: wrong arch (new iso only)'
        wrong_arch_packages = [package
                               for package in new_iso.package_dict.itervalues()
                               if not package['arch'] in [args.arch, 'source', 'noarch']]
        wrong_arch_packages_set = set()
        for package in wrong_arch_packages:
            wrong_arch_packages_set.add(".".join(["-".join([package['name'], package['version'], package['release']]),
                                                  package['arch']]))
        pprint.pprint(wrong_arch_packages_set)


main()
