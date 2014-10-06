# -*- encoding: utf-8 -*-
"""
staticdhcpdlib.databases._sql
=============================
Provides a uniform datasource API, implementing multiple SQL-based backends.
 
Legal
-----
This file is part of staticDHCPd.
staticDHCPd is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

(C) Neil Tallim, 2014 <flan@uguu.ca>
(C) Matthew Boedicker, 2011 <matthewm@boedicker.org>
"""
import logging

from .. import config

from generic import (Definition, CachingDatabase)

_logger = logging.getLogger("databases._sql")
_extra = []
if config.EXTRA_MAPS:
    for i in config.EXTRA_MAPS:
        _extra.append('maps.' + i)
    del i
if config.EXTRA_SUBNETS:
    for i in config.EXTRA_SUBNETS:
        _extra.append('subnets.' + i)
    del i
if not _extra:
    _extra = None
    
    
class _SQLDatabase(CachingDatabase):
    """
    A stub documenting the features an _SQLDatabase object must provide.
    """
    def _getConnection(self):
        """
        Provides a connection to the database.
        
        :return: The connection object to be used.
        :except Exception: A problem occurred while accessing the database.
        """
        raise NotImplementedError("_getConnection must be overridden")
        
class _DB20Broker(_SQLDatabase):
    """
    Defines bevahiour for a DB API 2.0-compatible broker.
    """
    _module = None #: The db2api-compliant module to use
    _connection_details = None #: The module-specific details needed to connect to a database
    _query_mac = None #: The string used to look up a MAC's binding
    
    def _lookupMAC(self, mac):
        mac = str(mac)
        try:
            db = self._getConnection()
            cur = db.cursor()
            
            _logger.debug("Looking up MAC %(mac)s..." % {
             'mac': mac,
            })
            cur.execute(self._query_mac, (mac,))
            result = cur.fetchone()
            if result:
                _logger.debug("Record found for MAC %(mac)s" % {
                 'mac': mac,
                })
                return Definition(
                 ip=result[0], hostname=result[1],
                 gateways=result[2], subnet_mask=result[3], broadcast_address=result[4],
                 domain_name=result[5], domain_name_servers=result[6], ntp_servers=result[7],
                 lease_time=result[8], subnet=result[9], serial=result[10],
                 extra=(_extra and dict(zip(_extra, result[11:])) or None)
                )
            _logger.debug("No record found for MAC %(mac)s" % {
             'mac': mac,
            })
            return None
        finally:
            try:
                cur.close()
            except Exception:
                _logger.warn("Unable to close cursor")
            try:
                db.close()
            except Exception:
                _logger.warn("Unable to close connection")
                
class _PoolingBroker(_DB20Broker):
    """
    Defines bevahiour for a connection-pooling-capable DB API 2.0-compatible
    broker.
    """
    _pool = None #: The database connection pool
    _eventlet__db_pool = None #: A reference to the eventlet.db_pool module
    
    def __init__(self, concurrency_limit):
        """
        Sets up connection-pooling, if it's supported by the environment.
        
        :param int concurrency_limit: The number of concurrent database hits to
                                      permit.
        :except Exception: Failed to initialise pooling layer.
        """
        _DB20Broker.__init__(self, concurrency_limit)

        if config.USE_POOL:
            _logger.debug("Configuring connection-pooling...")
            try:
                import eventlet.db_pool
                self._eventlet__db_pool = eventlet.db_pool
            except ImportError:
                _logger.warn("eventlet is not available; falling back to unpooled mode")
                return
            else:
                self._pool = self._eventlet__db_pool.ConnectionPool(
                 self._module,
                 max_size=concurrency_limit, max_idle=30, max_age=600, connect_timeout=5,
                 **self._connection_details
                )
                
    def _getConnection(self):
        if self._pool is not None:
            return self._eventlet__db_pool.PooledConnectionWrapper(self._pool.get(), self._pool)
        else:
            return self._module.connect(**self._connection_details)
            
class _NonPoolingBroker(_DB20Broker):
    """
    Defines bevahiour for a non-connection-pooling-capable DB API 2.0-compatible
    broker.
    """
    def _getConnection(self):
        return self._module.connect(**self._connection_details)
        
class MySQL(_PoolingBroker):
    """
    Implements a MySQL broker.
    """
    _query_mac = """
     SELECT
      m.ip, m.hostname,
      s.gateway, s.subnet_mask, s.broadcast_address, s.domain_name, s.domain_name_servers,
      s.ntp_servers, s.lease_time, s.subnet, s.serial%(extra)s
     FROM maps m, subnets s
     WHERE
      %(mac)s = %%s AND m.subnet = s.subnet AND m.serial = s.serial
     LIMIT 1
    """ % {
     'mac': config.CASE_INSENSITIVE_MACS and 'LOWER(m.mac)' or 'm.mac',
     'extra': _extra and ','.join(
      [''] + ['m.' + i for i in config.EXTRA_MAPS] + ['s.' + i for i in config.EXTRA_SUBNETS]
     ) or '',
    }
    
    def __init__(self):
        """
        Constructs the broker.
        """
        _PoolingBroker.__init__(self, config.MYSQL_MAXIMUM_CONNECTIONS)
        
        import MySQLdb
        self._module = MySQLdb
        
        self._connection_details = {
         'db': config.MYSQL_DATABASE,
         'user': config.MYSQL_USERNAME,
         'passwd': config.MYSQL_PASSWORD,
        }
        if config.MYSQL_HOST is None:
            self._connection_details['host'] = 'localhost'
        else:
            self._connection_details['host'] = config.MYSQL_HOST
            self._connection_details['port'] = config.MYSQL_PORT
            
        _logger.debug("MySQL configured; connection-details: " + str(self._connection_details))
        
class PostgreSQL(_PoolingBroker):
    """
    Implements a PostgreSQL broker.
    """
    _query_mac = """
     SELECT
      m.ip, m.hostname,
      s.gateway, s.subnet_mask, s.broadcast_address, s.domain_name, s.domain_name_servers,
      s.ntp_servers, s.lease_time, s.subnet, s.serial%(extra)s
     FROM maps m, subnets s
     WHERE
      %(mac)s = %%s AND m.subnet = s.subnet AND m.serial = s.serial
     LIMIT 1
    """ % {
     'mac': config.CASE_INSENSITIVE_MACS and 'lower(m.mac)' or 'm.mac',
     'extra': _extra and ','.join(
      [''] + ['m.' + i for i in config.EXTRA_MAPS] + ['s.' + i for i in config.EXTRA_SUBNETS]
     ) or '',
    }
    
    def __init__(self):
        """
        Constructs the broker.
        """
        _PoolingBroker.__init__(self, config.POSTGRESQL_MAXIMUM_CONNECTIONS)
        
        import psycopg2
        self._module = psycopg2
        
        self._connection_details = {
         'database': config.POSTGRESQL_DATABASE,
         'user': config.POSTGRESQL_USERNAME,
         'password': config.POSTGRESQL_PASSWORD,
        }
        if not config.POSTGRESQL_HOST is None:
            self._connection_details['host'] = config.POSTGRESQL_HOST
            self._connection_details['port'] = config.POSTGRESQL_PORT
            self._connection_details['sslmode'] = config.POSTGRESQL_SSLMODE
            
        _logger.debug("PostgreSQL configured; connection-details: " + str(self._connection_details))
        
class Oracle(_PoolingBroker):
    """
    Implements an Oracle broker.
    """
    _query_mac = """
     SELECT
      m.ip, m.hostname,
      s.gateway, s.subnet_mask, s.broadcast_address, s.domain_name, s.domain_name_servers,
      s.ntp_servers, s.lease_time, s.subnet, s.serial%(extra)s
     FROM maps m, subnets s
     WHERE
      %(mac)s = :1 AND m.subnet = s.subnet AND m.serial = s.serial
     LIMIT 1
    """ % {
     'mac': config.CASE_INSENSITIVE_MACS and 'LOWER(m.mac)' or 'm.mac',
     'extra': _extra and ','.join(
      [''] + ['m.' + i for i in config.EXTRA_MAPS] + ['s.' + i for i in config.EXTRA_SUBNETS]
     ) or '',
    }

    def __init__(self):
        """
        Constructs the broker.
        """
        _PoolingBroker.__init__(self, config.ORACLE_MAXIMUM_CONNECTIONS)
        
        import cx_Oracle
        self._module = cx_Oracle
        
        self._connection_details = {
         'user': config.ORACLE_USERNAME,
         'password': config.ORACLE_PASSWORD,
         'dsn': config.ORACLE_DATABASE,
        }
        
        _logger.debug("Oracle configured; connection-details: " + str(self._connection_details))

class SQLite(_NonPoolingBroker):
    """
    Implements a SQLite broker.
    """
    _query_mac = """
     SELECT
      m.ip, m.hostname,
      s.gateway, s.subnet_mask, s.broadcast_address, s.domain_name, s.domain_name_servers,
      s.ntp_servers, s.lease_time, s.subnet, s.serial%(extra)s
     FROM maps m, subnets s
     WHERE
      %(mac)s = ? AND m.subnet = s.subnet AND m.serial = s.serial
     LIMIT 1
    """ % {
     'mac': config.CASE_INSENSITIVE_MACS and 'lower(m.mac)' or 'm.mac',
     'extra': _extra and ','.join(
      [''] + ['m.' + i for i in config.EXTRA_MAPS] + ['s.' + i for i in config.EXTRA_SUBNETS]
     ) or '',
    }
    
    def __init__(self):
        """
        Constructs the broker.
        """
        _NonPoolingBroker.__init__(self, 1)
        
        import sqlite3
        self._module = sqlite3
        
        self._connection_details = {
         'database': config.SQLITE_FILE,
        }
        
        _logger.debug("SQLite configured; connection-details: " + str(self._connection_details))
