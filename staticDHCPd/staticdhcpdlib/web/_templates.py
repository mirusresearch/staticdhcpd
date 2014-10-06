# -*- encoding: utf-8 -*-
"""
staticdhcpdlib.web._templated
=============================
Handles all core templating requirements for rendering things like the
dashboard.

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
import datetime
import traceback

from .. import config
import functions

import staticdhcpdlib
import libpydhcpserver

_logger = logging.getLogger('web.server')

from staticdhcpdlib.web import (
 retrieveHeaderCallbacks,
 retrieveDashboardCallbacks,
 retrieveVisibleMethodCallbacks
)

_SYSTEM_NAME = functions.sanitise(config.SYSTEM_NAME) #: The name of the system
_FOOTER = """<div style="float: right;">If you benefit from this system, please <a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&amp;hosted_button_id=11056045">support it</a></div>
<a href="%(staticdhcpd-url)s">staticDHCPd</a> v%(staticdhcpd-version)s |
<a href="%(libpydhcpserver-url)s">libpydhcpserver</a> v%(libpydhcpserver-version)s""" % {
 'staticdhcpd-url': functions.sanitise(staticdhcpdlib.URL),
 'staticdhcpd-version': functions.sanitise(staticdhcpdlib.VERSION),
 'libpydhcpserver-url': functions.sanitise(libpydhcpserver.URL),
 'libpydhcpserver-version': functions.sanitise(libpydhcpserver.VERSION),
} #: The footer's HTML fragment
_BOOT_TIME = datetime.datetime.now().replace(microsecond=0) #: The time at which the system was started

def _renderHeaders(path, queryargs, mimetype, data, headers):
    """
    Renders all HTML headers.
    
    :param basestring path: The requested path.
    :param dict queryargs: All query arguments.
    :param basestring mimetype: The MIME-type of any accompanying data.
    :param str data: Any data uploaded by the client.
    :param headers: All HTTP headers.
    
    :return str: An HTML fragment.
    """
    output = []
    for callback in retrieveHeaderCallbacks():
        try:
            content = callback(path, queryargs, mimetype, data, headers)
        except Exception:
            _logger.error("Unable to execute header-element %(callback)r:\n%(error)s" % {
             'callback': callback,
             'error': traceback.format_exc(),
            })
        else:
            if content:
                output.append(content)
    return '\n'.join(output)
    
def _renderHeader():
    """
    Renders the header section of the web interface.
    
    :return str: An HTML fragment.
    """
    current_time = datetime.datetime.now().replace(microsecond=0)
    return """<div style="float: right;">Page generated %(current-time)s</div>
<a href="/" style="color: inherit; font-weight: bold;">%(name)s</a> online for %(uptime)s, since %(boot-time)s""" % {
     'current-time': current_time.ctime(),
     'name': _SYSTEM_NAME,
     'uptime': str(current_time - _BOOT_TIME),
     'boot-time': _BOOT_TIME.ctime(),
    }
    
def _renderFooter():
    """
    Renders the footer section of the web interface.
    
    :return str: An HTML fragment.
    """
    return _FOOTER
    
def _renderMain(elements, path, queryargs, mimetype, data, headers):
    """
    Renders the main section of the web interface.
    
    :param elements: The elements to render.
    :param basestring path: The requested path.
    :param dict queryargs: All query arguments.
    :param basestring mimetype: The MIME-type of any accompanying data.
    :param str data: Any data uploaded by the client.
    :param headers: All HTTP headers.
    
    :return str: An HTML fragment.
    """
    output = []
    for element in elements:
        if not element:
            output.append('<hr class="element"/>')
            continue
            
        try:
            result = element.callback(path=path, queryargs=queryargs, mimetype=mimetype, data=data, headers=headers)
        except Exception:
            _logger.error("Unable to render dashboard element '%(module)s' '%(name)s':\n%(error)s" % {
             'module': element.module,
             'name': element.name,
             'error': traceback.format_exc(),
            })
        else:
            if result is not None:
                output.append('<h1 class="element">%(module)s | %(name)s</h1>' % {
                'module': element.module,
                'name': element.name,
                })
                output.append('<div class="element">')
                output.append(result)
                output.append('</div>')
    return '\n'.join(output)
    
def _renderMethods():
    """
    Renders the methods section of the web interface.
    
    :return str: An HTML fragment.
    """
    output = []
    module = None
    for (element, path) in retrieveVisibleMethodCallbacks():
        if element.module != module:
            if module is not None:
                output.append('</div>')
            module = element.module
            output.append('<h1 class="method">%(module)s</h1>' % {
             'module': element.module,
            })
            output.append('<div class="method">')
        output.append('<a href="%(path)s" style="color: inherit;"%(confirm)s>%(name)s</a><br/>' % {
         'path': path,
         'name': element.name,
         'confirm': element.confirm and ' onclick="return confirm(\'&quot;%(module)s | %(name)s&quot; requested that you confirm your intent to proceed\');"' % {
          'module': element.module,
          'name': element.name,
         } or '',
        })
    else:
        if module is not None:
            output.append('</div>')
    return '\n'.join(output)
    
def _renderTemplate(elements, path, queryargs, mimetype, data, headers, rewrite_location=False):
    """
    Renders the web interface.
    
    :param elements: The elements to render.
    :param basestring path: The requested path.
    :param dict queryargs: All query arguments.
    :param basestring mimetype: The MIME-type of any accompanying data.
    :param str data: Any data uploaded by the client.
    :param headers: All HTTP headers.
    :param bool rewrite_location: Whether the URI should be rewritten to point
                                  at the dashboard.
    
    :return str: An HTML fragment.
    """
    return ('application/xhtml+xml; charset=utf-8',
"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
%(headers)s
    </head>
    <body%(rewrite-location)s>
        <div id="content">
            <div id="header">
%(header)s
            </div>
            <div id="methods">
%(methods)s
            </div>
            <div id="main">
%(main)s
            </div>
            <div id="footer">
%(footer)s
            </div>
        </div>
    </body>
</html>
""" % {
     'headers': _renderHeaders(path, queryargs, mimetype, data, headers),
     'header': _renderHeader(),
     'methods': _renderMethods(),
     'main': _renderMain(elements, path, queryargs, mimetype, data, headers),
     'footer': _renderFooter(),
     'rewrite-location': rewrite_location and ' onload="rewriteLocation(\'/\');"' or '',
    })
    
def renderTemplate(path, queryargs, mimetype, data, headers, element):
    """
    Renders a single-element view.
    
    :param basestring path: The requested path.
    :param dict queryargs: All query arguments.
    :param basestring mimetype: The MIME-type of any accompanying data.
    :param str data: Any data uploaded by the client.
    :param headers: All HTTP headers.
    :param :class:`WebMethod <web.WebMethod>` element: The element to render.
    
    :return str: An HTML fragment.
    """
    return _renderTemplate((element,), path=path, queryargs=queryargs, mimetype=mimetype, data=data, headers=headers)
    
def renderDashboard(path, queryargs, mimetype, data, headers, featured_element=None):
    """
    Renders the dashboard view.
    
    :param basestring path: The requested path.
    :param dict queryargs: All query arguments.
    :param basestring mimetype: The MIME-type of any accompanying data.
    :param str data: Any data uploaded by the client.
    :param headers: All HTTP headers.
    :param :class:`WebMethod <web.WebMethod>` featured_element: The element to
        present at the start of the dashboard.
    
    :return str: An HTML fragment.
    """
    elements = retrieveDashboardCallbacks()
    if featured_element:
        elements = [featured_element, None] + list(elements)
        
    return _renderTemplate(elements, path, queryargs, mimetype, data, headers, rewrite_location=bool(featured_element))
    