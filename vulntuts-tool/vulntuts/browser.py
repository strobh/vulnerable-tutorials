import base64
import io
import math
import os
import signal
import socket
import subprocess
import time
import traceback

import pychrome
from PIL import Image

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

BROWSER_PROFILE_DIR = "browser-profile"


def start_chromium(data_dir):
    chromium_script = os.path.join(__location__, "run-chromium.sh")
    profile_path = os.path.join(
        data_dir, f"{BROWSER_PROFILE_DIR}.{socket.gethostname()}"
    )
    return subprocess.Popen(
        [chromium_script, "--profile", profile_path], start_new_session=True
    )


def stop_chromium(chromium_runner):
    chromium_runner.send_signal(signal.SIGINT)
    chromium_runner.wait()
    time.sleep(1)


def is_chromium_running(chromium_runner):
    return chromium_runner.poll() is None


FAILED_REASON_TIMEOUT = "Page.navigate() timed out."
FAILED_REASON_STATUS_CODE = "Received HTTP error status code 4xx or 5xx."
FAILED_REASON_LOADING = "Loading failed."


class Browser:
    def __init__(self, debugger_url="http://127.0.0.1:9222"):
        # create a browser instance which controls chromium
        self.browser = pychrome.Browser(url=debugger_url)
        self.tab_count = 0
        self.empty_tab = None

        # check if there is an empty tab
        tabs = self._get_tabs()
        if len(tabs) == 1 and tabs[0]._kwargs.get("url") == "chrome://newtab/":
            self.empty_tab = tabs[0]

    def create_tab(self):
        tab = self.browser.new_tab()
        if self.tab_count == 0 and self.empty_tab:
            self._close_empty_tab()
        self.tab_count += 1
        return Tab(tab)

    def close_tab(self, tab):
        tab._stop_tab()
        # an empty tab is needed as the debug connection breaks when no tab is opened
        if self.tab_count == 1:
            self._create_empty_tab()
        self.browser.close_tab(tab.tab)
        self.tab_count -= 1

    def close(self):
        if not self.empty_tab:
            self._create_empty_tab()
        self.empty_tab.start()
        self.empty_tab.Browser.close()

    def _get_tabs(self):
        return self.browser.list_tab()

    def _create_empty_tab(self):
        self.empty_tab = self.browser.new_tab()

    def _close_empty_tab(self):
        self.browser.close_tab(self.empty_tab)
        self.empty_tab = None


class Tab:
    def __init__(self, tab):
        self.tab = tab
        self.frameId = None
        self._setup_tab()

    def navigate(self, url, wait=True, timeout=10):
        self.result = TabResult(self, url)
        self._setup_navigate()
        self._navigate(url, wait, timeout)
        return self.result

    def _navigate(self, url, wait, timeout):
        try:
            # open url and check if loading failed
            # self.tab.Page.bringToFront()
            self.tab.Page.navigate(url=url, _timeout=timeout)
            if self.result.failed:
                return

            # wait for load event and js
            if wait:
                self._wait_for_load_event_and_js()

            # get root node of document, is needed to be sure that the DOM is loaded
            self.root_node = self.tab.DOM.getDocument().get("root")
        except pychrome.exceptions.TimeoutException as e:
            self.result.set_failed(FAILED_REASON_TIMEOUT, type(e).__name__)
        except Exception as e:
            self.result.set_failed(str(e), type(e).__name__, traceback.format_exc())

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
        self.tab.Overlay.inspectNodeRequested = self._event_inspect_node_requested
        self.tab.Runtime.executionContextCreated = self._event_execution_context_created

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
            self.result.set_stopped_waiting("load event")
            # self.tab.Page.stopLoading()

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
        if self.requestId is None:
            self.requestId = requestId

        if self.frameId is None:
            self.frameId = kwargs.get("frameId", False)

    def _event_response_received(self, response, requestId, **kwargs):
        """Will be called when a response is received.

        This includes the originating request which resulted in the
        response being received.
        """
        status = str(response["status"])

        if requestId == self.requestId:
            self.result.headers = response["headers"]
            self.result.status_code = status
            if status.startswith("4") or status.startswith("5"):
                self.result.set_failed(FAILED_REASON_STATUS_CODE, status)

    def _event_loading_failed(self, requestId, errorText, **kwargs):
        if requestId == self.requestId:
            self.result.set_failed(FAILED_REASON_LOADING, errorText)

    def _event_navigated_within_document(self, url, frameId, **kwargs):
        is_root_frame = self.frameId == frameId
        if self.recordRedirects:
            self.result.add_redirect(url, root_frame=is_root_frame)

    def _event_load_event_fired(self, timestamp, **kwargs):
        """Will be called when the page sends an load event.

        Note that this only means that all resources are loaded, the
        page may still process some JavaScript.
        """
        self._is_loaded = True
        self.recordRedirects = False

    def _event_inspect_node_requested(self, backendNodeId):
        self._selected_backend_node = backendNodeId
        self.stop_node_selection()

    def _event_execution_context_created(self, context):
        if (
            self.frameId == context.get("auxData").get("frameId")
            and context.get("auxData").get("type") == "default"
        ):
            self._execution_context = context.get("id")

    ############################################################################
    # NODES
    ############################################################################

    def get_root_node(self):
        return self.tab.DOM.getDocument().get("root")

    def get_html_of_node(self, node_id):
        return self.tab.DOM.getOuterHTML(nodeId=node_id).get("outerHTML")

    def get_html_of_backend_node(self, backend_node_id):
        return self.tab.DOM.getOuterHTML(backendNodeId=backend_node_id).get("outerHTML")

    def get_node_id_by_selector(self, selector):
        node_id = self.tab.DOM.querySelector(
            selector=selector, nodeId=self.get_root_node().get("nodeId")
        ).get("nodeId")
        if node_id == 0:
            return None
        return node_id

    def get_text_of_backend_node(self, backend_node_id):
        remote_object_id = self._get_remote_object_id_for_backend_node(backend_node_id)
        return self._get_text_of_remote_object(remote_object_id)

    def get_text_of_node(self, node_id):
        remote_object_id = self._get_remote_object_id_for_node(node_id)
        return self._get_text_of_remote_object(remote_object_id)

    def _get_text_of_remote_object(self, remote_object_id):
        js_function = """
            function getInnerText(elem) {
                if (!elem) elem = this;
                return elem.innerText;
            }"""

        try:
            result = self.tab.Runtime.callFunctionOn(
                functionDeclaration=js_function, objectId=remote_object_id, silent=True
            ).get("result")
            return result.get("value")
        except pychrome.exceptions.CallMethodException:
            return None

    def get_box_model_of_backend_node(self, backend_node_id):
        return self.tab.DOM.getBoxModel(backendNodeId=backend_node_id).get("model")

    def get_bounding_box_of_backend_node(self, backend_node_id):
        box_model = self.get_box_model_of_backend_node(backend_node_id)
        quad = box_model.get("border")
        x = min(quad[0], quad[2], quad[4], quad[6])
        y = min(quad[1], quad[3], quad[5], quad[7])
        width = max(quad[0], quad[2], quad[4], quad[6]) - x
        height = max(quad[1], quad[3], quad[5], quad[7]) - y
        return {
            "x": int(x),
            "y": int(y),
            "width": int(width),
            "height": int(height),
        }

    def get_attributes_of_backend_node(self, backend_node_id):
        node = self.tab.DOM.describeNode(backendNodeId=backend_node_id).get("node")
        return self._dict_of_attributes(node.get("attributes"))

    def _dict_of_attributes(self, attributes):
        return dict(self._pairwise(attributes))

    def _pairwise(self, iterable):
        "s -> (s0, s1), (s2, s3), (s4, s5), ..."
        a = iter(iterable)
        return list(zip(a, a))

    def scroll_into_view(self, backend_node_id):
        js_function = """
            async function scrollIntoView(element) {
                if (!element) element = this;

                if (!element.isConnected)
                    return 'Node is detached from document';
                if (element.nodeType !== Node.ELEMENT_NODE)
                    return 'Node is not of type HTMLElement';
                const visibleRatio = await new Promise(resolve => {
                    const observer = new IntersectionObserver(entries => {
                        resolve(entries[0].intersectionRatio);
                        observer.disconnect();
                    });
                    observer.observe(element);
                });
                if (visibleRatio !== 1.0)
                    element.scrollIntoView({
                        block: 'center',
                        inline: 'center',
                        behavior: 'instant',
                    });
                return false;
            }"""

        try:
            remote_object_id = self._get_remote_object_id_for_backend_node(
                backend_node_id
            )
            self.tab.Runtime.callFunctionOn(
                functionDeclaration=js_function, objectId=remote_object_id, silent=True
            )
        except pychrome.exceptions.CallMethodException:
            return None

    def get_unique_selectors_of_backend_node(self, backend_node_id):
        js_function = """
            function uniqueSelector(elem) {
                if (!elem) elem = this;

                function getUniqueId(elem) {
                    let id = elem.getAttribute('id')
                    if (id) {
                        let selector = '[id="' + id.replace(/"/g, '\\\\"') + '"]';
                        if (document.querySelectorAll(selector).length == 1) {
                            return id;
                        }
                    }
                    return null;
                }

                function getUniqueClassCombination(elem) {
                    let className = elem.className
                    if (className
                        && document.getElementsByClassName(className).length == 1) {
                        return className;
                    }
                    return null;
                }

                function getUniqueAttributeCombination(elem) {
                    let attributes = Array.from(elem.attributes);
                    let selector = '';
                    for (var i = 0; i < attributes.length; i++) {
                        let attribute = attributes[i];
                        if (attribute.nodeName == 'style' || !attribute.nodeValue) {
                            continue;
                        }
                        selector += '[' + attribute.nodeName + '="'
                            + attribute.nodeValue.replace(/"/g, '\\\\"') + '"]';
                        console.log(selector);
                    }
                    if (selector && document.querySelectorAll(selector).length == 1) {
                        return selector;
                    }
                    return null;
                }

                return {
                    'name': elem.nodeName,
                    'unique_id': getUniqueId(elem),
                    'unique_class_combination': getUniqueClassCombination(elem),
                    'unique_attribute_selector': getUniqueAttributeCombination(elem),
                };
            }"""

        try:
            remote_object_id = self._get_remote_object_id_for_backend_node(
                backend_node_id
            )
            result = self.tab.Runtime.callFunctionOn(
                functionDeclaration=js_function, objectId=remote_object_id, silent=True
            ).get("result")
            return self._get_object_for_remote_object(result.get("objectId"))
        except pychrome.exceptions.CallMethodException:
            return None

    def get_scroll_percentage(self):
        js_function = """
            (function getScrollPercent() {
                var h = document.documentElement,
                    b = document.body,
                    st = 'scrollTop',
                    sh = 'scrollHeight';
                return (h[st]||b[st]) / ((h[sh]||b[sh]) - h.clientHeight) * 100;
            })();"""

        try:
            return (
                self.tab.Runtime.evaluate(expression=js_function, silent=True)
                .get("result")
                .get("value")
            )
        except pychrome.exceptions.CallMethodException:
            return None

    def scroll_to_position(self, x, y):
        js_function = """
            function scrollToPosition(x, y) {
                window.scrollTo(x, y);
            }"""
        try:
            self.tab.Runtime.callFunctionOn(
                functionDeclaration=js_function,
                executionContextId=self._execution_context,
                arguments=[{"value": x}, {"value": y}],
                silent=True,
            )
        except pychrome.exceptions.CallMethodException:
            pass

    def scroll_to_percentage(self, scroll_percentage):
        js_function = """
            function scrollToPercentage(percentage) {
                var h = document.documentElement,
                    b = document.body,
                    sh = 'scrollHeight';
                var height = h[sh]||b[sh];
                y = height * (percentage / 100.0);
                window.scrollTo(0, y);
            }"""
        try:
            self.tab.Runtime.callFunctionOn(
                functionDeclaration=js_function,
                executionContextId=self._execution_context,
                arguments=[{"value": scroll_percentage}],
                silent=True,
            )
        except pychrome.exceptions.CallMethodException:
            pass

    def scroll_to_top(self):
        self.scroll_to_position(0, 0)

    ############################################################################
    # SNAPSHOT / SCREENSHOT
    ############################################################################

    def set_viewport(self, width, height):
        self.tab.Emulation.setDeviceMetricsOverride(
            width=width, height=height, deviceScaleFactor=1, mobile=False
        )

    def reset_viewport(self):
        self.tab.Emulation.clearDeviceMetricsOverride()

    def get_html(self):
        return self.get_html_of_node(self.get_root_node().get("nodeId"))

    def take_snapshot(self):
        return self.tab.Page.captureSnapshot().get("data")

    def take_screenshot(self, only_viewport=False):
        # get the width and height
        layout_metrics = self.tab.Page.getLayoutMetrics()
        if only_viewport:
            viewport = layout_metrics.get("cssVisualViewport")
            width = viewport.get("clientWidth")
            height = viewport.get("clientHeight")
            x = viewport.get("pageX")
            y = viewport.get("pageY")
            screenshot_viewport = {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "scale": 1,
            }
            captureBeyondViewport = False
        else:
            viewport = layout_metrics.get("cssContentSize")
            width = viewport.get("width")
            height = viewport.get("height")
            screenshot_viewport = {
                "x": 0,
                "y": 0,
                "width": width,
                "height": height,
                "scale": 1,
            }
            captureBeyondViewport = True

            # scroll to top (fixed elements are placed at the top then)
            self.scroll_to_top()
            self.tab.wait(0.5)

        # take screenshot and return it
        return self._take_screenshot(
            screenshot_viewport, captureBeyondViewport=captureBeyondViewport
        )

    def take_screenshot_of_backend_node(self, backend_node_id):
        bounding_box = self.get_bounding_box_of_backend_node(backend_node_id)
        visual_viewport = self.tab.Page.getLayoutMetrics().get("cssVisualViewport")
        original_viewport = {
            "width": visual_viewport.get("clientWidth"),
            "height": visual_viewport.get("clientHeight"),
        }

        needs_viewport_reset = False

        # if the node to take a screenshot of is larger than the visual viewport,
        # the screenshot will be incomplete -> increase the visual viewport
        if bounding_box.get("width") > original_viewport.get(
            "width"
        ) or bounding_box.get("height") > original_viewport.get("height"):
            new_viewport = {
                "width": max(
                    original_viewport.get("width"), math.ceil(bounding_box.get("width"))
                ),
                "height": max(
                    original_viewport.get("height"),
                    math.ceil(bounding_box.get("height")),
                ),
            }
            # viewport is doubled to hide fixed headers/footers/banners
            self.set_viewport(
                new_viewport.get("width") * 2, new_viewport.get("height") * 2
            )
            needs_viewport_reset = True

        # scroll the node into view otherwise the screenshot will be incomplete
        self.scroll_into_view(backend_node_id)

        # get the bounding box (relative to the visual viewport) of the node and
        # convert it to the global coordinates
        local_rect = self.get_bounding_box_of_backend_node(backend_node_id)
        global_rect = self._local_to_global_rect(local_rect)

        # take the screenshot
        screenshot_viewport = dict(global_rect)
        screenshot_viewport["scale"] = 1
        screenshot = self._take_screenshot(
            screenshot_viewport, captureBeyondViewport=False
        )

        # reset viewport if it was increased earlier
        if needs_viewport_reset:
            self.reset_viewport()

        return screenshot

    def _take_screenshot(self, clip, captureBeyondViewport=True):
        # sources:
        # https://github.com/puppeteer/puppeteer/blob/
        # 230be28b067b521f0577206899db01f0ca7fc0d2/examples/screenshots-longpage.js
        # https://github.com/morteza-fsh/puppeteer-full-page-screenshot/blob/master/
        # src/index.js

        # screenshots have a maximum height of 16,384:
        # hardcoded max texture size of 16,384 (crbug.com/770769)
        max_screenshot_height = 16 * 1024

        # list of screenshots to be stitched together
        screenshots = list()

        y_top = clip.get("y")
        y_bottom = clip.get("y") + clip.get("height")

        # split screenshot into parts with max_screenshot_height
        for y_pos in range(y_top, y_bottom, max_screenshot_height):
            clip_height = min(y_bottom - y_pos, max_screenshot_height)
            self.tab.Page.bringToFront()
            screenshots.append(
                self.tab.Page.captureScreenshot(
                    format="png",
                    # quality=95,
                    clip={
                        "x": clip.get("x"),
                        "y": y_pos,
                        "width": clip.get("width"),
                        "height": clip_height,
                        "scale": 1,
                    },
                    captureBeyondViewport=captureBeyondViewport,
                    fromSurface=True,
                )["data"]
            )

        # function to stitch images together into one
        # source: https://stackoverflow.com/a/30228308
        def _stitch_screenshots(screenshots):
            # load images into Pillow
            images = [
                Image.open(io.BytesIO(base64.b64decode(screenshot)))
                for screenshot in screenshots
            ]

            # determine width and height
            widths, heights = zip(*(image.size for image in images))
            height = sum(heights)
            width = max(widths)

            stitched_image = Image.new("RGB", (width, height))
            y_offset = 0
            for image in images:
                stitched_image.paste(image, (0, y_offset))
                y_offset += image.size[1]

            buffer = io.BytesIO()
            stitched_image.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue())

        if len(screenshots) == 1:
            return screenshots[0]
        else:
            return _stitch_screenshots(screenshots)

    ############################################################################
    # HIGHLIGHT / OVERLAY
    ############################################################################

    def highlight_node(self, node_id):
        """Highlight the given node with an overlay."""
        highlightConfig = self._get_highlight_config()
        self.tab.Overlay.highlightNode(highlightConfig=highlightConfig, nodeId=node_id)

    def highlight_rect(self, x, y, width, height):
        color = self._get_highlight_config().get("contentColor")
        self.tab.Overlay.hightlightRect(
            x=x, y=y, width=width, height=height, color=color
        )

    def hide_highlight(self):
        self.tab.Overlay.hideHighlight()

    def _get_highlight_config(self):
        color_content = {"r": 152, "g": 196, "b": 234, "a": 0.5}
        color_padding = {"r": 184, "g": 226, "b": 183, "a": 0.5}
        color_margin = {"r": 253, "g": 201, "b": 148, "a": 0.5}
        return {
            "contentColor": color_content,
            "paddingColor": color_padding,
            "marginColor": color_margin,
        }

    ############################################################################
    # INSPECTION
    ############################################################################

    def start_node_selection(self):
        self._selected_backend_node = False
        self.tab.Overlay.setInspectMode(
            mode="searchForNode", highlightConfig=self._get_highlight_config()
        )

    def stop_node_selection(self):
        self.tab.Overlay.setInspectMode(
            mode="none", highlightConfig=self._get_highlight_config()
        )

    def get_selected_backend_node(self):
        # we wait for a node to be selected for inspection
        while not self._selected_backend_node:
            self.tab.wait(0.1)
        return self._selected_backend_node

    ############################################################################
    # I/O
    ############################################################################

    def _scroll(self, delta_y):
        self.tab.Input.emulateTouchFromMouseEvent(
            type="mouseWheel", x=1, y=1, button="none", deltaX=0, deltaY=-1 * delta_y
        )
        self.tab.wait(0.1)

    ############################################################################
    # COORDINATES
    ############################################################################

    def _local_to_global_rect(self, rect):
        layout_metrics = self.tab.Page.getLayoutMetrics()
        viewport = layout_metrics.get("cssVisualViewport")
        return {
            "x": int(rect.get("x") + viewport.get("pageX")),
            "y": int(rect.get("y") + viewport.get("pageY")),
            "width": rect.get("width"),
            "height": rect.get("height"),
        }

    ############################################################################
    # REMOTE OBJECTS
    ############################################################################

    def _get_object_for_remote_object(self, remote_object_id):
        object_attributes = self._get_properties_of_remote_object(remote_object_id)
        result = {
            attribute.get("name"): attribute.get("value").get("value")
            for attribute in object_attributes
            if self._is_remote_attribute_a_primitive(attribute)
        }

        # search for nested objects
        result.update(
            {
                attribute.get("name"): self._get_object_for_remote_object(
                    attribute.get("value").get("objectId")
                )
                for attribute in object_attributes
                if self._is_remote_attribute_an_object(attribute)
            }
        )

        # search for nested arrays
        result.update(
            {
                attribute.get("name"): self._get_array_for_remote_object(
                    attribute.get("value").get("objectId")
                )
                for attribute in object_attributes
                if self._is_remote_attribute_an_array(attribute)
            }
        )

        return result

    def _get_array_for_remote_object(self, remote_object_id):
        array_attributes = self._get_properties_of_remote_object(remote_object_id)
        return [
            array_element.get("value").get("value")
            for array_element in array_attributes
            if array_element.get("enumerable")
        ]

    def _is_remote_attribute_a_primitive(self, attribute):
        return (
            attribute.get("enumerable")
            and attribute.get("value").get("type") != "object"
            or attribute.get("value").get("subtype", "") == "null"
        )

    def _is_remote_attribute_an_object(self, attribute):
        return (
            attribute.get("enumerable")
            and attribute.get("value").get("type") == "object"
            and attribute.get("value").get("subtype", "") != "array"
            and attribute.get("value").get("subtype", "") != "null"
        )

    def _is_remote_attribute_an_array(self, attribute):
        return (
            attribute.get("enumerable")
            and attribute.get("value").get("type") == "object"
            and attribute.get("value").get("subtype", "") == "array"
        )

    def _get_properties_of_remote_object(self, remote_object_id):
        return self.tab.Runtime.getProperties(
            objectId=remote_object_id, ownProperties=True
        ).get("result")

    def _get_remote_object_id_for_backend_node(self, backend_node_id):
        try:
            return (
                self.tab.DOM.resolveNode(backendNodeId=backend_node_id)
                .get("object")
                .get("objectId")
            )
        except Exception:
            return None

    def _get_remote_object_id_for_node(self, node_id):
        try:
            return (
                self.tab.DOM.resolveNode(nodeId=node_id).get("object").get("objectId")
            )
        except Exception:
            return None


class TabResult:
    def __init__(self, tab, url):
        self.tab = tab
        self.url = url

        self.status_code = None
        self.headers = {}
        self.redirects = []

        self.failed = False
        self.failed_reason = None
        self.failed_exception = None
        self.failed_traceback = None

        self.stopped_waiting = False
        self.stopped_waiting_reason = None

    def add_redirect(self, url, root_frame=True):
        self.redirects.append({"url": url, "root_frame": root_frame})

    def set_failed(self, reason, exception=None, traceback=None):
        self.failed = True
        self.failed_reason = reason
        self.failed_exception = exception
        self.failed_traceback = traceback

    def set_stopped_waiting(self, reason):
        self.stopped_waiting = True
        self.stopped_waiting_reason = reason
