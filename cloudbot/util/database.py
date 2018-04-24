"""
database - contains variables set by cloudbot to be easily access
"""

from sqlalchemy.ext.declarative import declarative_base as _declarative_base

Base = _declarative_base()
metadata = Base.metadata


class ContextSession:
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
