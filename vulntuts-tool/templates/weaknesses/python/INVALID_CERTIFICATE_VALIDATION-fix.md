Most libraries already validate TLS certificates by default unless validation is manually disabled by the developer.
Therefore, the **validation should never be disabled manually**.

If the TLS certificate validation fails due to a self-signed certificate, the self-signed certificate should be added to the host's trusted certificates for the validation to succeed.
It is then no longer necessary to disable the TLS certificate validation.

To fix the example from the previous section, set the `verify` parameter to `True` or omit it, as this is the default value:

<pre class="language-python line-numbers" data-line="4"><code>
import requests

url = "https://example.org"
result = requests.get(url, verify=True)
</code></pre>
