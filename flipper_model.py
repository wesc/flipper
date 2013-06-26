
import time

import sqlite3


class FlipperModel(object):
    def __init__(self, db_filename=':memory:'):
        self.conn = sqlite3.connect(db_filename)

    def init_tables(self):
        """
        Creates tables in database. Can only be called once per
        database. Returns True on success, False for all error
        conditions.
        """

        try:
            with self.conn:
                self.conn.execute("CREATE TABLE users ("
                                  "username TEXT PRIMARY KEY, "
                                  "registration_time INTEGER, " # seconds since epoch
                                  "password TEXT"
                                  ")")
                return True
        except sqlite3.Error, e:
            pass

        return False

    def create_user(self, username, password):
        """
        Takes a username and a password and creates this user in the
        database. Return True on success, False on all error
        conditions, including attempts to create a user tha already
        exists.

        >>> fm = FlipperModel()
        >>> fm.init_tables()
        True
        >>> fm.create_user('wes', 'wespass')
        True
        """

        try:
            with self.conn:
                self.conn.execute("INSERT INTO users (username, password, registration_time) "
                                  "VALUES (?, ?, ?)",
                                  (username, password, time.time()))
                return True
        except sqlite3.Error, e:
            pass

        return False

    def get_user(self, username):
        """
        Looks up the user by username.

        >>> fm = FlipperModel()
        >>> fm.init_tables()
        True
        >>> fm.create_user('wes', 'wespass')
        True
        >>> fm.get_user('wes')['password'] == 'wespass'
        True
        """

        try:
            return self._fetchone("SELECT * FROM users WHERE username = ?", (username, ))
        except sqlite3.Error, e:
            pass

        return False

    def _fetchone(self, sel, params=[]):
        """
        Helper function that selects a single row using the given
        select statement and parameters, and constructs a dictionary
        of column names to values. Returns None if no entry
        found. Passes through any db exceptions.
        """

        with self.conn:
            cur = self.conn.execute(sel, params)
            columns = [c[0] for c in cur.description]
            row = cur.fetchone()
            if row:
                return dict(zip(columns, row))
            else:
                return None

    def _fetchall(self, sel, params=[]):
        """
        Helper function that selects all rows using the given select
        statement and parameters, and constructs a list of
        dictionaries of column names to values. Returns empty list if
        no entry found. Passes through any db exceptions.
        """

        with self.conn:
            cur = self.conn.execute(sel, params)
            columns = [c[0] for c in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
