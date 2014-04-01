from Queue import Queue
import SocketServer
from burp import (IBurpExtender, IHttpListener, IBurpExtenderCallbacks, IExtensionStateListener)
from threading import Thread, Event

import sys
import os

from urlparse import urlparse, urlunparse
from urllib import quote

import SimpleHTTPServer


try:
    raise NotImplementedError("No error")
except Exception, e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    root = os.path.dirname(exc_tb.tb_frame.f_code.co_filename)
    sys.path.extend([os.path.join(p, j) for p, d, f in os.walk(root) for j in f if j.endswith('.jar')])

from org.openqa.selenium import Proxy, NoAlertPresentException
from org.openqa.selenium.firefox import FirefoxDriver
from org.openqa.selenium.remote import DesiredCapabilities, CapabilityType

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, dotNetBeautifier  Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'


class DriverThread(Thread):
    def __init__(self, queue):
        super(DriverThread, self).__init__()
        self.queue = queue
        proxyServer = 'localhost:8080'
        proxy = Proxy()
        proxy.setHttpProxy(proxyServer)
        proxy.setSslProxy(proxyServer)
        capabilities = DesiredCapabilities()
        capabilities.setCapability(CapabilityType.PROXY, proxy)
        self.driver = FirefoxDriver(capabilities)

    def run(self):
        firstRun = True
        while True:
            url = self.queue.get()
            if not firstRun:
                self._acceptAlerts()
            elif firstRun:
                firstRun = False
            if not url:
                break
            sys.stdout.write('Fetching %s... ' % url)
            self.driver.get(url)
            print 'done.'
            self.queue.task_done()
        self.queue.task_done()
        self.driver.close()

    def _acceptAlerts(self):
        print '\n------ BEGIN ALERTS ------\n'
        while True:
            try:
                alert = self.driver.switchTo().alert()
                print 'javascript:alert(%s);' % repr(alert.getText())
                alert.dismiss()
            except NoAlertPresentException:
                print '\n------ END ALERTS ------\n'
                self.driver.switchTo().defaultContent()
                return


class DummyServer(Thread):

    def __init__(self):
        super(DummyServer, self).__init__()
        self._stop = Event()

    def run(self):
        httpd = SocketServer.TCPServer(('127.0.0.1', 31337), SimpleHTTPServer.SimpleHTTPRequestHandler)
        while not self.stopped():
            httpd.handle_request()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


class BurpExtender(IBurpExtender, IHttpListener, IExtensionStateListener):
    _redirectTemplate = 'HTTP/1.1 200 OK\r\n' \
                        'Cache-Control: no-cache, no-store\r\n' \
                        'Pragma: no-cache\r\n' \
                        'Content-Type: text/html; charset=utf-8\r\n' \
                        'Expires: -1\r\n\r\n' \
                        '<html><head><script>window.location=decodeURIComponent("%s")</script></head>' \
                        '<body>Please wait while we redirect you to your final destination...</body></html>\r\n\r\n'

    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        self._requestMaps = {}
        self._responses = {}
        self._counter = 0
        self._inCurrentSession = True

        self._queue = Queue()
        self._driver = DriverThread(self._queue)
        self._driver.start()
        self._dummyServer = DummyServer()
        self._dummyServer.start()

        callbacks.setExtensionName('Browser Renderer')
        callbacks.registerHttpListener(self)
        callbacks.registerExtensionStateListener(self)

    def _standardizeUrl(self, url):
        u = urlparse(url)
        if ':' not in u.netloc:
            return urlunparse((
                u.scheme,
                '%s:%d' % (u.netloc, 80 if u.scheme == 'http' else 443),
                u.path,
                u.params,
                u.query,
                u.fragment
            ))
        return url

    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        url = self._standardizeUrl(str(messageInfo.getUrl()))
        if toolFlag == IBurpExtenderCallbacks.TOOL_REPEATER:
            if messageIsRequest and url not in self._requestMaps:
                uniqueUrl = 'http://localhost:31337/realRenderer/%d' % self._counter
                self._requestMaps[url] = uniqueUrl
                self._requestMaps[uniqueUrl] = url
                self._counter += 1
            elif not messageIsRequest:
                self._callbacks.printError('Saving response for %s\n' % url)
                self._queue.join() # block until the last request is completed
                self._responses[(self._requestMaps[url], url)] = messageInfo.getResponse()
                self._callbacks.printError('Save complete for %s!\n' % url)
                self._queue.put(self._requestMaps[url])
                self._callbacks.printError('Navigating to %s in browser.\n' % url)
        elif toolFlag == IBurpExtenderCallbacks.TOOL_PROXY and not messageIsRequest:
            if url in self._requestMaps:
                if url.startswith('http://localhost:31337/realRenderer/'):
                    messageInfo.setResponse(
                        self._helpers.stringToBytes(
                            self._redirectTemplate % quote(self._requestMaps[url])
                        )
                    )
                else:
                    for h in self._helpers.analyzeRequest(messageInfo.getRequest()).getHeaders():
                        if h.startswith('Referer:'):
                            referer = self._standardizeUrl(h.split(': ')[1])
                            if (referer, url) in self._responses and self._responses[(referer, url)]:
                                messageInfo.setResponse(self._responses[(referer, url)])
                            break


    def extensionUnloaded(self):
        self._queue.put(None)
        self._driver.join()
        self._dummyServer.stop()