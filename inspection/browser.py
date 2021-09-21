import base64
import pprint
import pychrome
import os


FAILED_REASON_TIMEOUT = 'Page.navigate timeout'
FAILED_REASON_STATUS_CODE = 'status code'
FAILED_REASON_LOADING = 'loading failed'


class Browser:
    def __init__(self, debugger_url='http://127.0.0.1:9222'):
        # create a browser instance which controls chromium
        self.browser = pychrome.Browser(url=debugger_url)
        self.tab_count = 0
        self.empty_tab = None

    def create_tab(self):
        tab = self.browser.new_tab()
        if self.tab_count == 0 and self.empty_tab:
            self.browser.close_tab(self.empty_tab)
            self.empty_tab = None
        self.tab_count += 1
        return Tab(tab)

    def close_tab(self, tab):
        tab._stop_tab()
        # an empty tab is needed as the debug connection breaks when no tab is opened
        if self.tab_count == 1:
            self.empty_tab = self.browser.new_tab()
        self.browser.close_tab(tab.tab)
        self.tab_count -= 1


class Tab:
    def __init__(self, tab):
        self.tab = tab
        self._setup_tab()

    def navigate(self, url, wait=True):
        self.webpage = Webpage(self, url)
        self._setup_navigate()
        self._navigate(url, wait)
        return self.webpage

    def _navigate(self, url, wait):
        try:
            # open url and wait for load event and js
            self._navigate_and_wait(url, wait)
            if self.webpage.failed:
                return

            # get root node of document, is needed to be sure that the DOM is loaded
            self.root_node = self.tab.DOM.getDocument().get('root')
        except Exception as e:
            self.webpage.set_failed(str(e), type(e).__name__, traceback.format_exc())

    def _navigate_and_wait(self, url, wait):
        try:
            #self.tab.Page.bringToFront()
            self.tab.Page.navigate(url=url, _timeout=15)

            # return if failed to load page
            if self.webpage.failed:
                return

            # we wait for load event and JavaScript
            if wait:
                self._wait_for_load_event_and_js()
        except pychrome.exceptions.TimeoutException as e:
            self.webpage.set_failed(FAILED_REASON_TIMEOUT, type(e).__name__)

    ############################################################################
    # SETUP
    ############################################################################

    def _setup_tab(self):
        # set callbacks for request and response logging
        self.tab.Network.requestWillBeSent = self._event_request_will_be_sent
        self.tab.Network.responseReceived = self._event_response_received
        self.tab.Network.loadingFailed = self._event_loading_failed
        self.tab.Page.loadEventFired = self._event_load_event_fired
        self.tab.Page.navigatedWithinDocument = self._event_navigated_within_document
        
        # start our tab after callbacks have been registered
        self.tab.start()
        
        # enable network notifications for all request/response so our
        # callbacks actually receive some data
        self.tab.Network.enable()

        # enable page domain notifications so our load_event_fired
        # callback is called when the page is loaded
        self.tab.Page.enable()

        # enable DOM, Runtime and Overlay
        self.tab.DOM.enable()
        self.tab.Runtime.enable()
        self.tab.Overlay.enable()

    def _setup_navigate(self):
        # initialize `_is_loaded` variable to `False`
        # it will be set to `True` when the `loadEventFired` event occurs
        self._is_loaded = False

        # data about requests
        self.recordRedirects = True
        self.requestId = None
        self.frameId = None

    def _stop_tab(self):
        # stop the tab
        self.tab.stop()

    def _wait_for_load_event_and_js(self, load_event_timeout=30, js_timeout=2):
        self._wait_for_load_event(load_event_timeout)

        # wait for JavaScript code to be run, after the page has been loaded
        self.tab.wait(js_timeout)

    def _wait_for_load_event(self, load_event_timeout):
        # we wait for the load event to be fired (see `_event_load_event_fired`)
        waited = 0
        while not self._is_loaded and waited < load_event_timeout:
            self.tab.wait(0.1)
            waited += 0.1

        if waited >= load_event_timeout:
            self.webpage.set_stopped_waiting('load event')
            #self.tab.Page.stopLoading()

    ############################################################################
    # EVENTS
    ############################################################################

    def _event_request_will_be_sent(self, request, requestId, **kwargs):
        """Will be called when a request is about to be sent.

        Those requests can still be blocked or intercepted and modified.
        This script does not use any blocking or intercepting.

        Note: It does not say anything about the request being successful,
        there can still be connection issues.
        """
        # the request id of the first request is stored to detect failures
        if self.requestId == None:
            self.requestId = requestId

        if self.frameId == None:
            self.frameId = kwargs.get('frameId', False)

    def _event_response_received(self, response, requestId, **kwargs):
        """Will be called when a response is received.

        This includes the originating request which resulted in the
        response being received.
        """
        status = str(response['status'])

        if requestId == self.requestId:
            self.webpage.headers = response['headers']
        if requestId == self.requestId and (status.startswith('4') or status.startswith('5')):
            self.webpage.set_failed(FAILED_REASON_STATUS_CODE, status)

    def _event_loading_failed(self, requestId, errorText, **kwargs):
        if requestId == self.requestId:
            self.webpage.set_failed(FAILED_REASON_LOADING, errorText)

    def _event_navigated_within_document(self, url, frameId, **kwargs):
        is_root_frame = (self.frameId == frameId)
        if self.recordRedirects:
            self.webpage.add_redirect(url, root_frame=is_root_frame)

    def _event_load_event_fired(self, timestamp, **kwargs):
        """Will be called when the page sends an load event.

        Note that this only means that all resources are loaded, the
        page may still process some JavaScript.
        """
        self._is_loaded = True
        self.recordRedirects = False

    ############################################################################
    # NODES
    ############################################################################

    def get_root_node(self):
        return self.tab.DOM.getDocument().get('root')

    def get_html_of_node(self, node_id):
        return self.tab.DOM.getOuterHTML(nodeId=node_id).get('outerHTML')

    ############################################################################
    # SNAPSHOT
    ############################################################################
    def capture_snapshot(self):
        return self.tab.Page.captureSnapshot().get('data')

    ############################################################################
    # SCREENSHOTS
    ############################################################################

    def take_screenshot(self, only_viewport=False):
        # get the width and height
        layout_metrics = self.tab.Page.getLayoutMetrics()
        if only_viewport:
            viewport = layout_metrics.get('layoutViewport')
            width = viewport.get('clientWidth')
            height = viewport.get('clientHeight')
            x = viewport.get('pageX')
            y = viewport.get('pageY')
            screenshot_viewport = {'x': x, 'y': y, 'width': width, 'height': height, 'scale': 1}
        else:
            viewport = layout_metrics.get('cssContentSize')
            width = viewport.get('width')
            height = viewport.get('height')
            screenshot_viewport = {'x': 0, 'y': 0, 'width': width, 'height': height, 'scale': 1}

        # take screenshot and return it
        self._scroll(height)
        self._scroll(-height)
        return self.tab.Page.captureScreenshot(format='jpeg', quality=95,
            clip=screenshot_viewport, captureBeyondViewport=True, 
            fromSurface=True)['data']

    def _highlight_node(self, node_id):
        """Highlight the given node with an overlay."""
        color_content = {'r': 152, 'g': 196, 'b': 234, 'a': 0.5}
        color_padding = {'r': 184, 'g': 226, 'b': 183, 'a': 0.5}
        color_margin = {'r': 253, 'g': 201, 'b': 148, 'a': 0.5}
        highlightConfig = {'contentColor': color_content, 'paddingColor': color_padding, 'marginColor': color_margin}
        self.tab.Overlay.highlightNode(highlightConfig=highlightConfig, nodeId=node_id)

    def _hide_highlight(self):
        self.tab.Overlay.hideHighlight()

    ############################################################################
    # I/O
    ############################################################################
    
    def _scroll(self, delta_y):
        self.tab.Input.emulateTouchFromMouseEvent(type="mouseWheel", x=1, y=1, button="none", deltaX=0, deltaY=-1*delta_y)
        self.tab.wait(0.1)


class Webpage:
    def __init__(self, tab, url):
        self.tab = tab
        self.url = url

        self.headers = {}
        self.redirects = []

        self.failed = False
        self.failed_reason = None
        self.failed_exception = None
        self.failed_traceback = None

        self.stopped_waiting = False
        self.stopped_waiting_reason = None

        self.html = None
        self.snapshot = None
        self.screenshots = {}

    def add_redirect(self, url, root_frame=True):
        self.redirects.append({
                'url': url,
                'root_frame': root_frame
            })

    def set_failed(self, reason, exception=None, traceback=None):
        self.failed = True
        self.failed_reason = reason
        self.failed_exception = exception
        self.failed_traceback = traceback

    def set_stopped_waiting(self, reason):
        self.stopped_waiting = True
        self.stopped_waiting_reason = reason

    def capture_snapshot(self):
        # store html
        self.html = self.tab.get_html_of_node(self.tab.get_root_node().get('nodeId'))
        # store as mhtml
        self.snapshot = self.tab.capture_snapshot()

    def take_screenshot(self, name):
        # take screenshot and store it
        self.add_screenshot(name, self.tab.take_screenshot())

    def add_screenshot(self, name, screenshot):
        self.screenshots[name] = screenshot

    def save_screenshots(self, directory):
        for name, screenshot in self.screenshots.items():
            self._save_screenshot(name, screenshot, directory)

    def save_snapshot(self, directory):
        if self.snapshot:
            with open(os.path.join(directory, 'archive.mhtml'), 'w') as file:
                file.write(self.snapshot)
        if self.html:
            with open(os.path.join(directory, 'html.html'), 'w') as file:
                file.write(self.html)

    def _save_screenshot(self, name, screenshot, directory):
        with open(os.path.join(directory, f'{name}.png'), 'wb') as file:
            file.write(base64.b64decode(screenshot))
