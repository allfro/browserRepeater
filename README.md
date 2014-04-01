About
-----

This BurpSuite plugin renders responses returned in the Repeater tool in a real browser (specifically Firefox). The plugin uses
Selenium, a popular browser automation framework, to control the web browser when the Repeater tool is used in Burp
Suite. Think of this extension as the automatic 'Show Response In Browser' (SRIB) tool. Instead of using the SRIB
feature repeatedly in Burp Suite, this extension automates the process and makes pen-testing web apps that use mostly
JavaScript rendered web pages much easier.


Requirements
------------

You'll need the following to get started:
- the standalone version of Jython available at http://www.jython.org/downloads.html.
- the latest version of BurpSuite versions 1.6 or later.
- Firefox
- a positive attitude!


Known Issues & Workarounds
--------------------------

If a JavaScript alert box appears and the operator manually accepts the alert, Selenium will cease operation and the
extension will deadlock. The only work around for this issue is to manually close the browser and restart the plugin.


Help!
-----

This is still a work in progress so their may be a few bugs I haven't hammered out.
