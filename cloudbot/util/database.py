"""
database - contains variables set by cloudbot to be easily access
"""

from contextlib import AbstractContextManager

# this is assigned in the CloudBot so that its recreated when the bot restarts
metadata = None
base = None


class ContextSession(AbstractContextManager):
    def __init__(self, session):
        """
        :type session: sqlalchemy.orm.Session
        """
        self._session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            try:
                self.session.commit()
            except Exception:
                self.session.rollback()
                self.session.commit()
                raise
        else:
            self.session.rollback()
            self.session.commit()

        self.session.close()

    @property
    def session(self):
        return self._session
