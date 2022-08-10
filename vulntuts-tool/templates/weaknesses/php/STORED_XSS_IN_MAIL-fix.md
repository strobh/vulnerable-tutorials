The function `htmlspecialchars` converts any HTML special characters into their HTML encodings, meaning they will then *not* be processed as standard HTML.

As a general rule, you should **never trust input coming from a client**. Every GET or POST parameter and cookie value should therefore be validated. It is best practice to **always escape any output** so they will not be evaluated in an unexpected way. 

To fix the example from the previous section:

<pre class="language-php line-numbers" data-line="9,13"><code>
$subject = "Contact form on example.org";
$headers = "MIME-Version: 1.0\r\n"
    . "Content-type: text/html; charset=utf-8\r\n"
    . "From: contact@example.org\r\n";

$email_body = "
    &lt;div>
        &lt;label>Name:&lt;/label>
        " . htmlspecialchars($_POST['name']) . "
    &lt;/div>
    &lt;div>
        &lt;label>Text:&lt;/label>
        " . htmlspecialchars($_POST['text']) . "
    &lt;/div>";

mail("contact@example.org", $subject, $email_body, $headers);
</code></pre>

The resulting HTML of the email would then look like this:

<pre class="language-html line-numbers"><code>
&lt;div>
    &lt;label>Name:&lt;/label>
    Tom
&lt;/div>
&lt;div>
    &lt;label>Text:&lt;/label>
    Hello, I have a question regarding your website...
    &amp;lt;script&amp;gt;
    alert(&amp;quot;Malicious code&amp;quot;);
    &amp;lt;/script&amp;gt;
&lt;/div>
</code></pre>

And would be displayed in the email client like this:

<pre class="language-html line-numbers"><code>
Name: Tom
Text: Hello, I have a question regarding your website...
&lt;script&gt;
alert(&quot;Malicious code&quot;);
&lt;/script&gt;
</code></pre>

The script tag will not be interpreted as a JavaScript tag by the email client, but instead as simple text.
