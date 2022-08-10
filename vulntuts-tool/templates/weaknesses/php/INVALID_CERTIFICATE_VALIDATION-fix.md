Most libraries already validate TLS certificates by default unless validation is manually disabled by the developer.
Therefore, the **validation should never be disabled manually**.

If the TLS certificate validation fails due to a self-signed certificate, the self-signed certificate should be added to the host's trusted certificates for the validation to succeed.
It is then no longer necessary to disable the TLS certificate validation.

To fix the example from the previous section, set the CURL options `CURLOPT_SSL_VERIFYPEER` and `CURLOPT_SSL_VERIFYHOST` to `true`:

<pre class="language-php line-numbers" data-line="6-7"><code>
// url to connect to
$url = "https://example.org";

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, true);
curl_setopt($ch, CURLOPT_HEADER, false);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$result = curl_exec($ch);
</code></pre>
