#!/usr/bin/env python3

# Copyright (C) 2009 by Thomas Petazzoni <thomas.petazzoni@free-electrons.com>
# Copyright (C) 2020 by Gregory CLEMENT <gregory.clement@bootlin.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

import distutils.version
import operator
from nvd_api_v2 import NVD_API
from cpe import CPE_ID


class CVE:
    """An accessor class for CVE Items in NVD files"""
    CVE_AFFECTS = 1
    CVE_DOESNT_AFFECT = 2
    CVE_UNKNOWN = 3

    ops = {
        '>=': operator.ge,
        '>': operator.gt,
        '<=': operator.le,
        '<': operator.lt,
        '=': operator.eq
    }

    def __init__(self, nvd_cve):
        """Initialize a CVE from the database tuple representation"""
        self.id = nvd_cve[0]
        self.match_criteria = nvd_cve[2]
        self.v_start = nvd_cve[3]
        self.v_end = nvd_cve[4]
        self.op_start = nvd_cve[5]
        self.op_end = nvd_cve[6]

    @property
    def identifier(self):
        """The CVE unique identifier"""
        return self.id

    @property
    def affected_product(self):
        """Name of the affected product"""
        return CPE_ID.product(self.match_criteria)

    def affects(self, name, version, cve_ignore_list, cpeid=None):
        """
        True if the Buildroot Package object passed as argument is affected
        by this CVE.
        """
        if self.identifier in cve_ignore_list:
            return self.CVE_DOESNT_AFFECT

        pkg_version = distutils.version.LooseVersion(version)
        if not hasattr(pkg_version, "version"):
            print("Cannot parse package '%s' version '%s'" % (name, version))
            pkg_version = None

        # if we don't have a cpeid, build one based on name and version
        if not cpeid:
            cpeid = "cpe:2.3:*:*:%s:%s:*:*:*:*:*:*:*" % (name, version)
        # if we have a cpeid, use its version instead of the package
        # version, as they might be different due to
        # <pkg>_CPE_ID_VERSION
        else:
            pkg_version = distutils.version.LooseVersion(CPE_ID.version(cpeid))

        if not CPE_ID.matches(self.match_criteria, cpeid):
            return self.CVE_DOESNT_AFFECT
        if not self.v_start and not self.v_end:
            return self.CVE_AFFECTS
        if not pkg_version:
            return self.CVE_DOESNT_AFFECT

        if self.v_start:
            try:
                cve_affected_version = distutils.version.LooseVersion(self.v_start)
                inrange = self.ops.get(self.op_start)(pkg_version, cve_affected_version)
            except TypeError:
                return self.CVE_UNKNOWN

            # current package version is before v_start, so we're
            # not affected by the CVE
            if not inrange:
                return self.CVE_DOESNT_AFFECT

        if self.v_end:
            try:
                cve_affected_version = distutils.version.LooseVersion(self.v_end)
                inrange = self.ops.get(self.op_end)(pkg_version, cve_affected_version)
            except TypeError:
                return self.CVE_UNKNOWN

            # current package version is after v_end, so we're
            # not affected by the CVE
            if not inrange:
                return self.CVE_DOESNT_AFFECT

        # We're in the version range affected by this CVE
        return self.CVE_AFFECTS


class CVE_API(NVD_API):
    """Download and manage CVEs in a sqlite database."""
    def __init__(self, nvd_path):
        """ Create a new API and database endpoint."""
        NVD_API.__init__(self, nvd_path, 'CVEs', 'nvdcve')

    def init_db(self):
        """
        Create all tables if the are missing.
        """
        cursor = self.db_connection.cursor()

        cursor.execute('CREATE TABLE IF NOT EXISTS cves (\
            id TEXT UNIQUE, \
            description TEXT, \
            metric2 REAL, \
            metric3 REAL, \
            severity TEXT)')

        cursor.execute('CREATE TABLE IF NOT EXISTS cpe_matches (\
            id TEXT UNIQUE, \
            criteria TEXT, \
            version_start TEXT, \
            version_end TEXT, \
            operator_start TEXT, \
            operator_end TEXT)')

        cursor.execute('CREATE TABLE IF NOT EXISTS configurations (\
            cve_id TEXT, \
            cpe_match_id TEXT, \
            FOREIGN KEY (cve_id) REFERENCES cve (id) ON DELETE CASCADE, \
            FOREIGN KEY (cpe_match_id) REFERENCES cpe_match (id) ON DELETE CASCADE, \
            UNIQUE (cve_id, cpe_match_id))')

        cursor.close()

    def extract_cve_data(self, cve):
        """Map CVE API data to database fields."""
        description = ''
        for d in cve['descriptions']:
            if d['lang'] == 'en':
                description = d['value']
        metric2 = 0.0
        metric3 = 0.0
        severity = 'UNKNOWN'
        if 'cvssMetricV31' in cve['metrics']:
            metric3 = cve['metrics']['cvssMetricV31'][0]['cvssData']['baseScore']
            severity = cve['metrics']['cvssMetricV31'][0]['cvssData']['baseSeverity']
        elif 'cvssMetricV30' in cve['metrics']:
            metric3 = cve['metrics']['cvssMetricV30'][0]['cvssData']['baseScore']
            severity = cve['metrics']['cvssMetricV30'][0]['cvssData']['baseSeverity']
        elif 'cvssMetricV2' in cve['metrics']:
            metric2 = cve['metrics']['cvssMetricV2'][0]['cvssData']['baseScore']
            severity = cve['metrics']['cvssMetricV2'][0]['baseSeverity']

        return [cve['id'], description, metric2, metric3, severity]

    def extract_cpe_match_data(self, cpe_match):
        """Map CPE match information to database fields."""
        product = CPE_ID.product(cpe_match['criteria'])
        version = CPE_ID.version(cpe_match['criteria'])
        # ignore when product is '-', which means N/A
        if product == '-':
            return
        op_start = ''
        op_end = ''
        v_start = ''
        v_end = ''

        if version != '*' and version != '-':
            # Version is defined, this is a '=' match
            op_start = '='
            v_start = version
        else:
            # Parse start version, end version and operators
            if 'versionStartIncluding' in cpe_match:
                op_start = '>='
                v_start = cpe_match['versionStartIncluding']

            if 'versionStartExcluding' in cpe_match:
                op_start = '>'
                v_start = cpe_match['versionStartExcluding']

            if 'versionEndIncluding' in cpe_match:
                op_end = '<='
                v_end = cpe_match['versionEndIncluding']

            if 'versionEndExcluding' in cpe_match:
                op_end = '<'
                v_end = cpe_match['versionEndExcluding']

        return [
            cpe_match['matchCriteriaId'],
            cpe_match['criteria'],
            v_start,
            v_end,
            op_start,
            op_end
        ]

    def save_to_db(self, content) -> bool:
        """
        Save the response of a single API request to the database
        and report the progress.
        """
        cve_ids_changed = list()
        cve_ids_dropped = list()
        cves = list()
        cpe_matches = list()
        configurations = list()

        for vul in content['vulnerabilities']:
            if vul['cve']['vulnStatus'] == 'Rejected':
                cve_ids_dropped.append((vul['cve']['id'],))
                continue

            cve_ids_changed.append((vul['cve']['id'],))
            cves.append(self.extract_cve_data(vul['cve']))

            for config in vul['cve'].get('configurations', ()):
                for node in config['nodes']:
                    for cpe_match in node['cpeMatch']:
                        if not cpe_match['vulnerable']:
                            continue
                        match_data = self.extract_cpe_match_data(cpe_match)
                        if not match_data:
                            continue
                        cpe_matches.append(match_data)
                        configurations.append([vul['cve']['id'], match_data[0]])

        cursor = self.db_connection.cursor()

        # Drop all CVEs that are rejected, status might have changed
        cursor.executemany('DELETE FROM cves WHERE id = ?', cve_ids_dropped)

        # Delete configuration mapping for included CVEs, otherwise we can't detect
        # upstream dropping configurations.
        cursor.executemany('DELETE FROM configurations WHERE cve_id = ?', cve_ids_changed)
        cursor.executemany('INSERT OR REPLACE INTO cves VALUES (?, ?, ?, ?, ?)', cves)
        cursor.executemany('INSERT OR REPLACE INTO cpe_matches VALUES (?, ?, ?, ?, ?, ?)', cpe_matches)
        cursor.executemany('INSERT OR REPLACE INTO configurations VALUES (?, ?)', configurations)

        cursor.close()

        return True

    def load_all(self):
        """
        Load all entries from the database and use CVE class
        to yield each result individually.
        Each yielded object represents one configuration that
        the included CVE is vulnerable for.
        """
        self.check_for_updates()

        cursor = self.db_connection.cursor()
        sql = 'SELECT c.id as cve_id, m.id, m.criteria, m.version_start, m.version_end, \
            m.operator_start, m.operator_end \
            FROM configurations \
            INNER JOIN cves AS c ON c.id = configurations.cve_id \
            INNER JOIN cpe_matches AS m ON m.id = configurations.cpe_match_id \
            ORDER BY cve_id'

        for row in cursor.execute(sql):
            yield CVE(row)

        cursor.close()
        self.db_connection.close()
