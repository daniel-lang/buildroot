#!/usr/bin/env python3

from datetime import datetime, timezone
import os
import requests
import shutil
import sqlite3
import time

NVD_API_VERSION = '2.0'
NVD_API_BASE_URL = 'https://services.nvd.nist.gov/rest/json'


class NVD_API:
    """
    A helper class that fetches data from a NVD API and
    helps manage a sqlite database.
    """
    def __init__(self, nvd_path, service, database_file_prefix):
        """
        Initialize a new NVD API endpoint with service
        as the URL postfix.
        """
        self.nvd_path = nvd_path
        self.service = service
        self.url = '%s/%s/%s' % (NVD_API_BASE_URL, service.lower(), NVD_API_VERSION)
        self.db_file = os.path.join(nvd_path, '%s-%s.sqlite' % (database_file_prefix, NVD_API_VERSION))
        self.db_file_tmp = '%s.tmp' % self.db_file

    def init_db(self):
        """
        Needs to be implemented by derived classes.
        Used to make sure that database tables exist.
        """
        pass

    def save_to_db(self, start_index, total_results, content):
        """
        Needs to be implemented by derived classes.
        Used to save the data given by a single API request
        to the database.
        """
        pass

    def cleanup_db(self):
        """
        Clean up any files that where left by previously
        failed runs.
        """
        if os.path.exists(self.db_file_tmp):
            os.remove(self.db_file_tmp)

    def open_db(self, tmp=False):
        """
        Open and return a connection to the sqlite database.
        """
        if tmp:
            return sqlite3.connect(self.db_file_tmp)
        return sqlite3.connect(self.db_file)

    def download(self, last_update):
        """
        Download all entries from NVD since last_update (if not None).
        For each downloaded page save_to_db is called to together with
        progress information.
        NVD rate limiting allows 5 requests per 30 seconds or one every
        6 seconds.
        """
        args = {}
        start_index = 0
        total_results = 0
        results_per_page = 0

        print('Downloading new %s' % self.service)

        if (last_update is not None):
            args['lastModStartDate'] = last_update.isoformat()
            args['lastModEndDate'] = datetime.now(tz=timezone.utc).isoformat()

        while True:
            args['startIndex'] = start_index

            for attempt in range(5):
                try:
                    page = requests.get(self.url, params=args)
                    page.raise_for_status()
                    content = page.json()
                except Exception:
                    time.sleep(6)
                else:
                    break

            if content is None:
                # Nothing was downloaded
                return False

            results_per_page = content['resultsPerPage']
            total_results = content['totalResults']
            start_index = content['startIndex']

            start_index += results_per_page

            if self.save_to_db(start_index, total_results, content) is not True:
                return False

            self.connection.commit()

            if start_index >= total_results:
                return True

            # Otherwise rate limiting will be hit.
            time.sleep(6)

    def check_for_updates(self):
        """
        Check if the database file exists and if the last
        update was more than 24 hours ago.
        """
        self.cleanup_db()
        last_update = None
        if os.path.exists(self.db_file):
            last_update = os.stat(self.db_file).st_mtime
            if last_update >= time.time() - 86400:
                return []
            # NVD uses UTC timestamps
            last_update = datetime.fromtimestamp(last_update, tz=timezone.utc)
            shutil.copy2(self.db_file, self.db_file_tmp)

        self.connection = self.open_db(True)
        self.init_db()

        success = self.download(last_update)
        self.connection.close()
        if success:
            shutil.move(self.db_file_tmp, self.db_file)
        else:
            print("Update failed!")
            os.remove(self.db_file_tmp)
