"""
database - contains variables set by cloudbot to be easily access
"""
from sqlalchemy import MetaData

__all__ = ("metadata", "base")

# this is assigned in the CloudBot so that its recreated when the bot restarts
metadata = MetaData()
base = None
