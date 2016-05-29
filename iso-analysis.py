#!/usr/bin/python2

# for RPM based distributions, analyse given ISO and compare with the old one
# v0.21
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
import rpmUtils.miscutils
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


class RpmPackage:
    def __init__(self):
        pass

    @staticmethod
    def __package_data__(package_raw_data):
        return {
            'name': package_raw_data[0],
            'version': package_raw_data[1],
            'release': package_raw_data[2],
            'arch': package_raw_data[3],
            'source': package_raw_data[4],
            'signature': package_raw_data[-1][-8:]}


class MountedIso(RpmPackage):
    def __init__(self, iso_uri):
        RpmPackage.__init__(self)
        self.temp_dir = tempfile.mkdtemp()
        if '.iso' == iso_uri[-4:]:
            run('mount -o ro,loop %s %s' % (iso_uri, self.temp_dir,))
            self.type = 'iso'
        elif '.raw' == iso_uri[-4:]:
            try:
                start_at = int(run('fdisk -l %s 2>/dev/null| tail -1' % iso_uri).split()[1])
            except ValueError:
                start_at = int(run('fdisk -l %s 2>/dev/null| tail -1' % iso_uri).split()[2])
            run('mount -o ro,loop,offset=%d %s %s' % (start_at * 512, iso_uri, self.temp_dir,))
            self.type = 'image'
        elif '.qcow2' == iso_uri[-6:]:
            mount_point = run("guestmount -a %s -m /dev/sdx1 %s 2>&1 | grep -e ext4 -e xfs | awk '{ print $2 }'" % (iso_uri, self.temp_dir))
            if not mount_point:
                output = run("guestmount -a %s -m /dev/sdx1 %s" % (iso_uri, self.temp_dir))
                print output
                sys.exit(1)
            run("guestmount -a %s -m %s %s 2>&1 | grep -e ext4 -e xfs | awk '{ print $2 }'" % (iso_uri, mount_point.strip(), self.temp_dir))
            self.type = 'image'
        else:
            sys.exit(1)
        print "ISO Analysing files"
        self.file_dict = self.__get_files__()
        print "ISO Analysing packages"
        self.package_dict = self.__get_packages__()

    def __del__(self):
        run('umount %s' % self.temp_dir)

    def __get_files__(self):
        def add_file(file_type):
            single_file_path = os.path.join(root[len(self.temp_dir) + 1:], single_file)
            single_file_crc = run("md5sum %s" % (os.path.join(root, single_file))).split()[0]
            file_dict[single_file_path] = {'name': single_file, 'type': file_type, 'crc': single_file_crc}

        file_dict = {}
        if self.type == 'iso':
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
        def parse_data(data):
            if k[-8:] == '.src.rpm' and self.type == 'iso':
                data[3] = 'source'
                data[4] = os.path.split(k)[-1]
            package_dict['%s.%s' % (data[0], data[3],)] = \
                RpmPackage.__package_data__(data)

        package_dict = {}
        query_string = "rpm -q --qf='%{name} %{version} %{release} %{arch} %{sourcerpm} %{SIGPGP:pgpsig}' "\
                       "--nosignature "

        if self.type == 'iso':
            for k, v in self.file_dict.iteritems():
                if v['type'] == 'rpm':
                    package_raw_data = run("%s -p %s" % (query_string, os.path.join(self.temp_dir, k))).split()
                    parse_data(package_raw_data)
        elif self.type == 'image':
            for k in filter(bool, (run('rpm -qa --dbpath=%s/var/lib/rpm' % self.temp_dir)).split('\n')):
                package_raw_data = run("%s --dbpath=%s/var/lib/rpm %s" % (query_string, self.temp_dir, k)).split()
                parse_data(package_raw_data)

        return package_dict


class YumRepos(RpmPackage):
    def __init__(self, repofrompath):
        RpmPackage.__init__(self)
        print "YUM Analysing packages"
        self.package_dict = self.__get_packages__(repofrompath)

    @staticmethod
    def __get_packages__(repofrompath):
        repos_define = ''
        repos_enable = ''
        for k in repofrompath:
            repos_define += ' --repofrompath=%s ' % k
            if repos_enable:
                repos_enable += ',%s' % k.split(',')[0]
            else:
                repos_enable += '%s' % k.split(',')[0]
        print repos_define
        print repos_enable
        package_dict = {}
        package_list = run("repoquery %s --disablerepo='*' --enablerepo=%s "
                           "--qf='%%{name} %%{version} %%{release} %%{arch} %%{sourcerpm} none' --all"
                           % (repos_define, repos_enable, ))
        for package_raw_data in package_list.split('\n'):
            if package_raw_data:
                package_raw_data_split = package_raw_data.split()
                package_dict['%s.%s' % (package_raw_data_split[0], package_raw_data_split[3],)] = \
                    RpmPackage.__package_data__(package_raw_data_split)
        return package_dict


def main():
    parser = optparse.OptionParser()
    parser.add_option("--new-iso", dest="new_iso", help="URI of binary content for validation (new)")
    parser.add_option("--source-iso", dest="source_iso", help="URI of source content for validation (new)")
    parser.add_option("--old-iso", dest="old_iso", help="URI of content for reference (old)")
    parser.add_option("--arch", dest="arch", help="Target architecture (x86_64, i686...)")
    parser.add_option("--key-id", dest="key_id", action="append",
                      help="Package signing Key ID (can be specified multiple times)")
    parser.add_option("--repo-comparison", dest="repo_comparison", action="store_true",
                      help="Compare ISO packages NVRs to the available yum repos")
    parser.add_option("--repofrompath", dest="repofrompath", action="append",
                      help="Specify repoid & path or url to additional repository (same path as in a baseurl) - unique"
                      " repoid and complete path required, can be specified multiple times. "
                      "Example. --repofrompath=<repoid>,<path/url>")

    args, _ = parser.parse_args()

    print
    print
    if args.new_iso is None:
        print "URI of ISO image for validation (--new_iso) is mandatory"
        sys.exit(1)
    print "# Analysing %s as new iso" % args.new_iso
    new_iso = MountedIso(args.new_iso)

    print
    print
    if args.old_iso is None:
        print "# Skipping tests requiring old iso"
    else:
        print "# Analysing %s as old iso" % args.old_iso
        old_iso = MountedIso(args.old_iso)

        ###############################################################################################################
        print
        print
        print "# File (non-rpm) tests (added, removed, changed)"
        print "(skipping files with .rpm suffix)"

        print
        print '## File (non-rpm) tests: files added (new vs old iso)'
        extra_files = [k
                       for k, v in new_iso.file_dict.iteritems()
                       if k in set(new_iso.file_dict.iterkeys()) - set(old_iso.file_dict.iterkeys())
                       and v['type'] == 'none']
        pprint.pprint(set(extra_files))

        print
        print '## File (non-rpm) tests: files removed (new vs old iso)'
        missing_files = [k
                         for k, v in old_iso.file_dict.iteritems()
                         if k in set(old_iso.file_dict.iterkeys()) - set(new_iso.file_dict.iterkeys())
                         and v['type'] == 'none']
        pprint.pprint(set(missing_files))

        print
        print '## File (non-rpm) tests: changed files (new vs old iso)'
        crc_mismatch = [single_file
                        for single_file in set(new_iso.file_dict.iterkeys()) & set(old_iso.file_dict.iterkeys())
                        if new_iso.file_dict[single_file]['crc'] != old_iso.file_dict[single_file]['crc']]
        pprint.pprint(set(crc_mismatch))

        ###############################################################################################################
        print
        print
        print "# Package (rpm) tests (added, removed)"
        print "(only files with .rpm suffix included)"

        print
        print '## Package tests: packages added (new vs old iso)'
        extra_packages = [new_iso.package_dict[package]
                          for package in set(new_iso.package_dict.iterkeys()) - set(old_iso.package_dict.iterkeys())
                          if new_iso.package_dict[package]['arch'] != 'source']
        extra_packages_set = set()
        for package in extra_packages:
            extra_packages_set.add(".".join(["-".join([package['name'], package['version'], package['release']]),
                                             package['arch']]))
        pprint.pprint(extra_packages_set)

        print
        print '## Package tests: packages removed (new vs old iso)'
        missing_packages = [old_iso.package_dict[package]
                            for package in set(old_iso.package_dict.iterkeys()) - set(new_iso.package_dict.iterkeys())
                            if old_iso.package_dict[package]['arch'] != 'source']
        missing_packages_set = set()
        for package in missing_packages:
            missing_packages_set.add(".".join(["-".join([package['name'], package['version'], package['release']]),
                                               package['arch']]))
        pprint.pprint(missing_packages_set)

        # Package (.rpm suffix) changed is missing, since we are comparing only package name. So the same package name
        # can have different version, release, architecture, signature

        iso_version_older_set = set()
        iso_version_newer_set = set()
        iso_extra_package_set = set()
        for k, v in new_iso.package_dict.iteritems():
            if v['arch'] != 'source':
                try:
                    comparison = rpmUtils.miscutils.compareEVR((old_iso.package_dict[k]['name'],
                                                                old_iso.package_dict[k]['version'],
                                                                old_iso.package_dict[k]['release']),
                                                               (v['name'],
                                                                v['version'],
                                                                v['release']))
                    if comparison < 0:
                        iso_version_newer_set.add(".".join(["-".join([v['name'], v['version'],
                                                                      v['release']]), v['arch']]))
                    elif comparison > 0:
                        iso_version_older_set.add(".".join(["-".join([v['name'], v['version'],
                                                                      v['release']]), v['arch']]))
                except KeyError:
                    iso_extra_package_set.add(".".join(["-".join([v['name'], v['version'],
                                                                  v['release']]), v['arch']]))
        print
        print "## Package tests: packages upgraded (new vs old iso)"
        pprint.pprint(iso_version_newer_set)
        print
        print "## Package tests: packages downgraded (new vs old iso)"
        pprint.pprint(iso_version_older_set)

    ###################################################################################################################
    print
    print
    if args.key_id is None:
        print "# Skipping tests requiring Key ID"
    else:
        print '# Package tests: possibly unsigned (new iso only)'
        unsigned_packages = [k
                             for k, v in new_iso.package_dict.iteritems()
                             if v['signature'] not in args.key_id]
        pprint.pprint(set(unsigned_packages))

    ###################################################################################################################
    print
    print
    if args.source_iso is None:
        print "# Skipping tests requiring source content (new)"
    else:
        print '# Package tests: missing source (new iso only)'
        print "# Analysing %s as source iso (new)" % args.source_iso
        source_iso = MountedIso(args.source_iso)
        source_names = [v['name']
                        for v in source_iso.file_dict.itervalues()
                        if len(v['name']) > 8 and v['name'][-8:] == '.src.rpm']

        missing_source_rpms = [v['source']
                               for v in new_iso.package_dict.itervalues()
                               if not v['source'] in source_names]
        pprint.pprint(set(missing_source_rpms))

    ###################################################################################################################
    print
    print
    if args.arch is None:
        print "# Skipping tests requiring target architecture"
    else:
        print '# Package tests: wrong arch (new iso only)'
        wrong_arch_packages = [package
                               for package in new_iso.package_dict.itervalues()
                               if not package['arch'] in [args.arch, 'source', 'noarch']]
        wrong_arch_packages_set = set()
        for package in wrong_arch_packages:
            wrong_arch_packages_set.add(".".join(["-".join([package['name'], package['version'], package['release']]),
                                                  package['arch']]))
        pprint.pprint(wrong_arch_packages_set)

    ###################################################################################################################
    print
    print
    if args.repo_comparison is None:
        print "# Skipping tests requiring repos"
    else:
        print '# Package tests: comparing ISO with yum repos'
        repo_packages = YumRepos(args.repofrompath)
        iso_version_older_set = set()
        iso_version_newer_set = set()
        iso_extra_package_set = set()
        for k, v in new_iso.package_dict.iteritems():
            if v['arch'] != 'source':
                try:
                    comparison = rpmUtils.miscutils.compareEVR((repo_packages.package_dict[k]['name'],
                                                                repo_packages.package_dict[k]['version'],
                                                                repo_packages.package_dict[k]['release']),
                                                               (v['name'],
                                                                v['version'],
                                                                v['release']))
                    if comparison < 0:
                        iso_version_newer_set.add(".".join(["-".join([v['name'], v['version'],
                                                                      v['release']]), v['arch']]))
                    elif comparison > 0:
                        iso_version_older_set.add(".".join(["-".join([v['name'], v['version'],
                                                                      v['release']]), v['arch']]))
                except KeyError:
                    iso_extra_package_set.add(".".join(["-".join([v['name'], v['version'],
                                                                  v['release']]), v['arch']]))
        print
        print "## Unreleased version (newer on ISO, older in yum repos)"
        pprint.pprint(iso_version_newer_set)
        print
        print "## Not updated packages (older on ISO, newer in yum repos)"
        pprint.pprint(iso_version_older_set)
        print
        print "## Packages on ISO, missing in yum repos"
        pprint.pprint(iso_extra_package_set)
        print
        print "## Packages in yum repos, missing on ISO"
        print "(out of scope of this tool, skipped)"


main()
