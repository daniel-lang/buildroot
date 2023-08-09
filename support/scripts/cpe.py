#!/usr/bin/env python3

from nvd_api_v2 import NVD_API


class CPE_ID:
    @staticmethod
    def matches(cpe1, cpe2):
        """Check if two CPE IDs match each other"""
        cpe1_elems = cpe1.split(":")
        cpe2_elems = cpe2.split(":")

        remains = filter(lambda x: x[0] not in ["*", "-"] and x[1] not in ["*", "-"] and x[0] != x[1],
                         zip(cpe1_elems, cpe2_elems))
        return len(list(remains)) == 0

    @staticmethod
    def product(cpe):
        return cpe.split(':')[4]

    @staticmethod
    def version(cpe):
        return cpe.split(':')[5]

    @staticmethod
    def no_version(cpe):
        return ":".join(cpe.split(":")[:5])


class CPE_API(NVD_API):
    def __init__(self, nvd_path):
        NVD_API.__init__(self, nvd_path, 'CPEs', 'nvdcpe')
        self.cpes = list()
        self.cpes_without_version = dict()

    def init_db(self):
        cursor = self.connection.cursor()

        cursor.execute('CREATE TABLE IF NOT EXISTS products ( \
            id TEXT UNIQUE, \
            name TEXT)')

        cursor.close()

    def save_to_db(self, start_index, total_results, content):
        cpe_ids_dropped = list()
        products = list()

        for product in content['products']:
            if product['cpe']['deprecated']:
                cpe_ids_dropped.append((product['cpe']['cpeNameId'],))
                continue

            cpe = product['cpe']

            products.append([cpe['cpeNameId'], cpe['cpeName']])

        cursor = self.connection.cursor()

        # Drop all CPEs that are deprecated, status might have changed
        cursor.executemany('DELETE FROM products WHERE id = ?', cpe_ids_dropped)
        cursor.executemany('INSERT OR REPLACE INTO products VALUES (?, ?)', products)

        print("[%07d/%07d]" % (start_index, total_results))

        return True

    def load_ids(self):
        self.check_for_updates()

        self.connection = self.open_db()
        cursor = self.connection.cursor()

        ids = list()
        for row in cursor.execute('SELECT name FROM products'):
            ids.append(row[0])

        cursor.close()
        self.connection.close()

        self.cpes = ids
        return ids

    def generate_partials(self):
        self.cpes_without_version = dict()
        for cpe in self.cpes:
            self.cpes_without_version[CPE_ID.no_version(cpe)] = cpe

    def find_partial(self, cpe_id):
        cpe_id_without_version = CPE_ID.no_version(cpe_id)
        if cpe_id_without_version in self.cpes_without_version.keys():
            return self.cpes_without_version[cpe_id_without_version]
