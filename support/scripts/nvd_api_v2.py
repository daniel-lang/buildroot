#!/usr/bin/env python3

from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import sqlite3
import time

NVD_API_VERSION = '2.0'
NVD_API_BASE_URL = 'https://services.nvd.nist.gov/rest/json'
# NVD rate limiting allows 5 requests per 30 seconds -> one every 6 seconds.
NVD_SLEEP_TIME_SEC = 30 / 5
# Number of minutes that are subtracted from the update timestap given by NVD.
NVD_TIMESTAMP_SUBTRACT_MINUTES = 1
# Only update the database if the given number of seconds elapsed.
NVD_CHECK_TIMEOUT_SECONDS = 120 * 60


class NVD_API:
    """A helper class that fetches data from a NVD API and helps manage a sqlite database.

    This class defines two functions that need to be implemented in a derived class.
    init_db: Called to create database tables.
    save_to_db: Called to actually analyse and save the downloaded data."""

    def __init__(self, nvd_path, service, database_file_prefix):
        """Initialize a new NVD API endpoint.

        nvd_path             - The local path of the database, typically DL_DIR/buildroot-nvd.
        service              - The service that gets appended to the API URL, should be 'CVEs' or 'CPEs'.
        database_file_prefix - The prefix of the sqlite database, typically 'nvdcve' or 'nvdcpe'.
        """
        self.nvd_path = nvd_path
        self.service = service
        self.url = f'{NVD_API_BASE_URL}/{service.lower()}/{NVD_API_VERSION}'
        self.db_file = Path(nvd_path, f'{database_file_prefix}-{NVD_API_VERSION}.sqlite')
        self.db_connection = None

    def init_db_meta(self) -> None:
        """Create the internal meta table that stores the last update date."""
        self.db_connection.execute('CREATE TABLE IF NOT EXISTS meta ( \
            id INTEGER UNIQUE, \
            last_update TIMESTAMP)').close()

    def init_db(self) -> None:
        """Used to make sure that database tables exist.

        Database connection is active at this point (self.db_connection).
        Needs to be implemented by derived classes.
        """
        pass

    def save_to_db(self, content) -> bool:
        """Used to save the data given by a single API request to the database.

        content is the json downloaded from NVD.
        Needs to be implemented by derived classes.
        """
        pass

    def download(self, last_update) -> None:
        """Download all entries from NVD since last_update (if not None).

        For each downloaded page save_to_db is called.
        """
        args = {}
        start_index = 0
        total_results = 0
        results_per_page = 0

        print(f'Downloading new {self.service}')

        if (last_update is not None):
            args['lastModStartDate'] = last_update.isoformat()
            args['lastModEndDate'] = datetime.now(tz=timezone.utc).isoformat()

        while True:
            args['startIndex'] = start_index

            page = requests.get(self.url, params=args)
            page.raise_for_status()
            content = page.json()

            if content is None:
                # Nothing was downloaded
                return False

            results_per_page = content['resultsPerPage']
            total_results = content['totalResults']
            start_index = content['startIndex']
            timestamp = content['timestamp']

            start_index += results_per_page

            # Call the save method of the derived class
            if not self.save_to_db(content):
                return False

            print(f'[{start_index:0{len(str(total_results))}}/{total_results}]')

            if start_index >= total_results:
                # Update the meta table with the timestamp given by NVD but
                # subtract a minute to make sure nothing is missed the next time.
                timestamp = datetime.fromisoformat(timestamp) - timedelta(minutes=NVD_TIMESTAMP_SUBTRACT_MINUTES)
                self.db_connection.execute('INSERT OR REPLACE INTO meta VALUES (0, ?)', (timestamp,)).close()
                self.db_connection.commit()
                return True

            self.db_connection.commit()

            # Otherwise rate limiting will be hit.
            time.sleep(NVD_SLEEP_TIME_SEC)

    def check_for_updates(self) -> None:
        """Check if new data needs to be fetched from NVD.

        If the last update happened more than 24 hours ago,
        a new download is triggered.
        """
        self.db_connection = sqlite3.connect(self.db_file)
        self.init_db_meta()
        self.init_db()

        last_update = None
        result = self.db_connection.execute('SELECT last_update FROM meta WHERE id = 0').fetchone()
        if result:
            # NVD uses UTC without specifying the timezone on their timestamp
            now = datetime.now(tz=timezone.utc)
            last_update = datetime.fromisoformat(result[0])
            delta = now - last_update.replace(tzinfo=timezone.utc)
            if delta.total_seconds() < NVD_CHECK_TIMEOUT_SECONDS:
                # Don't run the download if the last update
                # is less than two hours ago.
                return

        if not self.download(last_update):
            print('Update failed!')
