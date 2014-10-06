# -*- encoding: utf-8 -*-
"""
statidhcpdlib.web.methods
=========================
Provides implementations of several helpful web-components.
 
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
"""
import logging

from .. import config
from .. import logging_handlers
from ..import system
import functions
import _resources

_logger = logging.getLogger('web.methods')

_SEVERITY_MAP = {
 logging.DEBUG: 'debug',
 logging.INFO: 'info',
 logging.WARN: 'warn',
 logging.ERROR: 'error',
 logging.CRITICAL: 'critical',
} #: Mappings to show logging data in the web interface

class Logger(object):
    """
    A logging mechanism to provide a web-interface view of what's going on in
    the system.
    """
    _handler = None #: The loging handler
    
    def __init__(self):
        """
        Initialises and registers the logging handler.
        """
        _logger.info("Configuring web-accessible logging...")
        self._handler = logging_handlers.FIFOHandler(config.WEB_LOG_HISTORY)
        self._handler.setLevel(getattr(logging, config.WEB_LOG_SEVERITY))
        if config.DEBUG:
            self._handler.setFormatter(logging.Formatter("%(asctime)s : %(levelname)s : %(name)s : %(message)s"))
        else:
            self._handler.setFormatter(logging.Formatter("%(asctime)s : %(message)s"))
        _logger.root.addHandler(self._handler)
        _logger.info("Web-accessible logging online; buffer-size=" + str(config.WEB_LOG_HISTORY))
        
    def render(self, *args, **kwargs):
        """
        Generates a view of the current log.
        
        :return str: An HTML fragment, containing the log.
        """
        global _SEVERITY_MAP
        output = []
        for (severity, line) in self._handler.readContents():
            output.append('<span class="%(severity)s">%(message)s</span>' % {
             'severity': _SEVERITY_MAP[severity],
             'message': functions.sanitise(line).replace('\n', '<br/>'),
            })
            
        return """
        <div style='overflow-y: auto;%(max-height)s'>
        %(lines)s
        </div>""" % {
         'max-height': config.WEB_LOG_MAX_HEIGHT and ' max-height: %(max-height)ipx;' % {
          'max-height': config.WEB_LOG_MAX_HEIGHT,
         },
         'lines': '<br/>\n'.join(output),
        }
        
def reinitialise(*args, **kwargs):
    """
    Runs the reinitialisation sequence over the system.
    
    :return str: An HTML fragment, describing the result.
    """
    try:
        time_elapsed = system.reinitialise()
    except Exception, e:
        return '<span class="critical">Reinitilisation failed: %(error)s</span>' % {
         'error': str(e),
        }
    else:
        return 'System reinitilisation completed in %(time).4f seconds' % {
         'time': time_elapsed,
        }
        
def css(*args, **kwargs):
    """
    Produces the default CSS.
    
    :return str: The CSS byte-string.
    """
    return ('text/css', _resources.CSS)
    
def javascript(*args, **kwargs):
    """
    Produces the default JavaScript.
    
    :return str: The JavaScript byte-string.
    """
    return ('text/javascript', _resources.JS)
    
def favicon(*args, **kwargs):
    """
    Produces the default favicon.
    
    :return str: The favicon byte-string.
    """
    return ('image/x-icon', _resources.FAVICON)
    
